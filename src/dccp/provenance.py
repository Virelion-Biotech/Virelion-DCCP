"""Canonical hashing and provenance helpers for scenarios and evaluation runs."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping


def _canonical_bytes(obj: Any) -> bytes:
    """Deterministic JSON serialization (sorted keys, compact separators)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def canonical_hash(obj: Mapping[str, Any] | list[Any] | dict[str, Any]) -> str:
    """SHA-256 hex digest of the canonical JSON form of *obj*."""
    return hashlib.sha256(_canonical_bytes(obj)).hexdigest()


def scenario_digest(raw: Mapping[str, Any]) -> str:
    """Hash a scenario dict (typically the raw JSON before runtime fields)."""
    # Exclude non-semantic keys if present later; for now hash full structure.
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
    record: dict[str, Any] = {
        "scenario_id": scenario_id,
        "scenario_hash": scenario_hash,
        "tool": tool,
        "tool_version": tool_version,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if extra:
        record["extra"] = dict(extra)
    record["record_hash"] = canonical_hash(record)
    return record
