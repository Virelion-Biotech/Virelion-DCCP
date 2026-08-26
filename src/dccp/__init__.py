"""Virelion-DCCP — Defensive Computational Challenge Platform.

Scenario library, host multi-omics → phenotypic axes, CardiSim bridge,
defensive detectors, recovery evaluation, and challenge-set materialization.
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
from .omics_map import (
    map_module_scores_to_axes,
    draft_scenario_from_scores,
    score_to_ordinal,
    load_host_evidence_panel,
)
from .host_features import extract_host_features, HostProfileFeatures
from .accession_provenance import panel_accession_records, evidence_bundle_for_accessions

__version__ = "0.3.0"

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
    "map_module_scores_to_axes",
    "draft_scenario_from_scores",
    "score_to_ordinal",
    "load_host_evidence_panel",
    "extract_host_features",
    "HostProfileFeatures",
    "panel_accession_records",
    "evidence_bundle_for_accessions",
    "__version__",
]
