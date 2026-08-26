"""Optional CardiSim-backed surrogate runner.

If ``cardisim`` is not installed, functions raise a clear ImportError.
All public APIs still accept/return plain dicts so the rest of DCCP stays
decoupled.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .cardisim_bridge import CardisimEventSpec, scenario_to_event_specs
from .recovery import DEFAULT_RESCUE_EFFECTS, evaluate_recovery, RecoveryReport
from .scenario import Scenario


def _require_cardisim():
    try:
        from cardisim import CardiacSimulator, SimulationConfig  # type: ignore
        from cardisim.events import ChallengeEvent, EventSchedule  # type: ignore
    except ImportError as e:
        raise ImportError(
            "cardisim is required for surrogate runs. "
            "Install Virelion-CardiSim (pip install -e path/to/Virelion-CardiSim) "
            "or use recovery.evaluate_recovery on precomputed state dicts."
        ) from e
    return CardiacSimulator, SimulationConfig, ChallengeEvent, EventSchedule


def _specs_to_schedule(specs: Sequence[CardisimEventSpec | dict[str, Any]], ChallengeEvent, EventSchedule):
    events = []
    for s in specs:
        d = s.as_dict() if isinstance(s, CardisimEventSpec) else dict(s)
        events.append(
            ChallengeEvent(
                name=d["name"],
                onset=float(d.get("onset", 0.0)),
                duration=float(d.get("duration", 1.0)),
                magnitude=float(d.get("magnitude", 1.0)),
                effects=dict(d.get("effects") or {}),
                recovery=float(d.get("recovery", 1.0)),
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
    extra_events: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run CardiSim on DCCP-derived challenge events; return summary dict."""
    CardiacSimulator, SimulationConfig, ChallengeEvent, EventSchedule = _require_cardisim()
    specs = list(scenario_to_event_specs(scenario))
    if extra_events:
        specs_dicts = [s.as_dict() for s in specs] + list(extra_events)
        schedule = _specs_to_schedule(specs_dicts, ChallengeEvent, EventSchedule)
    else:
        schedule = _specs_to_schedule(specs, ChallengeEvent, EventSchedule)
    config = SimulationConfig(duration=duration, dt=dt, n_cells=n_cells, seed=seed)
    sim = CardiacSimulator(config)
    result = sim.run(schedule)
    summary = result.summary()
    return {
        "scenario_id": scenario.scenario_id,
        "events": list(summary.get("events") or []),
        "initial": summary["initial"],
        "final": summary["final"],
        "delta": summary["delta"],
        "maturity_score": summary.get("maturity_score"),
        "cardiac_health_score": summary.get("cardiac_health_score"),
        "config": {
            "duration": duration,
            "dt": dt,
            "n_cells": n_cells,
            "seed": seed,
        },
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
    """Baseline challenge run + challenge+rescue run, then RecoveryReport.

    Returns (challenged_summary, rescued_summary, recovery_report).
    """
    challenged = run_scenario_surrogate(
        scenario, duration=duration, dt=dt, n_cells=n_cells, seed=seed
    )
    rescue_event = dict(rescue) if rescue else {
        "name": "host_resilience_intervention",
        "onset": 2.0,
        "duration": 12.0,
        "magnitude": 1.0,
        "effects": dict(DEFAULT_RESCUE_EFFECTS),
        "recovery": 1.0,
    }
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
