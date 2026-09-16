"""Scenario library index, load-all, and CardiBench-oriented materialization."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from .audit import audit_scenario
from .evaluate import assess_scenario
from .provenance import canonical_hash, scenario_digest
from .scenario import Scenario, load_scenario


@dataclass(frozen=True)
class LibraryEntry:
    path: Path
    scenario: Scenario
    digest: str


def discover_scenarios(root: str | Path) -> list[Path]:
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(f"scenario root does not exist: {root}")
    return sorted(path for path in root.rglob("*.json") if path.is_file())


def load_library(root: str | Path = "scenarios") -> list[LibraryEntry]:
    return [
        LibraryEntry(path=path, scenario=(scenario := load_scenario(path)), digest=scenario_digest(scenario.raw))
        for path in discover_scenarios(root)
    ]


def iter_library(root: str | Path = "scenarios") -> Iterator[LibraryEntry]:
    yield from load_library(root)


def materialize_challenge_set(
    root: str | Path = "scenarios",
    *,
    include_ood: bool = True,
) -> dict[str, Any]:
    """Build a versioned, hashed challenge set for defensive evaluation / CardiBench hand-off.

    Does not redistribute biological data — only phenotypic scenario metadata
    and assessment labels derived from the library.
    """
    entries = load_library(root)
    cases = []
    for entry in entries:
        if entry.scenario.ood_flag and not include_ood:
            continue
        audit = audit_scenario(entry.scenario)
        assessment = assess_scenario(entry.scenario)
        cases.append(
            {
                "scenario_id": entry.scenario.scenario_id,
                "path": str(entry.path),
                "digest": entry.digest,
                "title": entry.scenario.title,
                "ood_flag": entry.scenario.ood_flag,
                "confidence": entry.scenario.confidence,
                "phenotypic_axes": dict(entry.scenario.phenotypic_axes),
                "assessment": assessment.as_dict(),
                "audit_passed": audit.passed,
                "ladder_role": _ladder_role(entry.scenario),
            }
        )

    payload = {
        "name": "dccp-cardiac-challenge-set",
        "version": "1.0.0",
        "description": (
            "Phenotypic adversarial challenge set for defensive cardiac AI evaluation. "
            "Host-response axes only; no agent construction parameters."
        ),
        "n_cases": len(cases),
        "n_ood": sum(1 for case in cases if case["ood_flag"]),
        "cases": cases,
    }
    payload["set_hash"] = canonical_hash({"cases": cases, "version": payload["version"]})
    return payload


def _ladder_role(sc: Scenario) -> str:
    if sc.ood_flag:
        return "novel_heldout"
    if sc.confidence == "exploratory":
        return "atypical"
    title = (sc.title or "").lower()
    if sc.scenario_id.endswith("001") or "ordinary" in title or "mi" in title:
        return "ordinary_pathology"
    if "hypoxia" in title:
        return "ordinary_pathology"
    return "ordinary_or_atypical"


def write_challenge_set(path: str | Path, root: str | Path = "scenarios") -> Path:
    path = Path(path)
    payload = materialize_challenge_set(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return path
