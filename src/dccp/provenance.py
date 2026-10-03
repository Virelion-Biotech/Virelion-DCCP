"""Canonical hashing and provenance helpers for scenarios and evaluation runs."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Mapping

from .fingerprint import content_hash

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


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
    scenario_id = str(scenario_id).strip()
    scenario_hash = str(scenario_hash).strip()
    tool = str(tool).strip()
    tool_version = str(tool_version).strip()
    if not scenario_id:
        raise ValueError("scenario_id must be non-empty")
    if not _SHA256_RE.fullmatch(scenario_hash):
        raise ValueError("scenario_hash must be a 64-character hexadecimal SHA-256 digest")
    if not tool:
        raise ValueError("tool must be non-empty")
    if not tool_version:
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
