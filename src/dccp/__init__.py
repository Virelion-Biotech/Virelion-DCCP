"""Virelion-DCCP — Defensive Computational Challenge Platform.

Scenario loading, validation, and audit helpers for phenotypic
adversarial challenge profiles used in defensive cardiac AI evaluation.
"""

from .scenario import Scenario, load_scenario, validate_scenario
from .audit import audit_scenario

__version__ = "0.1.0"

__all__ = [
    "Scenario",
    "load_scenario",
    "validate_scenario",
    "audit_scenario",
    "__version__",
]
