"""Tests for defensive assessment, CardiSim bridge, and provenance."""

from __future__ import annotations

import json
from pathlib import Path

from dccp.cardisim_bridge import axes_to_effects, scenario_to_cardisim_payload, scenario_to_event_specs
from dccp.evaluate import assess_scenario
from dccp.provenance import canonical_hash, scenario_digest
from dccp.scenario import load_scenario

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "scenarios" / "examples"


def test_ordinary_mi_not_ood():
    sc = load_scenario(EXAMPLES / "SCENARIO-001.ordinary-mi.json")
    a = assess_scenario(sc)
    assert a.abnormal is True
    assert a.nearest_ordinary == "mi_like"
    assert a.distance_to_nearest_ordinary < 0.5
    assert a.ood_suggested is False


def test_heldout_017_ood():
    sc = load_scenario(EXAMPLES / "SCENARIO-017.example.json")
    a = assess_scenario(sc)
    assert a.abnormal is True
    assert a.ood_suggested is True  # ood_flag set


def test_bridge_effects_include_contractility():
    sc = load_scenario(EXAMPLES / "SCENARIO-001.ordinary-mi.json")
    effects = axes_to_effects(sc.phenotypic_axes)
    assert "contractility" in effects
    assert effects["contractility"] < 0  # functional impairment → negative forcing
    assert "inflammation" in effects
    assert effects["inflammation"] > 0


def test_bridge_payload_has_events():
    sc = load_scenario(EXAMPLES / "SCENARIO-017.example.json")
    payload = scenario_to_cardisim_payload(sc)
    assert payload["scenario_id"] == "SCENARIO-017"
    assert len(payload["events"]) >= 1
    specs = scenario_to_event_specs(sc)
    assert specs[0].effects  # non-empty


def test_scenario_digest_stable():
    path = EXAMPLES / "SCENARIO-002.hypoxia-like.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    h1 = scenario_digest(data)
    h2 = scenario_digest(data)
    assert h1 == h2
    assert len(h1) == 64
    # key order independence
    reordered = {k: data[k] for k in sorted(data.keys(), reverse=True)}
    assert canonical_hash(reordered) == canonical_hash(data)
