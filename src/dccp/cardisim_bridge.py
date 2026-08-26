"""Map DCCP phenotypic scenarios to CardiSim-compatible challenge schedules.

This module produces *effect dictionaries* and event-like structures that
match CardiSim's phenotype names (contractility, inflammation, …).
It does not import cardisim at runtime so DCCP remains usable without
CardiSim installed; consumers can pass the dicts into ChallengeEvent.

Mapping is deliberately transparent and documented — not a black-box
"attack simulator".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .scenario import Scenario

# DCCP axis level → signed magnitude scale used for CardiSim effects.
_LEVEL_SCALE: dict[str, float] = {
    "none": 0.0,
    "low": 0.15,
    "moderate": 0.35,
    "substantial": 0.55,
    "high": 0.75,
    "severe": 0.95,
}

# DCCP phenotypic axis → CardiSim phenotype effect directions.
# Positive values increase the CardiSim state; negative decrease it.
# These are *host-response proxies*, not pathogen parameters.
_AXIS_TO_CARDISIM: dict[str, dict[str, float]] = {
    "inflammatory": {
        "inflammation": 1.0,
        "oxidative_stress": 0.4,
    },
    "vascular_endothelial": {
        "angiogenesis": -0.5,  # dysfunction → reduced angiogenic capacity
        "viability": -0.15,
    },
    "metabolic_mitochondrial": {
        "metabolism": -0.8,
        "mitochondrial_health": -1.0,
        "oxidative_stress": 0.5,
    },
    "contractile_functional": {
        "contractility": -1.0,
        "calcium_handling": -0.6,
        "electrophysiology": -0.35,
    },
    "structural_injury": {
        "fibrosis": 0.9,
        "hypertrophy": 0.35,
    },
    "cell_death": {
        "viability": -1.0,
    },
    "remodeling": {
        "fibrosis": 0.45,
        "hypertrophy": 0.4,
        "maturity": -0.1,
    },
}

_ONSET_DAYS: dict[str, float] = {
    "immediate": 0.0,
    "rapid": 0.0,
    "subacute": 1.0,
    "delayed": 3.0,
    "insidious": 5.0,
}

_PROGRESSION_DURATION: dict[str, float] = {
    "monotonic": 5.0,
    "biphasic": 3.0,
    "multiphasic": 2.5,
    "resolving": 4.0,
    "progressive": 8.0,
    "atypical": 4.0,
}


@dataclass(frozen=True)
class CardisimEventSpec:
    """CardiSim-compatible event specification (no cardisim import required)."""

    name: str
    onset: float
    duration: float
    magnitude: float
    effects: dict[str, float]
    recovery: float = 1.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "onset": self.onset,
            "duration": self.duration,
            "magnitude": self.magnitude,
            "effects": dict(self.effects),
            "recovery": self.recovery,
        }


def _scale(level: str | None) -> float:
    if not level:
        return 0.0
    return _LEVEL_SCALE.get(level, 0.0)


def axes_to_effects(axes: Mapping[str, str]) -> dict[str, float]:
    """Convert DCCP phenotypic_axes into a single CardiSim effects dict.

    Effects are summed across axes; values are clipped to a reasonable range.
    """
    acc: dict[str, float] = {}
    for axis, level in axes.items():
        if axis == "recovery_profile":
            continue
        mapping = _AXIS_TO_CARDISIM.get(axis)
        if not mapping:
            continue
        s = _scale(level)
        if s == 0.0:
            continue
        for pheno, weight in mapping.items():
            acc[pheno] = acc.get(pheno, 0.0) + weight * s
    # soft clip
    return {k: max(-1.0, min(1.0, v)) for k, v in acc.items()}


def scenario_to_event_specs(scenario: Scenario) -> list[CardisimEventSpec]:
    """Build one or more CardiSim-compatible event specs from a Scenario.

    - Single primary event from overall axes when no temporal phases.
    - One event per phase when temporal_profile.phases is present,
      distributing dominant axes across phases.
    """
    onset0 = _ONSET_DAYS.get(scenario.onset or "rapid", 0.0)
    base_dur = _PROGRESSION_DURATION.get(scenario.progression or "monotonic", 4.0)
    phases = None
    if scenario.temporal_profile:
        phases = scenario.temporal_profile.get("phases")

    if not phases:
        effects = axes_to_effects(scenario.phenotypic_axes)
        return [
            CardisimEventSpec(
                name=scenario.scenario_id,
                onset=onset0,
                duration=base_dur,
                magnitude=1.0,
                effects=effects,
            )
        ]

    specs: list[CardisimEventSpec] = []
    t = onset0
    for i, phase in enumerate(phases):
        name = phase.get("name") or f"phase_{i}"
        dominant = phase.get("dominant_axes") or list(scenario.phenotypic_axes.keys())
        subset = {
            ax: scenario.phenotypic_axes[ax]
            for ax in dominant
            if ax in scenario.phenotypic_axes and ax != "recovery_profile"
        }
        # include residual low-weight contribution from non-dominant axes
        for ax, lvl in scenario.phenotypic_axes.items():
            if ax not in subset and ax != "recovery_profile":
                subset[ax] = lvl  # still map, scale will apply
        # re-weight: dominant full, others half
        effects_full = axes_to_effects(subset)
        effects_dom = axes_to_effects(
            {ax: scenario.phenotypic_axes[ax] for ax in dominant if ax in scenario.phenotypic_axes}
        )
        # prefer dominant-focused effects
        effects = effects_dom if effects_dom else effects_full
        dur = base_dur
        specs.append(
            CardisimEventSpec(
                name=f"{scenario.scenario_id}:{name}",
                onset=t,
                duration=dur,
                magnitude=1.0,
                effects=effects,
            )
        )
        t += dur
    return specs


def scenario_to_cardisim_payload(scenario: Scenario) -> dict[str, Any]:
    """JSON-serializable payload for hand-off to CardiSim or evaluation harness."""
    specs = scenario_to_event_specs(scenario)
    return {
        "scenario_id": scenario.scenario_id,
        "confidence": scenario.confidence,
        "ood_flag": scenario.ood_flag,
        "phenotypic_axes": dict(scenario.phenotypic_axes),
        "events": [s.as_dict() for s in specs],
        "mapping_notes": (
            "Effects are transparent host-response proxies derived from DCCP axes; "
            "they are not pathogen or agent parameters."
        ),
    }
