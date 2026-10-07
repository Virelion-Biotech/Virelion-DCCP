"""Host profile feature engineering for cardiac phenotypic programs."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from .host_modules import DCCP_AXIS_MODULES, MATURITY_MODULES, module_coverage


def _validate_expression(
    expression: Sequence[Sequence[float]], genes: Sequence[str]
) -> tuple[int, int]:
    if len(expression) != len(genes):
        raise ValueError(f"expression has {len(expression)} rows but genes has {len(genes)} names")
    if len(expression) == 0:
        return 0, 0
    n_cells = len(expression[0])
    for row_index, row in enumerate(expression):
        if len(row) != n_cells:
            raise ValueError(f"expression row {row_index} has inconsistent cell count")
        for col_index, value in enumerate(row):
            value = float(value)
            if not math.isfinite(value) or value < 0:
                raise ValueError(
                    f"expression[{row_index}][{col_index}] must be finite and non-negative"
                )
    return len(expression), n_cells


def _index_genes(genes: Sequence[str]) -> dict[str, int]:
    index: dict[str, int] = {}
    for i, gene in enumerate(genes):
        key = str(gene).strip().upper()
        if not key:
            raise ValueError("gene names must be non-empty")
        if key in index:
            raise ValueError(f"duplicate gene name: {gene!r}")
        index[key] = i
    return index


def log1p_cpm_rows(
    expression: Sequence[Sequence[float]], *, _validated: bool = False
) -> list[list[float]]:
    """Library-size normalize columns to 10,000 and log1p; input is genes x cells."""
    if not _validated:
        _validate_expression(expression, [str(i) for i in range(len(expression))])
    if len(expression) == 0 or len(expression[0]) == 0:
        return []
    n_cells = len(expression[0])
    scales = [max(float(row[j]) for row in expression) for j in range(n_cells)]
    totals = [
        math.fsum(float(row[j]) / scales[j] for row in expression) if scales[j] else 0.0
        for j in range(n_cells)
    ]

    out: list[list[float]] = []
    for row in expression:
        new_row: list[float] = []
        for j, value in enumerate(row):
            total = totals[j]
            x = (float(value) / scales[j]) / total * 1e4 if total > 0 else 0.0
            new_row.append(math.log1p(x))
        out.append(new_row)
    return out


def _module_mean_scores_from_log(
    expr: Sequence[Sequence[float]], genes: Sequence[str], modules: Mapping[str, Sequence[str]]
) -> dict[str, list[float | None]]:
    idx = _index_genes(genes)
    n_cells = len(expr[0]) if expr else 0
    result: dict[str, list[float | None]] = {}
    for name, markers in modules.items():
        rows = [idx[str(g).strip().upper()] for g in markers if str(g).strip().upper() in idx]
        if not rows or n_cells == 0:
            result[name] = [None] * n_cells
            continue
        result[name] = [sum(expr[row][j] for row in rows) / len(rows) for j in range(n_cells)]
    return result


def module_mean_scores(
    expression: Sequence[Sequence[float]],
    genes: Sequence[str],
    modules: Mapping[str, Sequence[str]],
) -> dict[str, list[float | None]]:
    """Per-column mean of observed log1p-CP10K markers; missing modules are None."""
    _validate_expression(expression, genes)
    expr = log1p_cpm_rows(expression, _validated=True)
    return _module_mean_scores_from_log(expr, genes, modules)


def minmax_scale_1d(values: Sequence[float], lo_q: float = 0.01, hi_q: float = 0.99) -> list[float]:
    if len(values) == 0:
        return []
    if not 0.0 <= lo_q <= hi_q <= 1.0:
        raise ValueError("quantile bounds must satisfy 0 <= lo_q <= hi_q <= 1")
    numeric = [float(value) for value in values]
    if not all(math.isfinite(value) for value in numeric):
        raise ValueError("values must all be finite")
    scale = max((abs(value) for value in numeric), default=1.0) or 1.0
    numeric = [value / scale for value in numeric]
    sorted_v = sorted(numeric)
    n = len(sorted_v)

    def quantile(q: float) -> float:
        pos = q * (n - 1)
        low = int(math.floor(pos))
        high = int(math.ceil(pos))
        if low == high:
            return sorted_v[low]
        weight = pos - low
        return sorted_v[low] * (1 - weight) + sorted_v[high] * weight

    lo, hi = quantile(lo_q), quantile(hi_q)
    denom = hi - lo if hi > lo else 1.0
    return [max(0.0, min(1.0, (value - lo) / denom)) for value in numeric]


@dataclass
class HostProfileFeatures:
    axis_scores: dict[str, float | None]
    maturity_scores: dict[str, float | None]
    cardisim_proxy: dict[str, float]
    n_cells: int
    module_log_means: dict[str, float | None] = field(default_factory=dict)
    coverage: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "axis_scores": dict(self.axis_scores),
            "maturity_scores": dict(self.maturity_scores),
            "cardisim_proxy": dict(self.cardisim_proxy),
            "n_cells": self.n_cells,
            "module_log_means": self.module_log_means,
            "coverage": self.coverage,
            "notes": self.notes,
            "scientific_status": "uncalibrated host-marker summaries; not dysfunction or viability estimates",
        }


def extract_host_features(
    expression: Sequence[Sequence[float]], genes: Sequence[str]
) -> HostProfileFeatures:
    """Full host feature pass using one library-size normalization of the matrix."""
    _, n_cells = _validate_expression(expression, genes)
    expr = log1p_cpm_rows(expression, _validated=True)
    axis_raw = _module_mean_scores_from_log(expr, genes, DCCP_AXIS_MODULES)
    mat_raw = _module_mean_scores_from_log(expr, genes, MATURITY_MODULES)
    coverage = {
        **module_coverage(genes, DCCP_AXIS_MODULES),
        **module_coverage(genes, MATURITY_MODULES),
    }
    all_raw = {**axis_raw, **mat_raw}
    means = {
        key: sum(values) / len(values) if values and coverage[key] > 0 else None
        for key, values in all_raw.items()
    }

    def relative_scores(raw):
        return {
            key: (
                sum(minmax_scale_1d(values)) / len(values)
                if values and coverage[key] > 0 and max(values) > min(values)
                else None
            )
            for key, values in raw.items()
        }

    axis_scores = relative_scores(axis_raw)
    maturity_scores = relative_scores(mat_raw)
    notes = [
        "Scores describe within-profile heterogeneity; reference-fit scaling is needed for cross-sample comparisons.",
        "Absent modules and invariant expression have unavailable relative scores, not zero burden.",
        "Mixed marker directions cannot estimate dysfunction, cell death or simulator state without calibration.",
    ]
    return HostProfileFeatures(axis_scores, maturity_scores, {}, n_cells, means, coverage, notes)


def grn_hub_score(
    expression: Sequence[Sequence[float]], genes: Sequence[str], hubs: Sequence[str]
) -> list[float | None]:
    """Per-cell mean observed hub-marker abundance; missing hub sets are None."""
    return module_mean_scores(expression, genes, {"hubs": tuple(hubs)}).get("hubs", [])
