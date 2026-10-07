"""Map host multi-omics module scores to DCCP ordinal phenotypic axes."""

from __future__ import annotations

from .serialization import strict_loads

import itertools
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .host_modules import DCCP_AXIS_MODULES, ORDINAL_LEVELS, module_coverage
from .provenance import canonical_hash

DEFAULT_THRESHOLDS: tuple[float, ...] = (0.1, 0.25, 0.45, 0.65, 0.85)


def _validate_thresholds(thresholds: Sequence[float]) -> tuple[float, ...]:
    values = tuple(float(threshold) for threshold in thresholds)
    expected = len(ORDINAL_LEVELS) - 1
    if len(values) != expected:
        raise ValueError(f"thresholds must contain exactly {expected} values")
    if any(not math.isfinite(value) or not 0.0 <= value <= 1.0 for value in values):
        raise ValueError("thresholds must all be finite and within [0, 1]")
    if any(left >= right for left, right in itertools.pairwise(values)):
        raise ValueError("thresholds must be strictly increasing")
    return values


def score_to_ordinal(score: float, thresholds: Sequence[float] = DEFAULT_THRESHOLDS) -> str:
    """Map a finite [0, 1] score to none < low < ... < severe."""
    values = _validate_thresholds(thresholds)
    score = float(score)
    if not math.isfinite(score):
        raise ValueError("score must be finite")
    if not 0 <= score <= 1:
        raise ValueError("score must lie within [0, 1]")
    for index, threshold in enumerate(values):
        if score < threshold:
            return ORDINAL_LEVELS[index]
    return ORDINAL_LEVELS[-1]


def ordinal_to_rank(level: str) -> int:
    try:
        return ORDINAL_LEVELS.index(level)
    except ValueError:
        raise ValueError(f"unknown ordinal level: {level!r}") from None


@dataclass
class AxisScoreResult:
    continuous: dict[str, float | None]
    ordinal: dict[str, str | None]
    coverage: dict[str, float | None]
    thresholds: tuple[float, ...]
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "continuous": {
                key: None if value is None else round(value, 4)
                for key, value in self.continuous.items()
            },
            "ordinal": dict(self.ordinal),
            "coverage": {
                key: None if value is None else round(value, 4)
                for key, value in self.coverage.items()
            },
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
    min_coverage = float(min_coverage)
    if not math.isfinite(min_coverage) or not 0.0 <= min_coverage <= 1.0:
        raise ValueError("min_coverage must be finite and within [0, 1]")
    unknown = set(scores) - set(DCCP_AXIS_MODULES)
    if unknown:
        raise ValueError(f"Unknown score axes: {sorted(unknown)}")
    continuous: dict[str, float | None] = {}
    ordinal: dict[str, str | None] = {}
    notes: list[str] = []
    coverage = (
        module_coverage(genes_present, DCCP_AXIS_MODULES)
        if genes_present is not None
        else {axis: None for axis in DCCP_AXIS_MODULES}
    )

    for axis in DCCP_AXIS_MODULES:
        if axis not in scores or scores[axis] is None:
            continuous[axis] = None
            ordinal[axis] = None
            notes.append(f"{axis}: score unavailable")
            continue
        raw = float(scores[axis])
        if not math.isfinite(raw):
            raise ValueError(f"score for {axis} must be finite")
        if not 0 <= raw <= 1:
            raise ValueError("Scores must lie within [0, 1]")
        continuous[axis] = raw
        cov = coverage[axis]
        if genes_present is not None and cov < min_coverage:
            ordinal[axis] = None
            notes.append(
                f"{axis}: coverage {cov:.2f} < {min_coverage}; axis unavailable, not absence"
            )
        else:
            ordinal[axis] = score_to_ordinal(continuous[axis], values)

    return AxisScoreResult(continuous, ordinal, coverage, values, notes)


def load_host_evidence_panel(path: str | Path | None = None) -> dict[str, Any]:
    candidates: list[Path] = []
    if path:
        explicit = Path(path)
        if not explicit.is_file():
            raise FileNotFoundError(explicit)
        candidates.append(explicit)
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
                panel = strict_loads(handle.read())
            if not isinstance(panel, dict):
                raise ValueError(f"host evidence panel must be an object: {candidate}")
            return panel
    raise FileNotFoundError("host_evidence_panel.json not found")


def realism_evidence_for_axes(
    ordinal_axes: Mapping[str, str],
    *,
    panel: Mapping[str, Any] | None = None,
    min_level: str = "low",
) -> dict[str, Any]:
    """Build realism evidence without overstating empirical support."""
    panel = panel or load_host_evidence_panel()
    axis_ev = panel.get("axis_evidence") or {}
    min_rank = ordinal_to_rank(min_level)
    supported: list[str] = []
    proxy_only: list[str] = []
    accessions: list[str] = []
    for axis, level in ordinal_axes.items():
        if axis == "recovery_profile":
            continue
        if ordinal_to_rank(level) < min_rank:
            continue
        meta = axis_ev.get(axis) or {}
        axis_accessions = [
            str(accession).strip()
            for accession in meta.get("accessions") or []
            if str(accession).strip()
        ]
        if axis_accessions:
            proxy_only.append(
                f"{axis} proxy; linked accessions are candidate evidence, not analyzed validation"
            )
            for accession in axis_accessions:
                if accession not in accessions:
                    accessions.append(accession)
        else:
            proxy_only.append(f"{axis} host-response proxy (no linked panel accession)")
    return {
        "supported_components": supported or ["host cardiac phenotypic proxy scores"],
        "proxy_only_components": proxy_only,
        "references": [
            f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={accession}"
            for accession in accessions
        ],
        "proxy_notes": "Ordinal axes derive from host gene-module scores. Linked accessions are metadata-verified candidate sources only. No expression analysis or phenotype calibration is established by this mapping.",
        "accessions": accessions,
    }


def draft_scenario_from_scores(
    scores: Mapping[str, float],
    *,
    scenario_id: str,
    title: str,
    genes_present: Sequence[str] | None = None,
    ood_flag: bool = False,
    confidence: str = "exploratory",
    onset: str = "rapid",
    progression: str = "monotonic",
    recovery_profile: str = "typical",
    model_notes: str = "",
) -> dict[str, Any]:
    """Build a JSON-Schema-valid scenario dict from host module scores."""
    mapped = map_module_scores_to_axes(scores, genes_present=genes_present)
    axes = {axis: level for axis, level in mapped.ordinal.items() if level is not None}
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
            "proxy_notes": evidence["proxy_notes"]
            + (
                f" Proxy-only axes: {', '.join(evidence['proxy_only_components'])}."
                if evidence["proxy_only_components"]
                else ""
            ),
        },
        "scenario_assumptions": {
            "model_derived_components": [
                "ordinal thresholds on continuous module scores",
                "module gene membership as proxy for axis activity",
            ],
            "interaction_hypotheses": [],
            "unavailable_axes": [axis for axis, level in mapped.ordinal.items() if level is None],
            "notes": model_notes
            or "Continuous-to-ordinal mapping is heuristic pending dataset-specific calibration.",
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
