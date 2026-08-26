"""Map host multi-omics module scores → DCCP ordinal phenotypic axes.

Input is always *host* continuous scores (e.g. mean module expression z/min-max).
No pathogen sequences or agent parameters are accepted or emitted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from .host_modules import DCCP_AXIS_MODULES, ORDINAL_LEVELS, module_coverage
from .provenance import canonical_hash

# Default thresholds on [0, 1] scaled module scores → ordinal levels.
# Tunable; documented as heuristic, not calibrated clinical cut-points.
DEFAULT_THRESHOLDS: tuple[float, ...] = (0.1, 0.25, 0.45, 0.65, 0.85)


def score_to_ordinal(score: float, thresholds: Sequence[float] = DEFAULT_THRESHOLDS) -> str:
    """Map a [0, 1] score to none < low < … < severe."""
    s = max(0.0, min(1.0, float(score)))
    for i, t in enumerate(thresholds):
        if s < t:
            return ORDINAL_LEVELS[i]
    return ORDINAL_LEVELS[-1]


def ordinal_to_rank(level: str) -> int:
    try:
        return ORDINAL_LEVELS.index(level)
    except ValueError:
        return 0


@dataclass
class AxisScoreResult:
    continuous: dict[str, float]
    ordinal: dict[str, str]
    coverage: dict[str, float]
    thresholds: tuple[float, ...]
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "continuous": {k: round(v, 4) for k, v in self.continuous.items()},
            "ordinal": dict(self.ordinal),
            "coverage": {k: round(v, 4) for k, v in self.coverage.items()},
            "thresholds": list(self.thresholds),
            "notes": list(self.notes),
        }


def map_module_scores_to_axes(
    scores: Mapping[str, float],
    *,
    genes_present: Sequence[str] | None = None,
    thresholds: Sequence[float] = DEFAULT_THRESHOLDS,
    min_coverage: float = 0.3,
) -> AxisScoreResult:
    """Convert continuous axis module scores to DCCP ordinal axes.

    ``scores`` keys should match DCCP axis names (inflammatory, …).
    Missing axes default to 0.0 → "none".
    """
    continuous: dict[str, float] = {}
    ordinal: dict[str, str] = {}
    notes: list[str] = []
    coverage = module_coverage(genes_present or [], DCCP_AXIS_MODULES) if genes_present is not None else {
        ax: 1.0 for ax in DCCP_AXIS_MODULES
    }

    for axis in DCCP_AXIS_MODULES:
        raw = float(scores.get(axis, 0.0))
        continuous[axis] = max(0.0, min(1.0, raw))
        cov = coverage.get(axis, 1.0)
        if genes_present is not None and cov < min_coverage:
            ordinal[axis] = "none"
            notes.append(f"{axis}: coverage {cov:.2f} < {min_coverage}; ordinal forced to none")
        else:
            ordinal[axis] = score_to_ordinal(continuous[axis], thresholds)

    # recovery_profile is not scored from modules by default
    return AxisScoreResult(
        continuous=continuous,
        ordinal=ordinal,
        coverage=coverage,
        thresholds=tuple(thresholds),
        notes=notes,
    )


def load_host_evidence_panel(path: str | Path | None = None) -> dict[str, Any]:
    candidates = []
    if path:
        candidates.append(Path(path))
    here = Path(__file__).resolve()
    candidates.append(here.parents[2] / "data" / "reference" / "host_evidence_panel.json")
    candidates.append(here.parent / "data" / "host_evidence_panel.json")
    for p in candidates:
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError("host_evidence_panel.json not found")


def realism_evidence_for_axes(
    ordinal_axes: Mapping[str, str],
    *,
    panel: Mapping[str, Any] | None = None,
    min_level: str = "low",
) -> dict[str, Any]:
    """Build realism_evidence.supported_components + accession refs from the panel."""
    panel = panel or load_host_evidence_panel()
    axis_ev = panel.get("axis_evidence") or {}
    min_rank = ordinal_to_rank(min_level)
    supported: list[str] = []
    accessions: list[str] = []
    for axis, level in ordinal_axes.items():
        if axis == "recovery_profile":
            continue
        if ordinal_to_rank(level) < min_rank:
            continue
        meta = axis_ev.get(axis) or {}
        supported.append(f"{axis} host-response programs (public multi-omics)")
        for acc in meta.get("accessions") or []:
            if acc not in accessions:
                accessions.append(acc)
    return {
        "supported_components": supported or ["host cardiac phenotypic proxy scores"],
        "references": [
            f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={a}" for a in accessions
        ],
        "proxy_notes": (
            "Ordinal axes derived from host gene-module scores; "
            "accessions are public GEO metadata anchors, not redistributed matrices."
        ),
        "accessions": accessions,
    }


def draft_scenario_from_scores(
    scores: Mapping[str, float],
    *,
    scenario_id: str,
    title: str,
    genes_present: Sequence[str] | None = None,
    ood_flag: bool = False,
    confidence: str = "moderate",
    onset: str = "rapid",
    progression: str = "monotonic",
    recovery_profile: str = "typical",
    model_notes: str = "",
) -> dict[str, Any]:
    """Build a schema-shaped scenario dict from host module scores + evidence panel."""
    mapped = map_module_scores_to_axes(scores, genes_present=genes_present)
    axes = dict(mapped.ordinal)
    axes["recovery_profile"] = recovery_profile
    evidence = realism_evidence_for_axes(axes)
    draft = {
        "scenario_id": scenario_id,
        "title": title,
        "description": (
            "Host multi-omics-derived phenotypic profile. "
            "Axes reflect host gene-module proxies only."
        ),
        "tissue": "cardiac",
        "onset": onset,
        "progression": progression,
        "phenotypic_axes": axes,
        "realism_evidence": {
            "supported_components": evidence["supported_components"],
            "references": evidence["references"],
            "proxy_notes": evidence["proxy_notes"],
        },
        "scenario_assumptions": {
            "model_derived_components": [
                "ordinal thresholds on continuous module scores",
                "module gene membership as proxy for axis activity",
            ],
            "interaction_hypotheses": [],
            "notes": model_notes
            or "Continuous→ordinal mapping is heuristic pending dataset-specific calibration.",
        },
        "confidence": confidence,
        "ood_flag": ood_flag,
        "version": "1.0.0",
        "_mapping": mapped.as_dict(),
        "_evidence_accessions": evidence.get("accessions", []),
    }
    return draft


def accession_digest(accession: str, extra: Mapping[str, Any] | None = None) -> str:
    """Stable hash for an accession-level provenance record (metadata only)."""
    payload: dict[str, Any] = {"accession": accession, "kind": "host_omics_accession"}
    if extra:
        payload["extra"] = dict(extra)
    return canonical_hash(payload)
