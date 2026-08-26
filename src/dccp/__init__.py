"""Virelion-DCCP — Defensive Computational Challenge Platform.

Scenario library, audit, CardiSim bridge, defensive detectors, recovery
evaluation, and challenge-set materialization for phenotypic adversarial
challenges on cardiac models.
"""

from .scenario import Scenario, load_scenario, validate_scenario
from .audit import audit_scenario
from .evaluate import DefensiveAssessment, assess_scenario
from .provenance import canonical_hash, scenario_digest, run_provenance
from .cardisim_bridge import (
    CardisimEventSpec,
    axes_to_effects,
    scenario_to_event_specs,
    scenario_to_cardisim_payload,
)
from .recovery import RecoveryReport, evaluate_recovery, build_rescue_event_dict
from .detectors import Detector, HeuristicDetector, PrototypeDetector
from .library import load_library, materialize_challenge_set, write_challenge_set

__version__ = "0.2.0"

__all__ = [
    "Scenario",
    "load_scenario",
    "validate_scenario",
    "audit_scenario",
    "DefensiveAssessment",
    "assess_scenario",
    "canonical_hash",
    "scenario_digest",
    "run_provenance",
    "CardisimEventSpec",
    "axes_to_effects",
    "scenario_to_event_specs",
    "scenario_to_cardisim_payload",
    "RecoveryReport",
    "evaluate_recovery",
    "build_rescue_event_dict",
    "Detector",
    "HeuristicDetector",
    "PrototypeDetector",
    "load_library",
    "materialize_challenge_set",
    "write_challenge_set",
    "__version__",
]
