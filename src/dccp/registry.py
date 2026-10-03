"""Scenario registry: deterministic discovery, validation metadata and lookup."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

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


def build_registry(
    root: str | Path = "scenarios",
    *,
    exclude_paths: Iterable[str | Path] = (),
) -> list[RegistryEntry]:
    """Discover JSON scenarios and record auditable metadata.

    Paths in *exclude_paths* are resolved and omitted from discovery. This is
    used to prevent generated registries from recursively indexing themselves.
    """
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(f"scenario root does not exist: {root}")
    root_resolved = root.resolve()
    excluded = {Path(path).resolve() for path in exclude_paths}

    entries: list[RegistryEntry] = []
    for path in sorted(root.rglob("*.json")):
        path_resolved = path.resolve()
        if path_resolved in excluded:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"unable to read scenario JSON {path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise TypeError(f"scenario JSON must be an object: {path}")
        scenario = payload.get("scenario") or payload
        if not isinstance(scenario, dict):
            raise TypeError(f"scenario payload must be an object: {path}")
        result = audit_scenario(scenario)
        try:
            relative_path = path_resolved.relative_to(root_resolved).as_posix()
        except ValueError as exc:
            raise ValueError(f"scenario path escaped root: {path}") from exc
        scenario_id = str(scenario.get("scenario_id", path.stem)).strip()
        entries.append(
            RegistryEntry(
                scenario_id=scenario_id,
                path=relative_path,
                title=str(scenario.get("title", "")),
                ood=bool(scenario.get("ood_flag", False)),
                confidence=str(scenario.get("confidence", "")),
                audit_passed=result.passed,
                content_sha256=file_hash(path_resolved),
            )
        )

    seen: set[str] = set()
    duplicates: list[str] = []
    for entry in entries:
        if entry.scenario_id in seen:
            duplicates.append(entry.scenario_id)
        seen.add(entry.scenario_id)
    if duplicates:
        raise ValueError(f"duplicate scenario_id values in registry: {', '.join(sorted(set(duplicates)))}")
    return entries


def write_registry(root: str | Path, output: str | Path) -> dict[str, Any]:
    output = Path(output)
    entries = build_registry(root, exclude_paths=(output,))
    payload = {
        "registry_version": "1",
        "root": Path(root).as_posix(),
        "n_entries": len(entries),
        "n_audited": sum(entry.audit_passed for entry in entries),
        "entries": [entry.as_dict() for entry in entries],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return payload


def find_scenario(root: str | Path, scenario_id: str) -> RegistryEntry:
    scenario_id = str(scenario_id).strip()
    if not scenario_id:
        raise ValueError("scenario_id must be non-empty")
    for entry in build_registry(root):
        if entry.scenario_id == scenario_id:
            return entry
    raise KeyError(f"Unknown scenario_id: {scenario_id}")
