"""Host profile feature engineering for cardiac phenotypic programs."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .host_modules import AXIS_TO_CARDISIM_PHENOTYPES, DCCP_AXIS_MODULES, MATURITY_MODULES


def _validate_expression(expression: Sequence[Sequence[float]], genes: Sequence[str]) -> tuple[int, int]:
    if len(expression) != len(genes):
        raise ValueError(f"expression has {len(expression)} rows but genes has {len(genes)} names")
    if not expression:
        return 0, 0
    n_cells = len(expression[0])
    for row_index, row in enumerate(expression):
        if len(row) != n_cells:
            raise ValueError(f"expression row {row_index} has inconsistent cell count")
        for col_index, value in enumerate(row):
            value = float(value)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"expression[{row_index}][{col_index}] must be finite and non-negative")
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


def log1p_cpm_rows(expression: Sequence[Sequence[float]], *, _validated: bool = False) -> list[list[float]]:
    """Library-size normalize columns and log1p; input is genes x cells."""
    if not _validated:
        _validate_expression(expression, [str(i) for i in range(len(expression))])
    if not expression or not expression[0]:
        return []
    n_cells = len(expression[0])
    totals = [0.0] * n_cells
    for row in expression:
        for j, value in enumerate(row):
            totals[j] += float(value)

    out: list[list[float]] = []
    for row in expression:
        new_row: list[float] = []
        for j, value in enumerate(row):
            total = totals[j]
            x = float(value) / total * 1e4 if total > 0 else 0.0
            new_row.append(math.log1p(x))
        out.append(new_row)
    return out


def _module_mean_scores_from_log(expr: Sequence[Sequence[float]], genes: Sequence[str], modules: Mapping[str, Sequence[str]]) -> dict[str, list[float]]:
    idx = _index_genes(genes)
    n_cells = len(expr[0]) if expr else 0
    result: dict[str, list[float]] = {}
    for name, markers in modules.items():
        rows = [idx[str(g).strip().upper()] for g in markers if str(g).strip().upper() in idx]
        if not rows or n_cells == 0:
            result[name] = [0.0] * n_cells
            continue
        result[name] = [sum(expr[row][j] for row in rows) / len(rows) for j in range(n_cells)]
    return result


def module_mean_scores(expression: Sequence[Sequence[float]], genes: Sequence[str], modules: Mapping[str, Sequence[str]]) -> dict[str, list[float]]:
    """Per-column mean of log1p-CPM genes in each module."""
    _validate_expression(expression, genes)
    expr = log1p_cpm_rows(expression, _validated=True)
    return _module_mean_scores_from_log(expr, genes, modules)


def minmax_scale_1d(values: Sequence[float], lo_q: float = 0.01, hi_q: float = 0.99) -> list[float]:
    if not values:
        return []
    if not 0.0 <= lo_q <= hi_q <= 1.0:
        raise ValueError("quantile bounds must satisfy 0 <= lo_q <= hi_q <= 1")
    numeric = [float(value) for value in values]
    if not all(math.isfinite(value) for value in numeric):
        raise ValueError("values must all be finite")
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
    axis_scores: dict[str, float]
    maturity_scores: dict[str, float]
    cardisim_proxy: dict[str, float]
    n_cells: int

    def as_dict(self) -> dict[str, object]:
        return {"axis_scores": dict(self.axis_scores), "maturity_scores": dict(self.maturity_scores), "cardisim_proxy": dict(self.cardisim_proxy), "n_cells": self.n_cells}


def extract_host_features(expression: Sequence[Sequence[float]], genes: Sequence[str]) -> HostProfileFeatures:
    """Full host feature pass using one library-size normalization of the matrix."""
    _, n_cells = _validate_expression(expression, genes)
    expr = log1p_cpm_rows(expression, _validated=True)
    axis_raw = _module_mean_scores_from_log(expr, genes, DCCP_AXIS_MODULES)
    mat_raw = _module_mean_scores_from_log(expr, genes, MATURITY_MODULES)
    axis_scores = {key: (sum(minmax_scale_1d(values)) / len(values) if values else 0.0) for key, values in axis_raw.items()}
    maturity_scores = {key: (sum(minmax_scale_1d(values)) / len(values) if values else 0.0) for key, values in mat_raw.items()}

    inverse: dict[str, list[float]] = {}
    for axis, phenotypes in AXIS_TO_CARDISIM_PHENOTYPES.items():
        score = axis_scores.get(axis, 0.0)
        for phenotype in phenotypes:
            inverse.setdefault(phenotype, []).append(score)
    cardisim = {phenotype: sum(values) / len(values) for phenotype, values in inverse.items()}
    if "cell_death" in axis_scores:
        cardisim["viability"] = 1.0 - axis_scores["cell_death"]

    return HostProfileFeatures(axis_scores, maturity_scores, cardisim, n_cells)


def grn_hub_score(expression: Sequence[Sequence[float]], genes: Sequence[str], hubs: Sequence[str]) -> list[float]:
    """Simple per-cell mean log1p-CPM aggregate of listed hub genes."""
    return module_mean_scores(expression, genes, {"hubs": tuple(hubs)}).get("hubs", [])
