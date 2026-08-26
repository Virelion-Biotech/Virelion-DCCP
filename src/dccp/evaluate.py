"""Defensive evaluation stubs: abnormality, mechanism profile, OOD signal.

These are *reference heuristics* for the evaluation harness, not trained models.
They establish the output contract a defensive AI should satisfy:

1. Is the tissue state abnormal relative to a baseline?
2. Which response systems are implicated (mechanism-oriented axes)?
3. Does the profile fail to match known ordinary states (OOD-style flag)?

Replace or wrap with learned models without changing the result schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .scenario import Scenario

# Ordinal levels for distance calculations
_LEVEL_ORDER = ["none", "low", "moderate", "substantial", "high", "severe"]
_LEVEL_IDX = {n: i for i, n in enumerate(_LEVEL_ORDER)}

# Reference "normal" axes (all none/low)
_NORMAL: dict[str, str] = {
    "inflammatory": "none",
    "vascular_endothelial": "none",
    "metabolic_mitochondrial": "none",
    "contractile_functional": "none",
    "structural_injury": "none",
    "cell_death": "none",
    "remodeling": "none",
}

# Simple ordinary-pathology templates for distance-to-known
_ORDINARY_TEMPLATES: dict[str, dict[str, str]] = {
    "mi_like": {
        "inflammatory": "high",
        "vascular_endothelial": "moderate",
        "metabolic_mitochondrial": "substantial",
        "contractile_functional": "high",
        "structural_injury": "substantial",
        "cell_death": "substantial",
        "remodeling": "moderate",
    },
    "hypoxia_like": {
        "inflammatory": "moderate",
        "vascular_endothelial": "substantial",
        "metabolic_mitochondrial": "high",
        "contractile_functional": "substantial",
        "structural_injury": "low",
        "cell_death": "moderate",
        "remodeling": "low",
    },
}


def _axis_distance(a: Mapping[str, str], b: Mapping[str, str]) -> float:
    keys = set(a) | set(b)
    keys.discard("recovery_profile")
    if not keys:
        return 0.0
    total = 0.0
    for k in keys:
        ia = _LEVEL_IDX.get(a.get(k, "none"), 0)
        ib = _LEVEL_IDX.get(b.get(k, "none"), 0)
        total += abs(ia - ib)
    return total / len(keys)


@dataclass(frozen=True)
class DefensiveAssessment:
    """Mechanism-oriented defensive assessment of a challenge phenotype."""

    scenario_id: str
    abnormal: bool
    abnormality_score: float  # 0 = normal, higher = more abnormal
    mechanism_profile: dict[str, str]
    nearest_ordinary: str | None
    distance_to_nearest_ordinary: float
    ood_suggested: bool
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "abnormal": self.abnormal,
            "abnormality_score": round(self.abnormality_score, 4),
            "mechanism_profile": dict(self.mechanism_profile),
            "nearest_ordinary": self.nearest_ordinary,
            "distance_to_nearest_ordinary": round(self.distance_to_nearest_ordinary, 4),
            "ood_suggested": self.ood_suggested,
            "notes": list(self.notes),
        }


def assess_scenario(scenario: Scenario, *, ood_threshold: float = 1.5) -> DefensiveAssessment:
    """Heuristic defensive assessment from phenotypic axes alone.

    - abnormality_score: mean ordinal distance from normal
    - nearest_ordinary: closest ordinary template name
    - ood_suggested: True if far from all ordinary templates or scenario.ood_flag
    """
    axes = dict(scenario.phenotypic_axes)
    abn = _axis_distance(axes, _NORMAL)

    best_name: str | None = None
    best_dist = float("inf")
    for name, tmpl in _ORDINARY_TEMPLATES.items():
        d = _axis_distance(axes, tmpl)
        if d < best_dist:
            best_dist = d
            best_name = name

    notes: list[str] = []
    ood = bool(scenario.ood_flag) or best_dist >= ood_threshold
    if scenario.ood_flag:
        notes.append("scenario.ood_flag is set (held-out / novel by design)")
    if best_dist >= ood_threshold:
        notes.append(
            f"distance to nearest ordinary template ({best_name}) = {best_dist:.2f} ≥ {ood_threshold}"
        )

    abnormal = abn > 0.25
    if not abnormal:
        notes.append("profile close to normal reference")

    return DefensiveAssessment(
        scenario_id=scenario.scenario_id,
        abnormal=abnormal,
        abnormality_score=abn,
        mechanism_profile={k: v for k, v in axes.items() if k != "recovery_profile"},
        nearest_ordinary=best_name,
        distance_to_nearest_ordinary=best_dist if best_dist < float("inf") else 0.0,
        ood_suggested=ood,
        notes=notes,
    )
