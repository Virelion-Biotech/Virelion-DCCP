"""Map host multi-omics module scores to DCCP ordinal phenotypic axes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from .host_modules import DCCP_AXIS_MODULES, ORDINAL_LEVELS, module_coverage
from .provenance import canonical_hash

DEFAULT_THRESHOLDS: tuple[float, ...] = (0.1, 0.25, 0.45, 0.65, 0.85)


def _validate_thresholds(thresholds: Sequence[float]) -> tuple[float, ...]:
    values = tuple(float(t) for t in thresholds)
    expected = len(ORDINAL_LEVELS) - 1
    if len(values) != expected:
        raise ValueError(f"thresholds must contain exactly {expected} values")
    if any(not 0.0 <= t <= 1.0 for t in values):
        raise ValueError("thresholds must all be within [0, 1]")
    if any(left >= right for left, right in zip(values, values[1:])):
        raise ValueError("thresholds must be strictly increasing")
    return values


def score_to_ordinal(score: float, thresholds: Sequence[float] = DEFAULT_THRESHOLDS) -> str:
    """Map a [0, 1] score to none < low < ... < severe."""
    values = _validate_thresholds(thresholds)
    s = max(0.0, min(1.0, float(score)))
    for i, threshold in enumerate(values):
        if s < threshold:
            return ORDINAL_LEVELS[i]
    return ORDINAL_LEVELS[-1]


def ordinal_to_rank(level: str) -> int:
    try:
        return ORDINAL_LEVELS.index(level)
    except ValueError:
        raise ValueError(f"unknown ordinal level: {level!r}") from None


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
    """Convert continuous host module scores to DCCP ordinal axes."""
    values = _validate_thresholds(thresholds)
    if not 0.0 <= float(min_coverage) <= 1.0:
        raise ValueError("min_coverage must be within [0, 1]")
    continuous: dict[str, float] = {}
    ordinal: dict[str, str] = {}
    notes: list[str] = []
    coverage = (
        module_coverage(genes_present, DCCP_AXIS_MODULES)
        if genes_present is not None
        else {axis: 1.0 for axis in DCCP_AXIS_MODULES}
    )

    for axis in DCCP_AXIS_MODULES:
        raw = float(scores.get(axis, 0.0))
        continuous[axis] = max(0.0, min(1.0, raw))
        cov = coverage[axis]
        if genes_present is not None and cov < min_coverage:
            ordinal[axis] = "none"
            notes.append(f"{axis}: coverage {cov:.2f} < {min_coverage}; ordinal forced to none")
        else:
            ordinal[axis] = score_to_ordinal(continuous[axis], values)

    return AxisScoreResult(
        continuous=continuous,
        ordinal=ordinal,
        coverage=coverage,
        thresholds=values,
        notes=notes,
    )


def load_host_evidence_panel(path: str | Path | None = None) -> dict[str, Any]:
    candidates: list[Path] = []
    if path:
        candidates.append(Path(path))
    here = Path(__file__).resolve()
    candidates.extend(
        [
            here.parents[2] / "data" / "reference" / "host_evidence_panel.json",
            here.parent / "data" / "host_evidence_panel.json",
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            with candidate.open(encoding="utf-8") as handle:
                return json.load(handle)
    raise FileNotFoundError("host_evidence_panel.json not found")


def realism_evidence_for_axes(
    ordinal_axes: Mapping[str, str],
    *,
    panel: Mapping[str, Any] | None = None,
    min_level: str = "low",
) -> dict[str, Any]:
    """Build realism evidence and accession references from the evidence panel."""
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
        for accession in meta.get("accessions") or []:
            if accession not in accessions:
                accessions.append(accession)
    return {
        "supported_components": supported or ["host cardiac phenotypic proxy scores"],
        "references": [
            f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={accession}"
            for accession in accessions
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
    """Build a JSON-Schema-valid scenario dict from host module scores."""
    mapped = map_module_scores_to_axes(scores, genes_present=genes_present)
    axes = dict(mapped.ordinal)
    axes["recovery_profile"] = recovery_profile
    evidence = realism_evidence_for_axes(axes)
    return {
        "scenario_id": scenario_id,
        "title": title,
        "description": "Host multi-omics-derived phenotypic profile. Axes reflect host gene-module proxies only.",
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
            "notes": model_notes or "Continuous-to-ordinal mapping is heuristic pending dataset-specific calibration.",
        },
        "confidence": confidence,
        "ood_flag": bool(ood_flag),
        "version": "1.0.0",
    }


def accession_digest(accession: str, extra: Mapping[str, Any] | None = None) -> str:
    """Stable hash for an accession-level provenance record (metadata only)."""
    accession = str(accession).strip()
    if not accession:
        raise ValueError("accession must be non-empty")
    payload: dict[str, Any] = {"accession": accession, "kind": "host_omics_accession"}
    if extra:
        payload["extra"] = dict(extra)
    return canonical_hash(payload)
