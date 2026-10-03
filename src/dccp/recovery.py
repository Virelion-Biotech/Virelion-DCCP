"""Countermeasure / host-resilience evaluation on phenotype trajectories."""
from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

_POSITIVE = ("contractility", "calcium_handling", "electrophysiology", "metabolism", "angiogenesis", "viability", "mitochondrial_health", "maturity")
_BURDEN = ("inflammation", "fibrosis", "oxidative_stress", "hypertrophy")
_KNOWN = set(_POSITIVE) | set(_BURDEN)

@dataclass(frozen=True)
class RecoveryReport:
    scenario_id: str
    intervention_name: str
    baseline: Mapping[str, float]
    challenged: Mapping[str, float]
    rescued: Mapping[str, float]
    dimension_recovery: dict[str, float]
    overall_recovery: float
    health_baseline: float
    health_challenged: float
    health_rescued: float
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"scenario_id": self.scenario_id, "intervention_name": self.intervention_name, "baseline": dict(self.baseline), "challenged": dict(self.challenged), "rescued": dict(self.rescued), "dimension_recovery": {key: round(value, 4) for key, value in self.dimension_recovery.items()}, "overall_recovery": round(self.overall_recovery, 4), "health_baseline": round(self.health_baseline, 4), "health_challenged": round(self.health_challenged, 4), "health_rescued": round(self.health_rescued, 4), "notes": list(self.notes)}


def _validate_state(state: Mapping[str, float], name: str) -> None:
    for key, value in state.items():
        value = float(value)
        if not math.isfinite(value):
            raise ValueError(f"{name}[{key!r}] must be finite")


def _health(state: Mapping[str, float]) -> float:
    positive = [float(state[key]) for key in _POSITIVE if key in state]
    burden = [float(state[key]) for key in _BURDEN if key in state]
    if not positive:
        return 0.0
    positive_mean = sum(positive) / len(positive)
    burden_mean = sum(burden) / len(burden) if burden else 0.0
    return max(0.0, min(1.0, positive_mean - 0.55 * burden_mean))


def _dim_recovery(base: float, challenged: float, rescued: float, *, higher_better: bool) -> float:
    if higher_better:
        insult = base - challenged
        if insult <= 1e-9:
            return 1.0 if rescued >= challenged - 1e-9 else 0.0
        return max(0.0, min(1.0, (rescued - challenged) / insult))
    insult = challenged - base
    if insult <= 1e-9:
        return 1.0 if rescued <= challenged + 1e-9 else 0.0
    return max(0.0, min(1.0, (challenged - rescued) / insult))


def evaluate_recovery(*, scenario_id: str, intervention_name: str, baseline: Mapping[str, float], challenged: Mapping[str, float], rescued: Mapping[str, float]) -> RecoveryReport:
    """Score intervention recovery using only comparable recognized phenotype dimensions."""
    _validate_state(baseline, "baseline")
    _validate_state(challenged, "challenged")
    _validate_state(rescued, "rescued")
    all_known = (set(baseline) | set(challenged) | set(rescued)) & _KNOWN
    keys = sorted(set(baseline) & set(challenged) & set(rescued) & _KNOWN)
    missing = sorted(all_known - set(keys))
    ignored = sorted((set(baseline) | set(challenged) | set(rescued)) - _KNOWN)
    notes: list[str] = []
    if missing:
        notes.append(f"excluded recognized dimensions missing from one or more states: {', '.join(missing)}")
    if ignored:
        notes.append(f"ignored unrecognized phenotype dimensions: {', '.join(ignored)}")

    dimension_recovery = {
        key: _dim_recovery(float(baseline[key]), float(challenged[key]), float(rescued[key]), higher_better=key not in _BURDEN)
        for key in keys
    }
    priority = {"viability", "contractility", "mitochondrial_health", "inflammation", "oxidative_stress", "fibrosis"}
    weighted = [(key, 2.0 if key in priority else 1.0) for key in dimension_recovery]
    if weighted:
        total_weight = sum(weight for _, weight in weighted)
        overall = sum(weight * dimension_recovery[key] for key, weight in weighted) / total_weight
    else:
        overall = 0.0
        notes.append("no comparable recognized phenotype keys to score")

    health_baseline = _health(baseline)
    health_challenged = _health(challenged)
    health_rescued = _health(rescued)
    if health_rescued > health_challenged + 0.02:
        notes.append("rescued health exceeds challenged health")
    if health_rescued >= health_baseline - 0.05:
        notes.append("near-complete health restoration relative to baseline")
    return RecoveryReport(scenario_id, intervention_name, dict(baseline), dict(challenged), dict(rescued), dimension_recovery, overall, health_baseline, health_challenged, health_rescued, notes)

DEFAULT_RESCUE_EFFECTS: dict[str, float] = {"inflammation": -0.35, "oxidative_stress": -0.30, "contractility": 0.20, "mitochondrial_health": 0.25, "viability": 0.15, "metabolism": 0.12, "fibrosis": -0.10}


def build_rescue_event_dict(*, name: str = "host_resilience_intervention", onset: float = 2.0, duration: float = 10.0, magnitude: float = 1.0, effects: Mapping[str, float] | None = None) -> dict[str, Any]:
    """Return a CardiSim-compatible host-resilience event dictionary."""
    if not str(name).strip():
        raise ValueError("name must be non-empty")
    onset = float(onset); duration = float(duration); magnitude = float(magnitude)
    if not math.isfinite(onset) or onset < 0:
        raise ValueError("onset must be finite and non-negative")
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("duration must be finite and > 0")
    if not math.isfinite(magnitude):
        raise ValueError("magnitude must be finite")
    effect_map = dict(effects or DEFAULT_RESCUE_EFFECTS)
    if not all(math.isfinite(float(value)) for value in effect_map.values()):
        raise ValueError("effects must contain only finite numeric values")
    return {"name": name, "onset": onset, "duration": duration, "magnitude": magnitude, "effects": effect_map, "recovery": 1.0}
