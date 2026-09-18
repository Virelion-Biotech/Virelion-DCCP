"""Deep edge-path tests for DCCP runtime and integration contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dccp.accession_provenance import (
    attach_accession_provenance,
    evidence_bundle_for_accessions,
)
from dccp.bundle import build_bundle
from dccp.cardisim_bridge import (
    CardisimEventSpec,
    axes_to_effects,
    scenario_to_event_specs,
)
from dccp.cli import _parse_scores, main
from dccp.detectors import PrototypeDetector, axes_to_vector
from dccp.evaluation_protocol import CaseResult, summarize_cases, wilson_interval
from dccp.fingerprint import file_hash
from dccp.host_features import (
    HostProfileFeatures,
    _module_mean_scores_from_log,
    _validate_expression,
    grn_hub_score,
    log1p_cpm_rows,
    minmax_scale_1d,
    module_mean_scores,
)
from dccp.ingest import IngestedArtifact, normalize_records
from dccp.integrity import manifest_for_files, verify_file_hashes
from dccp.library import materialize_challenge_set
from dccp.omics_map import (
    accession_digest,
    load_host_evidence_panel,
    ordinal_to_rank,
    realism_evidence_for_axes,
)
from dccp.provenance import run_provenance
from dccp.provenance_v2 import ArtifactProvenance
from dccp.recovery import build_rescue_event_dict, evaluate_recovery
from dccp.release_gate import release_gate
from dccp.scenario import Scenario, validate_scenario
from dccp.surrogate import _require_cardisim, _specs_to_schedule, _validate_run_config

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "scenarios" / "examples"


def _scenario(**overrides: object) -> Scenario:
    data = {
        "scenario_id": "SCENARIO-900",
        "title": "deep test",
        "tissue": "cardiac",
        "phenotypic_axes": {
            "inflammatory": "high",
            "contractile_functional": "moderate",
        },
        "realism_evidence": {"supported_components": ["test"]},
        "scenario_assumptions": {"model_derived_components": ["test"]},
        "confidence": "moderate",
    }
    data.update(overrides)
    assert validate_scenario(data) == []
    return Scenario.from_dict(data)


def test_accession_provenance_explicit_and_inferred():
    explicit = attach_accession_provenance(_scenario().raw, ["GSE135310"])
    assert explicit["realism_evidence"]["host_omics_provenance"]["accessions"] == ["GSE135310"]

    inferred = attach_accession_provenance(
        {
            **_scenario().raw,
            "_evidence_accessions": ["GSE135310"],
        }
    )
    assert inferred["realism_evidence"]["host_omics_provenance"]["accessions"] == ["GSE135310"]

    ref_inferred = attach_accession_provenance(
        {
            **_scenario().raw,
            "realism_evidence": {
                "supported_components": ["test"],
                "references": ["paper?acc=GSE135310&x=1"],
            },
        }
    )
    assert ref_inferred["realism_evidence"]["host_omics_provenance"]["accessions"] == ["GSE135310"]

    with pytest.raises(ValueError):
        attach_accession_provenance(_scenario().raw, [""])


def test_accession_bundle_rejects_empty_and_digests_are_stable():
    with pytest.raises(ValueError):
        evidence_bundle_for_accessions(["GSE135310", ""])
    assert len(accession_digest("GSE135310")) == 64


def test_bundle_rejects_bad_metadata_and_manifest_input(tmp_path: Path):
    source = tmp_path / "input.txt"
    source.write_text("x", encoding="utf-8")

    with pytest.raises(ValueError):
        build_bundle(tmp_path / "b1", run_id="", input_files=[source])
    with pytest.raises(ValueError):
        build_bundle(tmp_path / "b2", run_id="x", producer_version="", input_files=[source])

    manifest_output = tmp_path / "b3"
    manifest_output.mkdir()
    manifest = manifest_output / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        build_bundle(
            manifest_output,
            run_id="x",
            input_files=[manifest],
            base_dir=tmp_path,
        )

    with pytest.raises(FileNotFoundError):
        build_bundle(
            tmp_path / "b4",
            run_id="x",
            input_files=[tmp_path / "missing"],
            base_dir=tmp_path,
        )


def test_evaluation_protocol_error_and_empty_paths():
    assert summarize_cases([])["accuracy"] == 0.0
    assert summarize_cases([])["ood_accuracy"] == 0.0
    with pytest.raises(ValueError):
        CaseResult("", True, True)
    with pytest.raises(ValueError):
        CaseResult("X", True, True, score=float("inf"))
    assert wilson_interval(0, 0) == (0.0, 0.0)
    with pytest.raises(ValueError):
        wilson_interval(-1, 2)
    with pytest.raises(ValueError):
        wilson_interval(3, 2)
    with pytest.raises(ValueError):
        wilson_interval(1, 2, z=float("nan"))


def test_host_feature_edge_paths():
    assert _validate_expression([], []) == (0, 0)
    assert log1p_cpm_rows([]) == []

    with pytest.raises(ValueError):
        _validate_expression([[1], [2, 3]], ["A", "B"])

    assert minmax_scale_1d([]) == []
    with pytest.raises(ValueError):
        minmax_scale_1d([1, 2], lo_q=0.8, hi_q=0.2)
    with pytest.raises(ValueError):
        minmax_scale_1d([1, float("nan")])
    assert minmax_scale_1d([2, 2, 2]) == [0.0, 0.0, 0.0]

    expr = [[1.0, 0.0], [0.0, 2.0]]
    scores = module_mean_scores(expr, ["A", "B"], {"none": ("C",)})
    assert scores["none"] == [0.0, 0.0]
    assert grn_hub_score(expr, ["A", "B"], ["A"]) == pytest.approx(
        module_mean_scores(expr, ["A", "B"], {"hubs": ("A",)})["hubs"]
    )

    assert isinstance(
        HostProfileFeatures({}, {}, {}, 0).as_dict(),
        dict,
    )


def test_host_feature_all_zero_columns_do_not_crash():
    values = log1p_cpm_rows([[0.0, 0.0], [0.0, 0.0]])
    assert values == [[0.0, 0.0], [0.0, 0.0]]


def test_ingest_transform_preserves_source_identity(tmp_path: Path):
    path = tmp_path / "x.json"
    path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    artifact = IngestedArtifact(
        source=path.as_posix(),
        source_sha256=file_hash(path),
        record_count=3,
        payload=[1, 2, 3],
        transform="identity-json",
    )
    transformed = normalize_records(
        artifact,
        lambda payload: [x * 2 for x in payload],
        transform_name="double",
    )
    assert transformed.record_count == 3
    assert transformed.payload == [2, 4, 6]
    assert transformed.source_sha256 == artifact.source_sha256

    with pytest.raises(ValueError):
        normalize_records(artifact, lambda x: x, transform_name="   ")


def test_integrity_manifest_generation_and_failure_kinds(tmp_path: Path):
    source = tmp_path / "data.txt"
    source.write_text("ok", encoding="utf-8")
    manifest = manifest_for_files([source, source], base_dir=tmp_path)
    assert len(manifest["files"]) == 1
    assert len(manifest["manifest_sha256"]) == 64
    assert verify_file_hashes(manifest, tmp_path) == []

    missing_hash = verify_file_hashes({"files": [{"path": "data.txt"}]}, tmp_path)
    assert any(issue.kind == "missing_hash" for issue in missing_hash)

    malformed = verify_file_hashes({"files": ["bad"]}, tmp_path)
    assert any(issue.kind == "invalid" for issue in malformed)

    missing = verify_file_hashes(
        {"files": [{"path": "missing.txt", "sha256": "0" * 64}]},
        tmp_path,
    )
    assert any(issue.kind == "missing" for issue in missing)

    wrong = verify_file_hashes(
        {"files": [{"path": "data.txt", "sha256": "0" * 64}]},
        tmp_path,
    )
    assert any(issue.kind == "hash_mismatch" for issue in wrong)

    no_files = verify_file_hashes({}, tmp_path)
    assert any(issue.kind == "invalid" for issue in no_files)


def test_release_gate_failure_matrix():
    assert release_gate({})["passed"] is False
    assert release_gate({"entries": [{}]})["passed"] is False
    assert release_gate(
        {
            "entries": [
                {
                    "scenario_id": "A",
                    "path": "a.json",
                    "content_sha256": "0" * 64,
                    "audit_passed": False,
                }
            ]
        }
    )["passed"] is False


def test_cardisim_edge_paths():
    with pytest.raises(ValueError):
        axes_to_effects({"inflammatory": "invalid"})

    with pytest.raises(ValueError):
        CardisimEventSpec("", 0, 1, 1, {})
    with pytest.raises(ValueError):
        CardisimEventSpec("x", -1, 1, 1, {})
    with pytest.raises(ValueError):
        CardisimEventSpec("x", 0, float("nan"), 1, {})
    with pytest.raises(ValueError):
        CardisimEventSpec("x", 0, 1, float("inf"), {})
    with pytest.raises(ValueError):
        CardisimEventSpec("x", 0, 1, 1, {"x": float("nan")})

    sc = _scenario(
        temporal_profile={
            "phases": [
                {"name": "all_axes"},
                {"name": "dominant", "dominant_axes": ["inflammatory"]},
            ]
        }
    )
    specs = scenario_to_event_specs(sc)
    assert len(specs) == 2

    with pytest.raises(ValueError):
        scenario_to_event_specs(
            _scenario(temporal_profile={"phases": "bad"})
        )

    with pytest.raises(ValueError):
        scenario_to_event_specs(
            _scenario(
                temporal_profile={
                    "phases": [
                        {
                            "name": "bad",
                            "dominant_axes": ["vascular_endothelial"],
                        }
                    ]
                }
            )
        )


def test_detector_serialization_and_failure_paths():
    with pytest.raises(ValueError):
        axes_to_vector({"inflammatory": "invalid"})

    with pytest.raises(ValueError):
        PrototypeDetector(prototypes={"x": [1, 2]})

    det = PrototypeDetector().fit_default_ordinary()
    payload = det.to_dict()
    restored = PrototypeDetector.from_dict(payload)
    assert restored.to_dict()["ood_radius"] == det.ood_radius

    only_normal = PrototypeDetector(
        prototypes={"normal": [0.0] * 7}
    )
    with pytest.raises(ValueError):
        only_normal.assess(_scenario())


def test_omics_mapping_and_panel_edge_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    assert ordinal_to_rank("none") == 0
    with pytest.raises(ValueError):
        ordinal_to_rank("unknown")

    import dccp.omics_map as omics_map
    monkeypatch.setattr(omics_map, "__file__", str(tmp_path / "fake" / "module.py"))
    with pytest.raises(FileNotFoundError):
        load_host_evidence_panel(tmp_path / "missing.json")

    invalid = tmp_path / "invalid.json"
    invalid.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        load_host_evidence_panel(invalid)

    evidence = realism_evidence_for_axes(
        {
            "inflammatory": "high",
            "recovery_profile": "severe",
        },
        panel={"axis_evidence": {}},
    )
    assert "host cardiac phenotypic proxy scores" in evidence["supported_components"]
    assert evidence["proxy_only_components"]


def test_recovery_edge_paths():
    with pytest.raises(ValueError):
        evaluate_recovery(
            scenario_id="S",
            intervention_name="I",
            baseline={"viability": float("nan")},
            challenged={},
            rescued={},
        )

    report = evaluate_recovery(
        scenario_id="S",
        intervention_name="I",
        baseline={},
        challenged={},
        rescued={},
    )
    assert report.overall_recovery == 0.0
    assert any("no comparable" in note for note in report.notes)

    event = build_rescue_event_dict()
    assert event["name"] == "host_resilience_intervention"

    with pytest.raises(ValueError):
        build_rescue_event_dict(name="   ")
    with pytest.raises(ValueError):
        build_rescue_event_dict(onset=-1)
    with pytest.raises(ValueError):
        build_rescue_event_dict(duration=0)
    with pytest.raises(ValueError):
        build_rescue_event_dict(magnitude=float("nan"))
    with pytest.raises(ValueError):
        build_rescue_event_dict(effects={"x": float("inf")})


def test_provenance_validation_and_serialization():
    valid_hash = "a" * 64

    record = run_provenance(
        scenario_id="S",
        scenario_hash=valid_hash,
        tool="tool",
        tool_version="1",
        extra={"x": 1},
    )
    assert record["record_hash"]
    assert record["extra"]["x"] == 1

    with pytest.raises(ValueError):
        run_provenance(scenario_id="", scenario_hash=valid_hash, tool="t", tool_version="1")
    with pytest.raises(ValueError):
        run_provenance(scenario_id="S", scenario_hash="bad", tool="t", tool_version="1")
    with pytest.raises(ValueError):
        run_provenance(scenario_id="S", scenario_hash=valid_hash, tool="", tool_version="1")
    with pytest.raises(ValueError):
        run_provenance(scenario_id="S", scenario_hash=valid_hash, tool="t", tool_version="")

    artifact = ArtifactProvenance.for_json(
        "A",
        "json",
        {"x": 1},
        inputs=("src",),
        parameters={"mode": "test"},
    )
    assert len(artifact.content_hash) == 64
    assert artifact.as_dict()["inputs"] == ("src",)

    with pytest.raises(ValueError):
        ArtifactProvenance("A", "json", "bad")

    with pytest.raises(ValueError):
        ArtifactProvenance("A", "json", valid_hash, inputs=("",))

    with pytest.raises(ValueError):
        ArtifactProvenance("A", "json", valid_hash, producer="")


def test_surrogate_config_and_optional_dependency_boundary():
    assert _validate_run_config(1, 0.5, 1, 7) == (1.0, 0.5, 1, 7)
    with pytest.raises(ValueError):
        _validate_run_config(0, 0.5, 1, 7)
    with pytest.raises(ValueError):
        _validate_run_config(1, 2, 1, 7)
    with pytest.raises(ValueError):
        _validate_run_config(1, 0.5, 0, 7)

    with pytest.raises(ImportError, match="cardisim is required"):
        _require_cardisim()


def test_library_can_exclude_ood():
    all_cases = materialize_challenge_set(EXAMPLES, include_ood=True)
    non_ood = materialize_challenge_set(EXAMPLES, include_ood=False)
    assert non_ood["n_cases"] < all_cases["n_cases"]
    assert non_ood["n_ood"] == 0


def test_cli_score_parser_and_error_returns():
    assert _parse_scores("inflammatory=0.8, contractile_functional=0.4") == {
        "inflammatory": 0.8,
        "contractile_functional": 0.4,
    }
    with pytest.raises(ValueError):
        _parse_scores("")
    with pytest.raises(ValueError):
        _parse_scores("x=0.1=x")
    with pytest.raises(ValueError):
        _parse_scores("x=1.1")
    with pytest.raises(ValueError):
        _parse_scores("x=0.1,x=0.2")

    assert main(["validate", str(EXAMPLES / "does-not-exist.json")]) == 2


def test_module_mean_scores_helper_empty_matrix():
    assert _module_mean_scores_from_log([], ["A"], {"x": ("A",)}) == {"x": []}


def test_schedule_conversion():
    class FakeChallengeEvent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeSchedule:
        def __init__(self, events):
            self.events = events

    spec = CardisimEventSpec("x", 1, 2, 0.5, {"contractility": -0.2})
    schedule = _specs_to_schedule(
        [spec, {"name": "y", "effects": {"viability": -0.1}}],
        FakeChallengeEvent,
        FakeSchedule,
    )
    assert len(schedule.events) == 2
    assert schedule.events[1].kwargs["recovery"] == 1.0
