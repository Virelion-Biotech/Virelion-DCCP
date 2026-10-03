"""Tests for recovery scoring, library materialization, and prototype detector."""

from __future__ import annotations

from pathlib import Path

from dccp.detectors import HeuristicDetector, PrototypeDetector
from dccp.library import load_library, materialize_challenge_set
from dccp.recovery import evaluate_recovery
from dccp.scenario import load_scenario

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "scenarios" / "examples"


def test_recovery_partial_rescue():
    baseline = {
        "contractility": 0.62,
        "viability": 0.96,
        "inflammation": 0.10,
        "mitochondrial_health": 0.63,
        "oxidative_stress": 0.15,
        "fibrosis": 0.08,
    }
    challenged = {
        "contractility": 0.25,
        "viability": 0.50,
        "inflammation": 0.80,
        "mitochondrial_health": 0.25,
        "oxidative_stress": 0.70,
        "fibrosis": 0.45,
    }
    rescued = {
        "contractility": 0.45,
        "viability": 0.75,
        "inflammation": 0.40,
        "mitochondrial_health": 0.48,
        "oxidative_stress": 0.35,
        "fibrosis": 0.30,
    }
    report = evaluate_recovery(
        scenario_id="T",
        intervention_name="demo",
        baseline=baseline,
        challenged=challenged,
        rescued=rescued,
    )
    assert 0.0 < report.overall_recovery < 1.0
    assert report.health_rescued > report.health_challenged
    assert report.dimension_recovery["contractility"] > 0.0


def test_library_loads_all_examples():
    entries = load_library(EXAMPLES)
    assert len(entries) >= 6
    ids = {e.scenario.scenario_id for e in entries}
    assert "SCENARIO-001" in ids
    assert "SCENARIO-018" in ids


def test_materialize_challenge_set():
    payload = materialize_challenge_set(EXAMPLES)
    assert payload["n_cases"] >= 6
    assert payload["n_ood"] >= 2
    assert len(payload["set_hash"]) == 64
    assert all("assessment" in c for c in payload["cases"])


def test_prototype_detector_flags_heldout():
    ordinary = [
        load_scenario(EXAMPLES / "SCENARIO-001.ordinary-mi.json"),
        load_scenario(EXAMPLES / "SCENARIO-002.hypoxia-like.json"),
    ]
    heldout = load_scenario(EXAMPLES / "SCENARIO-018.heldout-metabolic-vascular.json")
    det = PrototypeDetector(ood_radius=2.0).fit(ordinary, labels=["mi", "hypoxia"])
    a_ord = det.assess(ordinary[0])
    a_ood = det.assess(heldout)
    assert a_ord.abnormal is True
    assert a_ood.ood_suggested is True  # flag or distance


def test_heuristic_detector_api():
    sc = load_scenario(EXAMPLES / "SCENARIO-001.ordinary-mi.json")
    a = HeuristicDetector().assess(sc)
    assert a.scenario_id == "SCENARIO-001"
