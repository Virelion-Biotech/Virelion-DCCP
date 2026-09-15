"""Safe ingestion primitives with explicit normalization and provenance hooks."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .fingerprint import file_hash


@dataclass(frozen=True)
class IngestedArtifact:
    source: str
    source_sha256: str
    record_count: int
    payload: Any
    transform: str


def load_json(path: str | Path) -> IngestedArtifact:
    path = Path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    count = len(payload) if isinstance(payload, (list, dict)) else 1
    return IngestedArtifact(path.as_posix(), file_hash(path), count, payload, "identity-json")


def normalize_records(
    artifact: IngestedArtifact,
    transform: Callable[[Any], Any],
    *,
    transform_name: str,
) -> IngestedArtifact:
    """Apply a named deterministic transformation while retaining source identity."""
    if not transform_name.strip():
        raise ValueError("transform_name must be non-empty")
    payload = transform(artifact.payload)
    count = len(payload) if isinstance(payload, (list, dict)) else 1
    return IngestedArtifact(
        source=artifact.source,
        source_sha256=artifact.source_sha256,
        record_count=count,
        payload=payload,
        transform=transform_name,
    )
