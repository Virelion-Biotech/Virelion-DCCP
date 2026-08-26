"""Scenario representation and validation for Virelion-DCCP."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

# Schema is kept next to the package for runtime validation; the canonical
# copy also lives at schemas/scenario.schema.json in the repo root.
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "scenario.schema.json"

_AXIS_LEVELS = ("none", "low", "moderate", "substantial", "high", "severe")
_CONFIDENCE = ("high", "moderate", "exploratory")


def _load_schema() -> dict[str, Any]:
    if not _SCHEMA_PATH.is_file():
        # Fallback for editable installs / alternate layouts
        alt = Path(__file__).resolve().parents[1] / "schemas" / "scenario.schema.json"
        path = alt if alt.is_file() else _SCHEMA_PATH
    else:
        path = _SCHEMA_PATH
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@dataclass(frozen=True)
class Scenario:
    """Immutable phenotypic challenge scenario.

    Only host-response / phenotypic fields are represented.
    Agent construction or operational parameters are intentionally absent.
    """

    scenario_id: str
    title: str
    tissue: str
    phenotypic_axes: Mapping[str, str]
    realism_evidence: Mapping[str, Any]
    scenario_assumptions: Mapping[str, Any]
    confidence: str
    onset: str | None = None
    progression: str | None = None
    temporal_profile: Mapping[str, Any] | None = None
    description: str | None = None
    ood_flag: bool = False
    version: str = "1.0.0"
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Scenario":
        return cls(
            scenario_id=data["scenario_id"],
            title=data["title"],
            tissue=data["tissue"],
            phenotypic_axes=dict(data.get("phenotypic_axes") or {}),
            realism_evidence=dict(data["realism_evidence"]),
            scenario_assumptions=dict(data["scenario_assumptions"]),
            confidence=data["confidence"],
            onset=data.get("onset"),
            progression=data.get("progression"),
            temporal_profile=data.get("temporal_profile"),
            description=data.get("description"),
            ood_flag=bool(data.get("ood_flag", False)),
            version=str(data.get("version", "1.0.0")),
            raw=dict(data),
        )

    def mechanism_summary(self) -> dict[str, str]:
        """Return phenotypic axes as a mechanism-oriented assessment dict."""
        return dict(self.phenotypic_axes)


def validate_scenario(data: Mapping[str, Any]) -> list[str]:
    """Validate a scenario dict against the JSON Schema.

    Returns a list of error messages (empty if valid).
    """
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    return [f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors]


def load_scenario(path: str | Path) -> Scenario:
    """Load and validate a scenario JSON file.

    Raises ValueError if the file fails schema validation.
    """
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    errs = validate_scenario(data)
    if errs:
        raise ValueError(
            f"Scenario validation failed for {path}:\n" + "\n".join(f"  - {e}" for e in errs)
        )
    return Scenario.from_dict(data)
