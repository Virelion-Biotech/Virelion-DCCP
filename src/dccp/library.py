"""Scenario library index, load-all, and CardiBench-oriented materialization."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from .audit import audit_scenario
from .evaluate import assess_scenario
from .provenance import scenario_digest
from .scenario import Scenario, load_scenario


@dataclass(frozen=True)
class LibraryEntry:
    path: Path
    scenario: Scenario
    digest: str


def discover_scenarios(root: str | Path) -> list[Path]:
    root = Path(root)
    return sorted(p for p in root.rglob("*.json") if p.is_file())


def load_library(root: str | Path = "scenarios") -> list[LibraryEntry]:
    entries: list[LibraryEntry] = []
    for path in discover_scenarios(root):
        sc = load_scenario(path)
        raw = json.loads(path.read_text(encoding="utf-8"))
        entries.append(LibraryEntry(path=path, scenario=sc, digest=scenario_digest(raw)))
    return entries


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
    for e in entries:
        if e.scenario.ood_flag and not include_ood:
            continue
        assessment = assess_scenario(e.scenario)
        audit = audit_scenario(e.scenario)
        cases.append(
            {
                "scenario_id": e.scenario.scenario_id,
                "path": str(e.path),
                "digest": e.digest,
                "title": e.scenario.title,
                "ood_flag": e.scenario.ood_flag,
                "confidence": e.scenario.confidence,
                "phenotypic_axes": dict(e.scenario.phenotypic_axes),
                "assessment": assessment.as_dict(),
                "audit_passed": audit.passed,
                "ladder_role": _ladder_role(e.scenario),
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
        "n_ood": sum(1 for c in cases if c["ood_flag"]),
        "cases": cases,
    }
    # digest over cases without nested assessment volatility? include full for audit
    from .provenance import canonical_hash

    payload["set_hash"] = canonical_hash({"cases": cases, "version": payload["version"]})
    return payload


def _ladder_role(sc: Scenario) -> str:
    if sc.ood_flag:
        return "novel_heldout"
    if sc.confidence == "exploratory":
        return "atypical"
    sid = sc.scenario_id
    if sid.endswith("001") or "ordinary" in (sc.title or "").lower() or "mi" in (sc.title or "").lower():
        return "ordinary_pathology"
    if "hypoxia" in (sc.title or "").lower():
        return "ordinary_pathology"
    return "ordinary_or_atypical"


def write_challenge_set(path: str | Path, root: str | Path = "scenarios") -> Path:
    path = Path(path)
    payload = materialize_challenge_set(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
