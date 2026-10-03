"""Audit helpers for DCCP scenarios.

Ensures every scenario separates realism evidence from model assumptions
and carries an explicit confidence label — required for reconstructibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .scenario import Scenario, validate_scenario


@dataclass(frozen=True)
class AuditResult:
    scenario_id: str
    ok: bool
    schema_errors: list[str]
    policy_warnings: list[str]
    policy_errors: list[str]

    @property
    def passed(self) -> bool:
        return self.ok and not self.policy_errors


def audit_scenario(data: Mapping[str, Any] | Scenario) -> AuditResult:
    """Run schema validation plus DCCP policy checks.

    Policy checks (errors block acceptance):
    - realism_evidence.supported_components must be non-empty
    - scenario_assumptions.model_derived_components should be present
      (warning if empty when confidence is exploratory is acceptable)
    - confidence must be one of the allowed values (already in schema)
    - tissue must be cardiac for the current scope

    Policy checks (warnings):
    - ood_flag true with confidence high is unusual
    - missing temporal_profile when progression is multiphasic
    """
    if isinstance(data, Scenario):
        raw = data.raw
        sid = data.scenario_id
    else:
        raw = dict(data)
        sid = str(raw.get("scenario_id", "<unknown>"))

    schema_errors = validate_scenario(raw)
    policy_errors: list[str] = []
    policy_warnings: list[str] = []

    if schema_errors:
        return AuditResult(
            scenario_id=sid,
            ok=False,
            schema_errors=schema_errors,
            policy_warnings=policy_warnings,
            policy_errors=policy_errors,
        )

    # --- policy ---
    evidence = raw.get("realism_evidence") or {}
    supported = evidence.get("supported_components") or []
    if not supported:
        policy_errors.append("realism_evidence.supported_components must list at least one component")

    assumptions = raw.get("scenario_assumptions") or {}
    model_derived = assumptions.get("model_derived_components") or []
    if not model_derived and raw.get("confidence") == "exploratory":
        policy_warnings.append(
            "exploratory scenarios ideally list model_derived_components for auditability"
        )

    if raw.get("tissue") != "cardiac":
        policy_errors.append("current DCCP scope requires tissue == 'cardiac'")

    if raw.get("ood_flag") and raw.get("confidence") == "high":
        policy_warnings.append(
            "ood_flag=true with confidence=high is unusual; confirm intentional"
        )

    progression = raw.get("progression")
    if progression == "multiphasic" and not raw.get("temporal_profile"):
        policy_warnings.append(
            "multiphasic progression without temporal_profile reduces reconstructibility"
        )

    # Soft check: no keys that look like agent/operational parameters
    forbidden_substrings = (
        "sequence", "genome", "plasmid", "inoculat", "virulence_factor",
        "dose_response", "propagation_protocol", "weapon",
    )
    blob = str(raw).lower()
    for s in forbidden_substrings:
        if s in blob:
            policy_errors.append(
                f"content appears to contain operational/agent-related term '{s}' — "
                "DCCP scenarios may only describe host phenotypic consequences"
            )
            break

    ok = not schema_errors and not policy_errors
    return AuditResult(
        scenario_id=sid,
        ok=ok,
        schema_errors=schema_errors,
        policy_warnings=policy_warnings,
        policy_errors=policy_errors,
    )
