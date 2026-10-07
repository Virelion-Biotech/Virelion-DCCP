from dataclasses import replace
from pathlib import Path

import pytest

from dccp.detectors import PrototypeDetector
from dccp.evaluate import assess_scenario
from dccp.host_features import log1p_cpm_rows
from dccp.integrity import manifest_for_files, verify_file_hashes
from dccp.omics_map import map_module_scores_to_axes
from dccp.recovery import evaluate_recovery
from dccp.scenario import load_scenario

EXAMPLE = Path(__file__).resolve().parents[1] / "scenarios/examples/SCENARIO-001.ordinary-mi.json"


def test_ood_label_cannot_change_prediction():
    scenario = load_scenario(EXAMPLE)
    assert (
        assess_scenario(scenario).ood_suggested
        == assess_scenario(replace(scenario, ood_flag=True)).ood_suggested
    )
    detector = PrototypeDetector().fit_default_ordinary()
    assert (
        detector.assess(scenario).ood_suggested
        == detector.assess(replace(scenario, ood_flag=True)).ood_suggested
    )


def test_abnormal_radius_controls_decision():
    scenario = load_scenario(EXAMPLE)
    assert (
        PrototypeDetector(abnormal_radius=20.0).fit_default_ordinary().assess(scenario).abnormal
        is False
    )


def test_missing_gene_coverage_is_not_absence():
    mapped = map_module_scores_to_axes({"inflammatory": 0.8}, genes_present=[])
    assert mapped.ordinal["inflammatory"] is None


def test_unknown_score_axes_fail():
    with pytest.raises(ValueError):
        map_module_scores_to_axes({"invented": 0.8})


def test_large_counts_do_not_normalize_to_zero():
    result = log1p_cpm_rows([[1e308], [1e308]])
    assert result[0][0] > 8.0


def test_manifest_digest_is_verified(tmp_path):
    source = tmp_path / "data.txt"
    source.write_text("data")
    manifest = manifest_for_files([source], tmp_path)
    manifest["manifest_sha256"] = "0" * 64
    assert verify_file_hashes(manifest, tmp_path)


def test_recovery_rejects_unbounded_states():
    with pytest.raises(ValueError):
        evaluate_recovery(
            scenario_id="synthetic",
            intervention_name="none",
            baseline={"viability": 100.0},
            challenged={"viability": 50.0},
            rescued={"viability": 80.0},
        )


@pytest.mark.parametrize("raw", ['{"a":1,"a":2}', '{"x":NaN}', '{"x":1e999}'])
def test_strict_json(raw):
    from dccp.serialization import strict_loads

    with pytest.raises(ValueError):
        strict_loads(raw)


def test_bundle_verifiable_and_tamper_detected(tmp_path):
    from dccp.bundle import build_bundle

    source = tmp_path / "source.txt"
    source.write_text("original")
    bundle = build_bundle(
        tmp_path / "bundle", run_id="synthetic", input_files=[source], base_dir=tmp_path
    )
    assert not verify_file_hashes(bundle, tmp_path)
    bundle["records"]["forged"] = True
    assert any(
        issue.kind == "manifest_hash_mismatch" for issue in verify_file_hashes(bundle, tmp_path)
    )


def test_source_manifest_cannot_contain_external_paths(tmp_path):
    outside = tmp_path.parent / "dccp-audit-outside.txt"
    outside.write_text("x")
    try:
        with pytest.raises(ValueError, match="outside base_dir"):
            manifest_for_files([outside], tmp_path)
    finally:
        outside.unlink()


def test_scenario_input_is_copied():
    import json
    from dccp.scenario import Scenario

    raw = json.loads(EXAMPLE.read_text())
    scenario = Scenario.from_dict(raw)
    raw["phenotypic_axes"]["inflammatory"] = "none"
    assert scenario.phenotypic_axes["inflammatory"] == "high"
    assert scenario.raw["phenotypic_axes"]["inflammatory"] == "high"


def test_unknown_modules_and_constant_profiles_not_health_estimates():
    from dccp.host_features import extract_host_features

    result = extract_host_features([[1.0, 1.0]], ["UNRELATED"])
    assert result.axis_scores["cell_death"] is None
    assert result.module_log_means["cell_death"] is None
    assert result.cardisim_proxy == {}


def test_incomplete_omics_draft_not_detector_ready():
    from dccp.omics_map import draft_scenario_from_scores
    from dccp.scenario import Scenario

    draft = draft_scenario_from_scores(
        {"inflammatory": 0.8}, scenario_id="SCENARIO-900", title="synthetic incomplete"
    )
    with pytest.raises(ValueError, match="unavailable"):
        assess_scenario(Scenario.from_dict(draft))


def test_healthy_baseline_uses_common_dimensions():
    report = evaluate_recovery(
        scenario_id="S",
        intervention_name="I",
        baseline={"viability": 1.0, "contractility": 0.0},
        challenged={"viability": 0.5},
        rescued={"viability": 0.8},
    )
    assert report.health_baseline == 1.0
    assert report.overall_recovery == pytest.approx(0.6)


def test_release_gate_cannot_trust_forged_audit(tmp_path):
    import json
    from dccp.fingerprint import file_hash
    from dccp.release_gate import release_gate

    path = tmp_path / "scenario.json"
    path.write_text("{}")
    registry = {
        "root": ".",
        "entries": [
            {
                "scenario_id": "SCENARIO-900",
                "path": "scenario.json",
                "content_sha256": file_hash(path),
                "audit_passed": True,
            }
        ],
    }
    assert release_gate(registry, base_dir=tmp_path)["passed"] is False
    registry["entries"][0]["audit_passed"] = "false"
    assert release_gate(registry)["passed"] is False
    path.write_text(json.dumps({"scenario_id": "SCENARIO-900"}))


def test_unaffected_domains_do_not_inflate_recovery():
    report = evaluate_recovery(
        scenario_id="S",
        intervention_name="I",
        baseline={"viability": 1.0, "contractility": 1.0},
        challenged={"viability": 0.5, "contractility": 1.0},
        rescued={"viability": 0.5, "contractility": 1.0},
    )
    assert report.overall_recovery == 0.0
    assert set(report.dimension_recovery) == {"viability"}


def test_no_trials_means_no_interval_information():
    from dccp.evaluation_protocol import wilson_interval

    assert wilson_interval(0, 0) == (0.0, 1.0)
    with pytest.raises(ValueError, match="integers"):
        wilson_interval(0.5, 1)


def test_atomic_write_failure_preserves_existing_artifact(tmp_path):
    from dccp.serialization import write_json

    output = tmp_path / "report.json"
    output.write_text("existing")
    with pytest.raises(ValueError):
        write_json(output, {"invalid": float("nan")})
    assert output.read_text() == "existing"


def test_source_and_packaged_examples_match():
    root = Path(__file__).resolve().parents[1]
    for source in (root / "scenarios/examples").glob("*.json"):
        assert source.read_bytes() == (root / "src/dccp/data/scenarios" / source.name).read_bytes()
    for source, target in [
        ("schemas/scenario.schema.json", "src/dccp/data/scenario.schema.json"),
        ("data/reference/host_evidence_panel.json", "src/dccp/data/host_evidence_panel.json"),
    ]:
        assert (root / source).read_bytes() == (root / target).read_bytes()


def test_extreme_quantile_values_are_scaled_without_overflow():
    from dccp.host_features import minmax_scale_1d

    assert minmax_scale_1d([-1e308, 0, 1e308], lo_q=0, hi_q=1) == [0.0, 0.5, 1.0]


def test_materialization_rejects_empty_or_policy_failed_sets(tmp_path):
    import json
    from dccp.library import materialize_challenge_set

    with pytest.raises(ValueError, match="empty"):
        materialize_challenge_set(tmp_path)
    raw = json.loads(EXAMPLE.read_text())
    raw["description"] = "agent genome"
    (tmp_path / "scenario.json").write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="policy audit"):
        materialize_challenge_set(tmp_path)
