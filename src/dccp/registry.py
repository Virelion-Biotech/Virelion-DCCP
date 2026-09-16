"""Scenario registry: deterministic discovery, validation metadata and lookup."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .audit import audit_scenario
from .fingerprint import file_hash


@dataclass(frozen=True)
class RegistryEntry:
    scenario_id: str
    path: str
    title: str
    ood: bool
    confidence: str
    audit_passed: bool
    content_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_registry(root: str | Path = "scenarios") -> list[RegistryEntry]:
    """Discover JSON scenarios and record auditable metadata.

    Invalid/unreadable JSON is surfaced rather than silently omitted, so a
    release cannot accidentally pass because a scenario disappeared from the registry.
    """
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(f"scenario root does not exist: {root}")

    entries: list[RegistryEntry] = []
    for path in sorted(root.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"unable to read scenario JSON {path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"scenario JSON must be an object: {path}")
        result = audit_scenario(payload)
        scenario = payload.get("scenario") or payload
        if not isinstance(scenario, dict):
            raise ValueError(f"scenario payload must be an object: {path}")
        scenario_id = str(scenario.get("scenario_id", path.stem))
        entries.append(
            RegistryEntry(
                scenario_id=scenario_id,
                path=path.as_posix(),
                title=str(scenario.get("title", "")),
                ood=bool(scenario.get("ood_flag", False)),
                confidence=str(scenario.get("confidence", "")),
                audit_passed=result.passed,
                content_sha256=file_hash(path),
            )
        )

    ids = [entry.scenario_id for entry in entries]
    if len(ids) != len(set(ids)):
        duplicates = sorted({sid for sid in ids if ids.count(sid) > 1})
        raise ValueError(f"duplicate scenario_id values in registry: {', '.join(duplicates)}")
    return entries


def write_registry(root: str | Path, output: str | Path) -> dict[str, Any]:
    entries = build_registry(root)
    payload = {
        "registry_version": "1",
        "root": Path(root).as_posix(),
        "n_entries": len(entries),
        "n_audited": sum(entry.audit_passed for entry in entries),
        "entries": [entry.as_dict() for entry in entries],
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def find_scenario(root: str | Path, scenario_id: str) -> RegistryEntry:
    for entry in build_registry(root):
        if entry.scenario_id == scenario_id:
            return entry
    raise KeyError(f"Unknown scenario_id: {scenario_id}")
