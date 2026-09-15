"""Scenario registry: deterministic discovery, validation metadata and lookup."""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
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
    """Discover JSON scenarios and record only auditable metadata."""
    root = Path(root)
    entries: list[RegistryEntry] = []
    for path in sorted(root.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        result = audit_scenario(payload)
        scenario = payload.get("scenario") or payload
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
    return entries


def write_registry(root: str | Path, output: str | Path) -> dict[str, Any]:
    entries = build_registry(root)
    payload = {
        "registry_version": "1",
        "root": str(root),
        "n_entries": len(entries),
        "n_audited": sum(e.audit_passed for e in entries),
        "entries": [e.as_dict() for e in entries],
    }
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def find_scenario(root: str | Path, scenario_id: str) -> RegistryEntry:
    for entry in build_registry(root):
        if entry.scenario_id == scenario_id:
            return entry
    raise KeyError(f"Unknown scenario_id: {scenario_id}")
