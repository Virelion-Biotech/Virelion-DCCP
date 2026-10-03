"""Tests for scenario loading and validation."""

from __future__ import annotations

import json
from pathlib import Path

from dccp.audit import audit_scenario
from dccp.scenario import Scenario, load_scenario, validate_scenario

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "scenarios" / "examples" / "SCENARIO-017.example.json"


def test_example_validates():
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    assert validate_scenario(data) == []


def test_load_example():
    sc = load_scenario(EXAMPLE)
    assert isinstance(sc, Scenario)
    assert sc.scenario_id == "SCENARIO-017"
    assert sc.tissue == "cardiac"
    assert sc.ood_flag is True
    assert sc.confidence == "exploratory"
    axes = sc.mechanism_summary()
    assert axes["inflammatory"] == "substantial"
    assert axes["contractile_functional"] == "high"


def test_audit_example_passes():
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    result = audit_scenario(data)
    assert result.passed
    assert result.schema_errors == []
    assert result.policy_errors == []


def test_missing_required_fails():
    data = {"scenario_id": "SCENARIO-001", "title": "x"}
    errors = validate_scenario(data)
    assert errors


def test_empty_supported_components_is_schema_rejected():
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data["realism_evidence"] = {"supported_components": []}
    result = audit_scenario(data)
    assert not result.passed
    assert result.schema_errors
    assert "supported_components" in result.schema_errors[0]
