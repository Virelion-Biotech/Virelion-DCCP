"""Host profile feature engineering: modules, simple GRN-style aggregates, maturity.

Operates on gene×sample (or gene×cell) matrices provided by the caller.
Does not download expression data; does not handle pathogen genomes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .host_modules import (
    AXIS_TO_CARDISIM_PHENOTYPES,
    DCCP_AXIS_MODULES,
    MATURITY_MODULES,
)


def _index_genes(genes: Sequence[str]) -> dict[str, int]:
    return {g.upper(): i for i, g in enumerate(genes)}


def log1p_cpm_rows(expression: Sequence[Sequence[float]]) -> list[list[float]]:
    """Library-size normalize columns and log1p (pure Python, no numpy required)."""
    if not expression or not expression[0]:
        return []
    n_genes = len(expression)
    n_cells = len(expression[0])
    totals = [0.0] * n_cells
    for i in range(n_genes):
        row = expression[i]
        for j in range(n_cells):
            totals[j] += float(row[j])
    out: list[list[float]] = []
    for i in range(n_genes):
        row = expression[i]
        new_row = []
        for j in range(n_cells):
            t = totals[j]
            if t <= 0:
                new_row.append(0.0)
            else:
                # log1p(x / total * 1e4)
                x = float(row[j]) / t * 1e4
                new_row.append(_log1p(x))
        out.append(new_row)
    return out


def _log1p(x: float) -> float:
    # series-free stable enough for non-negative x
    return __import__("math").log1p(x)


def module_mean_scores(
    expression: Sequence[Sequence[float]],
    genes: Sequence[str],
    modules: Mapping[str, Sequence[str]],
) -> dict[str, list[float]]:
    """Per-column mean of log1p-CPM genes in each module. Shape: module → [n_cells]."""
    expr = log1p_cpm_rows(expression)
    idx = _index_genes(genes)
    n_cells = len(expr[0]) if expr else 0
    result: dict[str, list[float]] = {}
    for name, markers in modules.items():
        rows = [idx[g.upper()] for g in markers if g.upper() in idx]
        if not rows or n_cells == 0:
            result[name] = [0.0] * n_cells
            continue
        scores = []
        for j in range(n_cells):
            scores.append(sum(expr[r][j] for r in rows) / len(rows))
        result[name] = scores
    return result


def minmax_scale_1d(values: Sequence[float], lo_q: float = 0.01, hi_q: float = 0.99) -> list[float]:
    if not values:
        return []
    sorted_v = sorted(values)
    n = len(sorted_v)

    def _q(q: float) -> float:
        i = int(max(0, min(n - 1, round(q * (n - 1)))))
        return sorted_v[i]

    lo, hi = _q(lo_q), _q(hi_q)
    denom = hi - lo if hi > lo else 1.0
    return [max(0.0, min(1.0, (v - lo) / denom)) for v in values]


@dataclass
class HostProfileFeatures:
    """Aggregated host features ready for DCCP / CardiSim."""

    axis_scores: dict[str, float]  # mean across cells, [0,1]
    maturity_scores: dict[str, float]
    cardisim_proxy: dict[str, float]
    n_cells: int

    def as_dict(self) -> dict:
        return {
            "axis_scores": dict(self.axis_scores),
            "maturity_scores": dict(self.maturity_scores),
            "cardisim_proxy": dict(self.cardisim_proxy),
            "n_cells": self.n_cells,
        }


def extract_host_features(
    expression: Sequence[Sequence[float]],
    genes: Sequence[str],
) -> HostProfileFeatures:
    """Full host feature pass: DCCP axes, maturity modules, CardiSim-oriented proxies."""
    axis_raw = module_mean_scores(expression, genes, DCCP_AXIS_MODULES)
    mat_raw = module_mean_scores(expression, genes, MATURITY_MODULES)
    n_cells = len(next(iter(axis_raw.values()))) if axis_raw else 0

    axis_scores = {
        k: (sum(minmax_scale_1d(v)) / len(v) if v else 0.0) for k, v in axis_raw.items()
    }
    maturity_scores = {
        k: (sum(minmax_scale_1d(v)) / len(v) if v else 0.0) for k, v in mat_raw.items()
    }

    # CardiSim proxy: map axis scores onto phenotype names (simple mean of linked axes)
    cardisim: dict[str, float] = {}
    inv: dict[str, list[float]] = {}
    for axis, phenos in AXIS_TO_CARDISIM_PHENOTYPES.items():
        s = axis_scores.get(axis, 0.0)
        for p in phenos:
            inv.setdefault(p, []).append(s)
    for p, vals in inv.items():
        cardisim[p] = sum(vals) / len(vals)

    # viability is inverse of cell_death-like signal for downstream forcing intuition
    if "viability" in cardisim and "cell_death" in axis_scores:
        cardisim["viability"] = max(0.0, min(1.0, 1.0 - axis_scores["cell_death"]))

    return HostProfileFeatures(
        axis_scores=axis_scores,
        maturity_scores=maturity_scores,
        cardisim_proxy=cardisim,
        n_cells=n_cells,
    )


def grn_hub_score(
    expression: Sequence[Sequence[float]],
    genes: Sequence[str],
    hubs: Sequence[str],
) -> list[float]:
    """Simple hub aggregate: mean log1p-CPM of listed TF/hub genes per cell.

    Not a full GRN inference — an auditable summary feature for maturity / stress.
    """
    mod = {"hubs": tuple(hubs)}
    return module_mean_scores(expression, genes, mod).get("hubs", [])
