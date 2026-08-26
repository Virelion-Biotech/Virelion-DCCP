"""Tests for host modules, omics mapping, features, and accession provenance."""

from __future__ import annotations

from dccp.accession_provenance import evidence_bundle_for_accessions, panel_accession_records
from dccp.host_features import extract_host_features, minmax_scale_1d
from dccp.host_modules import DCCP_AXIS_MODULES, module_coverage
from dccp.omics_map import (
    draft_scenario_from_scores,
    map_module_scores_to_axes,
    score_to_ordinal,
)
from dccp.scenario import validate_scenario


def test_score_to_ordinal_monotone():
    assert score_to_ordinal(0.0) == "none"
    assert score_to_ordinal(0.5) in {"moderate", "substantial"}
    assert score_to_ordinal(0.99) == "severe"


def test_map_module_scores():
    scores = {
        "inflammatory": 0.8,
        "contractile_functional": 0.7,
        "metabolic_mitochondrial": 0.4,
    }
    r = map_module_scores_to_axes(scores)
    assert r.ordinal["inflammatory"] in {"high", "severe", "substantial"}
    assert "vascular_endothelial" in r.ordinal


def test_draft_scenario_validates():
    draft = draft_scenario_from_scores(
        {"inflammatory": 0.75, "contractile_functional": 0.6, "structural_injury": 0.5},
        scenario_id="SCENARIO-099",
        title="Unit test draft",
        confidence="moderate",
    )
    # strip internal keys before schema validate
    clean = {k: v for k, v in draft.items() if not k.startswith("_")}
    errs = validate_scenario(clean)
    assert errs == [], errs


def test_module_coverage():
    genes = ["IL1B", "TNF", "TNNT2", "MYH7"]
    cov = module_coverage(genes, DCCP_AXIS_MODULES)
    assert cov["inflammatory"] > 0
    assert cov["contractile_functional"] > 0


def test_extract_host_features_toy_matrix():
    # genes x cells toy matrix
    genes = ["IL1B", "TNF", "CCL2", "TNNT2", "MYH7", "COL1A1", "PPARGC1A", "TFAM"]
    expr = [[float(i + j) for j in range(4)] for i in range(len(genes))]
    feat = extract_host_features(expr, genes)
    assert feat.n_cells == 4
    assert "inflammatory" in feat.axis_scores
    assert 0.0 <= feat.axis_scores["inflammatory"] <= 1.0


def test_minmax_scale():
    s = minmax_scale_1d([1.0, 2.0, 3.0, 4.0, 100.0])
    assert min(s) >= 0.0 and max(s) <= 1.0


def test_panel_accessions_and_bundle():
    recs = panel_accession_records()
    assert any(r["accession"] == "GSE135310" for r in recs)
    bundle = evidence_bundle_for_accessions(["GSE135310", "GSE999999"])
    assert "bundle_hash" in bundle
    assert "GSE999999" in bundle["missing_from_panel"]
    assert "leakage_policy_note" in bundle
