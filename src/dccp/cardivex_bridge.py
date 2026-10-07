"""Exact-semantics bridge from DCCP ordinal axes to CardiVex distance primitives."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import sqrt, isfinite


def abnormality_score(left, right):
    try:
        from cardivex.defense import abnormality_score as external
    except ModuleNotFoundError as exc:
        if exc.name != "cardivex":
            raise
        return sqrt(sum((left[key] - right[key]) ** 2 for key in left) / len(left))
    return external(left, right)


def nearest_state_distance(query, references):
    return min(abnormality_score(query, ref) for ref in references)


_LEVEL_IDX = {"none": 0, "low": 1, "moderate": 2, "substantial": 3, "high": 4, "severe": 5}
_LEVEL_MAX = 5


def _encode_axes(axes: Mapping[str, str]) -> dict[str, float]:
    """Cumulative binary encoding whose squared distance equals ordinal L1 distance."""
    encoded: dict[str, float] = {}
    for axis in sorted(key for key in axes if key != "recovery_profile"):
        level = axes.get(axis, "none")
        if level not in _LEVEL_IDX:
            raise ValueError(f"unknown ordinal level for axis {axis!r}: {level!r}")
        index = _LEVEL_IDX[level]
        for threshold in range(1, _LEVEL_MAX + 1):
            encoded[f"{axis}::ge::{threshold}"] = 1.0 if index >= threshold else 0.0
    return encoded


def ordinal_axis_distance(a: Mapping[str, str], b: Mapping[str, str]) -> float:
    """Match DCCP's legacy mean absolute ordinal distance using CardiVex."""
    keys = (set(a) | set(b)) - {"recovery_profile"}
    if not keys:
        return 0.0
    a_full = {key: a.get(key, "none") for key in keys}
    b_full = {key: b.get(key, "none") for key in keys}
    score = abnormality_score(_encode_axes(a_full), _encode_axes(b_full))
    return _LEVEL_MAX * score * score


def nearest_ordinal_axis_distance(
    query: Mapping[str, str],
    references: Sequence[Mapping[str, str]],
) -> float:
    """Nearest DCCP ordinal distance delegated to CardiVex OOD primitive."""
    if not references:
        raise ValueError("at least one reference state is required")
    keys = set(query) - {"recovery_profile"}
    for reference in references:
        keys.update(set(reference) - {"recovery_profile"})
    query_full = {key: query.get(key, "none") for key in keys}
    refs_full = [{key: ref.get(key, "none") for key in keys} for ref in references]
    score = nearest_state_distance(
        _encode_axes(query_full),
        [_encode_axes(reference) for reference in refs_full],
    )
    return _LEVEL_MAX * score * score


def ordinal_vector_euclidean(a: Sequence[float], b: Sequence[float]) -> float:
    """Match raw Euclidean prototype distance using CardiVex abnormality_score."""
    if len(a) != len(b):
        raise ValueError("prototype vectors must have equal dimensions")
    if not a:
        return 0.0
    if any(
        isinstance(x, bool) or not isfinite(float(x)) or not 0 <= float(x) <= 5 for x in (*a, *b)
    ):
        raise ValueError("Ordinal vectors must be finite and within [0, 5]")
    left = {str(i): float(value) / _LEVEL_MAX for i, value in enumerate(a)}
    right = {str(i): float(value) / _LEVEL_MAX for i, value in enumerate(b)}
    score = abnormality_score(left, right)
    return score * _LEVEL_MAX * sqrt(len(a))
