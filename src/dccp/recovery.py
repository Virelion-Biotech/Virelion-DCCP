"""Countermeasure / host-resilience evaluation.

Compares baseline → challenged → intervened trajectories on phenotype
dimensions that defensive systems care about (viability, contractility,
inflammation burden, mitochondrial health, etc.).

Works on plain dict summaries so CardiSim is optional. When cardisim is
installed, ``run_challenge_with_rescue`` can drive a full simulation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

# Phenotypes where *higher* is healthier
_POSITIVE = (
    "contractility",
    "calcium_handling",
    "electrophysiology",
    "metabolism",
    "angiogenesis",
    "viability",
    "mitochondrial_health",
    "maturity",
)
# Phenotypes where *lower* is healthier
_BURDEN = (
    "inflammation",
    "fibrosis",
    "oxidative_stress",
    "hypertrophy",
)


@dataclass(frozen=True)
class RecoveryReport:
    """Structured recovery / rescue evaluation."""

    scenario_id: str
    intervention_name: str
    baseline: Mapping[str, float]
    challenged: Mapping[str, float]
    rescued: Mapping[str, float]
    dimension_recovery: dict[str, float]  # 0 = no recovery, 1 = full return to baseline
    overall_recovery: float
    health_baseline: float
    health_challenged: float
    health_rescued: float
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "intervention_name": self.intervention_name,
            "baseline": dict(self.baseline),
            "challenged": dict(self.challenged),
            "rescued": dict(self.rescued),
            "dimension_recovery": {k: round(v, 4) for k, v in self.dimension_recovery.items()},
            "overall_recovery": round(self.overall_recovery, 4),
            "health_baseline": round(self.health_baseline, 4),
            "health_challenged": round(self.health_challenged, 4),
            "health_rescued": round(self.health_rescued, 4),
            "notes": list(self.notes),
        }


def _health(state: Mapping[str, float]) -> float:
    pos = [float(state[k]) for k in _POSITIVE if k in state]
    bur = [float(state[k]) for k in _BURDEN if k in state]
    if not pos:
        return 0.0
    positive = sum(pos) / len(pos)
    burden = sum(bur) / len(bur) if bur else 0.0
    return max(0.0, min(1.0, positive - 0.55 * burden))


def _dim_recovery(base: float, challenged: float, rescued: float, *, higher_better: bool) -> float:
    """Fraction of insult recovered toward baseline (clamped to [0, 1])."""
    if higher_better:
        insult = base - challenged
        if insult <= 1e-9:
            return 1.0 if rescued >= challenged - 1e-9 else 0.0
        gain = rescued - challenged
        return max(0.0, min(1.0, gain / insult))
    # lower is better
    insult = challenged - base
    if insult <= 1e-9:
        return 1.0 if rescued <= challenged + 1e-9 else 0.0
    reduction = challenged - rescued
    return max(0.0, min(1.0, reduction / insult))


def evaluate_recovery(
    *,
    scenario_id: str,
    intervention_name: str,
    baseline: Mapping[str, float],
    challenged: Mapping[str, float],
    rescued: Mapping[str, float],
) -> RecoveryReport:
    """Score how well an intervention restores phenotype state toward baseline."""
    keys = set(baseline) | set(challenged) | set(rescued)
    dim: dict[str, float] = {}
    notes: list[str] = []
    for k in sorted(keys):
        b = float(baseline.get(k, 0.0))
        c = float(challenged.get(k, 0.0))
        r = float(rescued.get(k, 0.0))
        higher = k not in _BURDEN
        dim[k] = _dim_recovery(b, c, r, higher_better=higher)

    # Weight key defensive dimensions more heavily
    priority = (
        "viability",
        "contractility",
        "mitochondrial_health",
        "inflammation",
        "oxidative_stress",
        "fibrosis",
    )
    weights: list[tuple[str, float]] = []
    for k in priority:
        if k in dim:
            weights.append((k, 2.0))
    for k, v in dim.items():
        if k not in priority:
            weights.append((k, 1.0))
    if weights:
        overall = sum(w * dim[k] for k, w in weights) / sum(w for _, w in weights)
    else:
        overall = 0.0
        notes.append("no overlapping phenotype keys to score")

    hb, hc, hr = _health(baseline), _health(challenged), _health(rescued)
    if hr > hc + 0.02:
        notes.append("rescued health exceeds challenged health")
    if hr >= hb - 0.05:
        notes.append("near-complete health restoration relative to baseline")

    return RecoveryReport(
        scenario_id=scenario_id,
        intervention_name=intervention_name,
        baseline=dict(baseline),
        challenged=dict(challenged),
        rescued=dict(rescued),
        dimension_recovery=dim,
        overall_recovery=overall,
        health_baseline=hb,
        health_challenged=hc,
        health_rescued=hr,
        notes=notes,
    )


# Default host-centric rescue effects (attenuate injury axes) — not drug recipes.
DEFAULT_RESCUE_EFFECTS: dict[str, float] = {
    "inflammation": -0.35,
    "oxidative_stress": -0.30,
    "contractility": 0.20,
    "mitochondrial_health": 0.25,
    "viability": 0.15,
    "metabolism": 0.12,
    "fibrosis": -0.10,
}


def build_rescue_event_dict(
    *,
    name: str = "host_resilience_intervention",
    onset: float = 2.0,
    duration: float = 10.0,
    magnitude: float = 1.0,
    effects: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """CardiSim-compatible rescue event as a plain dict."""
    return {
        "name": name,
        "onset": onset,
        "duration": duration,
        "magnitude": magnitude,
        "effects": dict(effects or DEFAULT_RESCUE_EFFECTS),
        "recovery": 1.0,
    }
