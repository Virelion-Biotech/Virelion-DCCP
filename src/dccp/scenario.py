"""Scenario representation and validation for Virelion-DCCP."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

_SCHEMA_CANDIDATES = (
    Path(__file__).resolve().parents[2] / "schemas" / "scenario.schema.json",
    Path(__file__).resolve().parent / "data" / "scenario.schema.json",
)


def _resolve_schema_path() -> Path:
    for path in _SCHEMA_CANDIDATES:
        if path.is_file():
            return path
    raise FileNotFoundError(
        "scenario.schema.json not found. Expected under repo schemas/ or package data/."
    )


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    path = _resolve_schema_path()
    with path.open(encoding="utf-8") as handle:
        schema = json.load(handle)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


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
            temporal_profile=dict(data["temporal_profile"]) if data.get("temporal_profile") else None,
            description=data.get("description"),
            ood_flag=bool(data.get("ood_flag", False)),
            version=str(data.get("version", "1.0.0")),
            raw=dict(data),
        )

    def mechanism_summary(self) -> dict[str, str]:
        """Return phenotypic axes as a mechanism-oriented assessment dict."""
        return dict(self.phenotypic_axes)


def validate_scenario(data: Mapping[str, Any]) -> list[str]:
    """Validate a scenario dict against the JSON Schema."""
    if not isinstance(data, Mapping):
        return ["<root>: scenario must be a JSON object"]
    errors = sorted(_validator().iter_errors(data), key=lambda error: tuple(str(p) for p in error.path))
    return [f"{'/'.join(str(p) for p in error.path) or '<root>'}: {error.message}" for error in errors]


def load_scenario(path: str | Path) -> Scenario:
    """Load and validate a scenario JSON file."""
    path = Path(path)
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    errors = validate_scenario(data)
    if errors:
        raise ValueError(
            f"Scenario validation failed for {path}:\n" + "\n".join(f"  - {error}" for error in errors)
        )
    return Scenario.from_dict(data)
