"""Tests for the reproducibility infrastructure layer."""
from __future__ import annotations

import json

from dccp.fingerprint import canonical_json, content_hash
from dccp.evaluation_protocol import CaseResult, summarize_cases, wilson_interval


def test_canonical_hash_is_order_independent():
    assert canonical_json({"b": 2, "a": 1}) == canonical_json({"a": 1, "b": 2})
    assert content_hash({"b": 2, "a": 1}) == content_hash({"a": 1, "b": 2})


def test_evaluation_summary_counts_confusion_matrix():
    result = summarize_cases([
        CaseResult("A", True, True),
        CaseResult("B", True, False),
        CaseResult("C", False, True),
        CaseResult("D", False, False),
    ])
    assert result["confusion"] == {"tp": 1, "tn": 1, "fp": 1, "fn": 1}
    assert result["accuracy"] == 0.5
    assert result["f1"] == 0.5


def test_wilson_interval_is_bounded():
    low, high = wilson_interval(8, 10)
    assert 0 <= low <= high <= 1
