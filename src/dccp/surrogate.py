"""Optional CardiSim-backed surrogate runner."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from .cardisim_bridge import CardisimEventSpec, scenario_to_event_specs
from .recovery import DEFAULT_RESCUE_EFFECTS, RecoveryReport, evaluate_recovery
from .scenario import Scenario


def _require_cardisim():
    try:
        from cardisim import CardiacSimulator, SimulationConfig  # type: ignore
        from cardisim.events import ChallengeEvent, EventSchedule  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "cardisim is required for surrogate runs. Install Virelion-CardiSim "
            "or use recovery.evaluate_recovery on precomputed state dicts."
        ) from exc
    return CardiacSimulator, SimulationConfig, ChallengeEvent, EventSchedule


def _validate_run_config(duration: float, dt: float, n_cells: int, seed: int) -> tuple[float, float, int, int]:
    duration = float(duration)
    dt = float(dt)
    n_cells = int(n_cells)
    seed = int(seed)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("duration must be finite and > 0")
    if not math.isfinite(dt) or dt <= 0:
        raise ValueError("dt must be finite and > 0")
    if dt > duration:
        raise ValueError("dt must not exceed duration")
    if n_cells <= 0:
        raise ValueError("n_cells must be > 0")
    return duration, dt, n_cells, seed


def _specs_to_schedule(
    specs: Sequence[CardisimEventSpec | Mapping[str, Any]],
    ChallengeEvent,
    EventSchedule,
):
    events = []
    for spec in specs:
        data = spec.as_dict() if isinstance(spec, CardisimEventSpec) else dict(spec)
        events.append(
            ChallengeEvent(
                name=str(data["name"]),
                onset=float(data.get("onset", 0.0)),
                duration=float(data.get("duration", 1.0)),
                magnitude=float(data.get("magnitude", 1.0)),
                effects=dict(data.get("effects") or {}),
                recovery=float(data.get("recovery", 1.0)),
            )
        )
    return EventSchedule(tuple(events))


def run_scenario_surrogate(
    scenario: Scenario,
    *,
    duration: float = 28.0,
    dt: float = 0.5,
    n_cells: int = 64,
    seed: int = 7,
    extra_events: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run CardiSim on DCCP-derived challenge events and return its summary."""
    duration, dt, n_cells, seed = _validate_run_config(duration, dt, n_cells, seed)
    CardiacSimulator, SimulationConfig, ChallengeEvent, EventSchedule = _require_cardisim()
    specs: list[CardisimEventSpec | Mapping[str, Any]] = list(scenario_to_event_specs(scenario))
    if extra_events:
        specs.extend(dict(event) for event in extra_events)
    schedule = _specs_to_schedule(specs, ChallengeEvent, EventSchedule)
    config = SimulationConfig(duration=duration, dt=dt, n_cells=n_cells, seed=seed)
    result = CardiacSimulator(config).run(schedule)
    summary = result.summary()
    return {
        "scenario_id": scenario.scenario_id,
        "events": list(summary.get("events") or []),
        "initial": summary["initial"],
        "final": summary["final"],
        "delta": summary["delta"],
        "maturity_score": summary.get("maturity_score"),
        "cardiac_health_score": summary.get("cardiac_health_score"),
        "config": {"duration": duration, "dt": dt, "n_cells": n_cells, "seed": seed},
    }


def run_challenge_with_rescue(
    scenario: Scenario,
    *,
    rescue: Mapping[str, Any] | None = None,
    duration: float = 28.0,
    dt: float = 0.5,
    n_cells: int = 64,
    seed: int = 7,
) -> tuple[dict[str, Any], dict[str, Any], RecoveryReport]:
    """Run challenge and challenge+rescue simulations and score recovery."""
    rescue_event = dict(rescue) if rescue is not None else {
        "name": "host_resilience_intervention",
        "onset": 2.0,
        "duration": 12.0,
        "magnitude": 1.0,
        "effects": dict(DEFAULT_RESCUE_EFFECTS),
        "recovery": 1.0,
    }
    challenged = run_scenario_surrogate(scenario, duration=duration, dt=dt, n_cells=n_cells, seed=seed)
    rescued = run_scenario_surrogate(
        scenario,
        duration=duration,
        dt=dt,
        n_cells=n_cells,
        seed=seed,
        extra_events=[rescue_event],
    )
    report = evaluate_recovery(
        scenario_id=scenario.scenario_id,
        intervention_name=str(rescue_event.get("name", "rescue")),
        baseline=challenged["initial"],
        challenged=challenged["final"],
        rescued=rescued["final"],
    )
    return challenged, rescued, report
