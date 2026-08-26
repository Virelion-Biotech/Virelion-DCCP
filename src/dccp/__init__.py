"""Virelion-DCCP — Defensive Computational Challenge Platform.

Scenario loading, validation, audit, CardiSim bridge, defensive assessment,
and provenance helpers for phenotypic adversarial challenge profiles.
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

__version__ = "0.1.0"

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
    "__version__",
]
