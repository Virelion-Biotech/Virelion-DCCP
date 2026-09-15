"""Release-readiness gates for challenge sets and benchmark artifacts."""
from __future__ import annotations

from typing import Any


def release_gate(registry: dict[str, Any], *, require_all_audited: bool = True) -> dict[str, Any]:
    entries = registry.get("entries", [])
    failures = []
    for entry in entries:
        if require_all_audited and not entry.get("audit_passed", False):
            failures.append({"scenario_id": entry.get("scenario_id"), "reason": "audit_failed"})
        if not entry.get("content_sha256"):
            failures.append({"scenario_id": entry.get("scenario_id"), "reason": "missing_fingerprint"})
    return {
        "passed": not failures and bool(entries),
        "n_entries": len(entries),
        "failures": failures,
    }
