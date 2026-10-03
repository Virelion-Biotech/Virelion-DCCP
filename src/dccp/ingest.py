"""Safe ingestion primitives with explicit normalization and provenance hooks."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .fingerprint import file_hash


def _record_count(payload: Any) -> int:
    if isinstance(payload, list):
        return len(payload)
    return 1 if payload is not None else 0


@dataclass(frozen=True)
class IngestedArtifact:
    source: str
    source_sha256: str
    record_count: int
    payload: Any
    transform: str


def load_json(path: str | Path) -> IngestedArtifact:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return IngestedArtifact(
        source=path.as_posix(),
        source_sha256=file_hash(path),
        record_count=_record_count(payload),
        payload=payload,
        transform="identity-json",
    )


def normalize_records(
    artifact: IngestedArtifact,
    transform: Callable[[Any], Any],
    *,
    transform_name: str,
) -> IngestedArtifact:
    """Apply a named deterministic transformation while retaining source identity."""
    name = transform_name.strip()
    if not name:
        raise ValueError("transform_name must be non-empty")
    payload = transform(artifact.payload)
    return IngestedArtifact(
        source=artifact.source,
        source_sha256=artifact.source_sha256,
        record_count=_record_count(payload),
        payload=payload,
        transform=name,
    )
