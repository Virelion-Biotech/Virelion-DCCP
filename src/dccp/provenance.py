"""Canonical hashing and provenance helpers for scenarios and evaluation runs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from .fingerprint import content_hash


def canonical_hash(obj: Any) -> str:
    """SHA-256 digest of the canonical JSON representation of *obj*."""
    return content_hash(obj)


def scenario_digest(raw: Mapping[str, Any]) -> str:
    """Hash a scenario dict before any runtime-only fields are attached."""
    return canonical_hash(dict(raw))


def run_provenance(
    *,
    scenario_id: str,
    scenario_hash: str,
    tool: str,
    tool_version: str,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a provenance record for an evaluation or surrogate run."""
    if not str(scenario_id).strip():
        raise ValueError("scenario_id must be non-empty")
    if not str(tool).strip():
        raise ValueError("tool must be non-empty")
    if not str(tool_version).strip():
        raise ValueError("tool_version must be non-empty")
    record: dict[str, Any] = {
        "scenario_id": scenario_id,
        "scenario_hash": scenario_hash,
        "tool": tool,
        "tool_version": tool_version,
        "timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    if extra:
        record["extra"] = dict(extra)
    record["record_hash"] = canonical_hash(record)
    return record
