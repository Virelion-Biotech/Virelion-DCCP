"""Artifact provenance records inspired by reproducible scientific pipelines."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .fingerprint import content_hash


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            content_hash=content_hash(payload),
            schema_version=schema_version,
            producer_version=producer_version,
            inputs=inputs,
            parameters=parameters or {},
        )
