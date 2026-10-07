import math
from pathlib import Path

import pytest

from dccp.scenario import load_scenario


def test_pinned_cardivex_matches_direct_ordinal_math():
    pytest.importorskip("cardivex")
    from dccp.cardivex_bridge import ordinal_axis_distance, ordinal_vector_euclidean

    for a in range(6):
        for b in range(6):
            levels = ["none", "low", "moderate", "substantial", "high", "severe"]
            assert ordinal_axis_distance({"axis": levels[a]}, {"axis": levels[b]}) == pytest.approx(
                abs(a - b)
            )
            assert ordinal_vector_euclidean([a, 0, 5], [b, 5, 0]) == pytest.approx(
                math.sqrt((a - b) ** 2 + 50)
            )


def test_actual_cardisim_rescue_and_determinism():
    pytest.importorskip("cardisim")
    from dccp.surrogate import run_challenge_with_rescue

    scenario = load_scenario(
        Path(__file__).resolve().parents[1] / "scenarios/examples/SCENARIO-001.ordinary-mi.json"
    )
    first = run_challenge_with_rescue(scenario, duration=8.0, dt=0.5, n_cells=8, seed=7)
    second = run_challenge_with_rescue(scenario, duration=8.0, dt=0.5, n_cells=8, seed=7)
    assert first[0] == second[0] and first[1] == second[1]
    assert first[2].as_dict() == second[2].as_dict()
    assert first[1]["final"]["viability"] > first[0]["final"]["viability"]
    assert 0 < first[2].overall_recovery < 1
