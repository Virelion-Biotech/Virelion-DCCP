"""Map DCCP phenotypic scenarios to CardiSim-compatible challenge schedules."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .scenario import Scenario

_LEVEL_SCALE = {"none": 0.0, "low": 0.15, "moderate": 0.35, "substantial": 0.55, "high": 0.75, "severe": 0.95}
_AXIS_TO_CARDISIM = {
    "inflammatory": {"inflammation": 1.0, "oxidative_stress": 0.4},
    "vascular_endothelial": {"angiogenesis": -0.5, "viability": -0.15},
    "metabolic_mitochondrial": {"metabolism": -0.8, "mitochondrial_health": -1.0, "oxidative_stress": 0.5},
    "contractile_functional": {"contractility": -1.0, "calcium_handling": -0.6, "electrophysiology": -0.35},
    "structural_injury": {"fibrosis": 0.9, "hypertrophy": 0.35},
    "cell_death": {"viability": -1.0},
    "remodeling": {"fibrosis": 0.45, "hypertrophy": 0.4, "maturity": -0.1},
}
_ONSET_DAYS = {"immediate": 0.0, "rapid": 0.0, "subacute": 1.0, "delayed": 3.0, "insidious": 5.0}
_PROGRESSION_DURATION = {"monotonic": 5.0, "biphasic": 3.0, "multiphasic": 2.5, "resolving": 4.0, "progressive": 8.0, "atypical": 4.0}


def _scale(level: str | None) -> float:
    if level is None:
        return 0.0
    try:
        return _LEVEL_SCALE[level]
    except KeyError:
        raise ValueError(f"unknown phenotypic axis level: {level!r}") from None

@dataclass(frozen=True)
class CardisimEventSpec:
    name: str
    onset: float
    duration: float
    magnitude: float
    effects: dict[str, float]
    recovery: float = 1.0

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("event name must be non-empty")
        onset = float(self.onset)
        duration = float(self.duration)
        magnitude = float(self.magnitude)
        recovery = float(self.recovery)
        if not math.isfinite(onset) or onset < 0:
            raise ValueError("onset must be finite and non-negative")
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("duration must be finite and > 0")
        if not math.isfinite(magnitude) or not math.isfinite(recovery):
            raise ValueError("magnitude and recovery must be finite")
        if not all(math.isfinite(float(value)) for value in self.effects.values()):
            raise ValueError("event effects must be finite numbers")

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "onset": float(self.onset), "duration": float(self.duration), "magnitude": float(self.magnitude), "effects": dict(self.effects), "recovery": float(self.recovery)}


def axes_to_effects(axes: Mapping[str, str]) -> dict[str, float]:
    acc: dict[str, float] = {}
    for axis, level in axes.items():
        if axis == "recovery_profile":
            continue
        mapping = _AXIS_TO_CARDISIM.get(axis)
        if not mapping:
            continue
        scale = _scale(level)
        for phenotype, weight in mapping.items():
            acc[phenotype] = acc.get(phenotype, 0.0) + weight * scale
    return {key: max(-1.0, min(1.0, value)) for key, value in acc.items()}


def scenario_to_event_specs(scenario: Scenario) -> list[CardisimEventSpec]:
    onset = _ONSET_DAYS.get(scenario.onset or "rapid", 0.0)
    base_duration = _PROGRESSION_DURATION.get(scenario.progression or "monotonic", 4.0)
    phases = scenario.temporal_profile.get("phases") if scenario.temporal_profile else None
    if not phases:
        return [CardisimEventSpec(scenario.scenario_id, onset, base_duration, 1.0, axes_to_effects(scenario.phenotypic_axes))]
    if not isinstance(phases, list):
        raise ValueError("temporal_profile.phases must be a list")
    specs: list[CardisimEventSpec] = []
    time = onset
    for index, phase in enumerate(phases):
        if not isinstance(phase, Mapping):
            raise ValueError(f"temporal_profile.phases[{index}] must be an object")
        name = str(phase.get("name") or f"phase_{index}")
        dominant = {str(axis) for axis in (phase.get("dominant_axes") or [])}
        if not dominant:
            dominant = {axis for axis in scenario.phenotypic_axes if axis != "recovery_profile"}
        full_axes = {axis: level for axis, level in scenario.phenotypic_axes.items() if axis != "recovery_profile"}
        dominant_axes = {axis: full_axes[axis] for axis in dominant if axis in full_axes}
        residual_axes = {axis: level for axis, level in full_axes.items() if axis not in dominant_axes}
        effects = axes_to_effects(dominant_axes)
        residual = axes_to_effects(residual_axes)
        for phenotype, value in residual.items():
            effects[phenotype] = max(-1.0, min(1.0, effects.get(phenotype, 0.0) + 0.5 * value))
        specs.append(CardisimEventSpec(f"{scenario.scenario_id}:{name}", time, base_duration, 1.0, effects))
        time += base_duration
    return specs


def scenario_to_cardisim_payload(scenario: Scenario) -> dict[str, Any]:
    specs = scenario_to_event_specs(scenario)
    return {"scenario_id": scenario.scenario_id, "confidence": scenario.confidence, "ood_flag": scenario.ood_flag, "phenotypic_axes": dict(scenario.phenotypic_axes), "events": [spec.as_dict() for spec in specs], "mapping_notes": "Effects are transparent host-response proxies derived from DCCP axes; they are not pathogen or agent parameters."}
