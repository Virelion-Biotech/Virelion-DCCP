"""Integration and edge-case tests for the hardened DCCP contracts."""
from __future__ import annotations

import hashlib
import json

import pytest

from dccp.cardisim_bridge import CardisimEventSpec, scenario_to_event_specs
from dccp.detectors import PrototypeDetector
from dccp.host_features import extract_host_features
from dccp.ingest import load_json
from dccp.integrity import verify_file_hashes
from dccp.omics_map import draft_scenario_from_scores, score_to_ordinal
from dccp.registry import build_registry
from dccp.release_gate import release_gate
from dccp.scenario import Scenario, validate_scenario


def _scenario(**overrides) -> Scenario:
    data = {
        "scenario_id": "SCENARIO-900",
        "title": "test",
        "tissue": "cardiac",
        "phenotypic_axes": {"inflammatory": "high", "contractile_functional": "moderate"},
        "realism_evidence": {"supported_components": ["test"]},
        "scenario_assumptions": {"model_derived_components": ["test"]},
        "confidence": "moderate",
    }
    data.update(overrides)
    assert validate_scenario(data) == []
    return Scenario.from_dict(data)


def test_draft_scenario_is_schema_valid():
    draft = draft_scenario_from_scores(
        {"inflammatory": 0.8, "contractile_functional": 0.4},
        scenario_id="SCENARIO-901",
        title="draft",
    )
    assert validate_scenario(draft) == []
    assert not any(key.startswith("_") for key in draft)


def test_custom_thresholds_are_validated():
    assert score_to_ordinal(0.7, (0.1, 0.2, 0.4, 0.6, 0.8)) == "high"
    with pytest.raises(ValueError):
        score_to_ordinal(0.7, (0.1, 0.2))
    with pytest.raises(ValueError):
        score_to_ordinal(0.7, (0.1, 0.4, 0.3, 0.6, 0.8))


def test_temporal_residual_axes_are_weighted():
    scenario = _scenario(
        phenotypic_axes={"inflammatory": "high", "contractile_functional": "high"},
        temporal_profile={"phases": [{"name": "early", "dominant_axes": ["inflammatory"]}]},
    )
    events = scenario_to_event_specs(scenario)
    assert len(events) == 1
    # Inflammatory contributes fully, contractile contributes as a half-weight residual.
    assert events[0].effects["inflammation"] > 0
    assert events[0].effects["contractility"] < 0


def test_registry_is_complete_and_release_gate_passes():
    entries = build_registry("scenarios/examples")
    assert len(entries) >= 7
    payload = {"entries": [entry.as_dict() for entry in entries]}
    result = release_gate(payload)
    assert result["passed"] is True


def test_registry_rejects_missing_root():
    with pytest.raises(FileNotFoundError):
        build_registry("does-not-exist")


def test_integrity_rejects_unsafe_path(tmp_path):
    target = tmp_path / "data.txt"
    target.write_text("ok", encoding="utf-8")
    digest = hashlib.sha256(b"ok").hexdigest()
    issues = verify_file_hashes(
        {"files": [{"path": "../data.txt", "sha256": digest}]},
        tmp_path / "nested",
    )
    assert any(issue.kind == "unsafe_path" for issue in issues)


def test_ingest_counts_a_json_object_as_one_record(tmp_path):
    path = tmp_path / "artifact.json"
    path.write_text(json.dumps({"a": 1, "b": 2}), encoding="utf-8")
    artifact = load_json(path)
    assert artifact.record_count == 1


def test_host_feature_extraction_normalizes_once_and_validates_shape():
    genes = ["TNNT2", "TNNI3", "IL1B"]
    expression = [[1, 2], [3, 4], [5, 6]]
    features = extract_host_features(expression, genes)
    assert features.n_cells == 2
    with pytest.raises(ValueError):
        extract_host_features([[1, 2], [3]], genes[:2])


def test_prototype_detector_rejects_bad_labels_and_vectors():
    detector = PrototypeDetector()
    with pytest.raises(ValueError):
        detector.fit([_scenario()], labels=[])
    with pytest.raises(ValueError):
        PrototypeDetector.from_dict({"prototypes": {"x": [1, 2]}})


def test_event_spec_rejects_non_finite_values():
    with pytest.raises(ValueError):
        CardisimEventSpec("x", 0, 1, float("nan"), {})
