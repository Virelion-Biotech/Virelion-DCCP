"""Artifact provenance records for reproducible DCCP outputs."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .fingerprint import content_hash

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _require_text(value: str, name: str) -> str:
    value = str(value).strip()
    if not value:
        raise ValueError(f"{name} must be non-empty")
    return value


@dataclass(frozen=True)
class ArtifactProvenance:
    artifact_id: str
    artifact_type: str
    content_hash: str
    schema_version: str | None = None
    producer: str = "virelion-dccp"
    producer_version: str | None = None
    created_at: str = field(default_factory=utc_now)
    inputs: tuple[str, ...] = ()
    parameters: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_text(self.artifact_id, "artifact_id")
        _require_text(self.artifact_type, "artifact_type")
        if not _SHA256_RE.fullmatch(str(self.content_hash).strip()):
            raise ValueError("content_hash must be a 64-character hexadecimal SHA-256 digest")
        if self.schema_version is not None and not str(self.schema_version).strip():
            raise ValueError("schema_version must be non-empty when provided")
        _require_text(self.producer, "producer")
        if self.producer_version is not None and not str(self.producer_version).strip():
            raise ValueError("producer_version must be non-empty when provided")
        if not all(str(item).strip() for item in self.inputs):
            raise ValueError("inputs must contain only non-empty strings")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def for_json(
        cls,
        artifact_id: str,
        artifact_type: str,
        payload: Any,
        *,
        schema_version: str | None = None,
        producer_version: str | None = None,
        inputs: tuple[str, ...] = (),
        parameters: dict[str, Any] | None = None,
    ) -> "ArtifactProvenance":
        return cls(
            artifact_id=_require_text(artifact_id, "artifact_id"),
            artifact_type=_require_text(artifact_type, "artifact_type"),
            content_hash=content_hash(payload),
            schema_version=schema_version,
            producer_version=producer_version,
            inputs=tuple(str(item).strip() for item in inputs),
            parameters=dict(parameters or {}),
        )
