import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("numpy")


def test_independent_real_input_and_label_blindness():
    path = Path(__file__).resolve().parents[1] / "scripts/validate_cpu.py"
    spec = importlib.util.spec_from_file_location("dccp_cpu_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.validate()
    assert report["passed"], report["checks"]
    assert report["empirical_validation"]["status"] == "not_validated"
    # Preserve genuine failures instead of tuning to the library's held-out flags.
    assert report["detector_baselines"]["heuristic"]["ood_confusion"]["fn"] > 0
