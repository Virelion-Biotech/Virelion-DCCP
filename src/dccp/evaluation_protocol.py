"""Evaluation protocol primitives: scenario-level results and aggregate metrics."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import sqrt
from typing import Any, Iterable


@dataclass(frozen=True)
class CaseResult:
    scenario_id: str
    expected_positive: bool
    predicted_positive: bool
    score: float | None = None
    ood_expected: bool = False
    ood_predicted: bool = False

    @property
    def correct(self) -> bool:
        return self.expected_positive == self.predicted_positive

    def as_dict(self) -> dict[str, Any]:
        return asdict(self) | {"correct": self.correct}


def _rate(n: int, d: int) -> float:
    return n / d if d else 0.0


def summarize_cases(cases: Iterable[CaseResult]) -> dict[str, Any]:
    rows = list(cases)
    tp = sum(r.expected_positive and r.predicted_positive for r in rows)
    tn = sum((not r.expected_positive) and (not r.predicted_positive) for r in rows)
    fp = sum((not r.expected_positive) and r.predicted_positive for r in rows)
    fn = sum(r.expected_positive and (not r.predicted_positive) for r in rows)
    ood_correct = sum(r.ood_expected == r.ood_predicted for r in rows)
    accuracy = _rate(tp + tn, len(rows))
    precision = _rate(tp, tp + fp)
    recall = _rate(tp, tp + fn)
    f1 = _rate(2 * precision * recall, precision + recall)
    return {
        "n": len(rows),
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "ood_accuracy": _rate(ood_correct, len(rows)),
        "cases": [r.as_dict() for r in rows],
    }


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if total < 0:
        raise ValueError("total must be non-negative")
    if successes < 0 or successes > total:
        raise ValueError("successes must satisfy 0 <= successes <= total")
    if z < 0:
        raise ValueError("z must be non-negative")
    if total == 0:
        return (0.0, 0.0)
    p = successes / total
    z2 = z * z
    denom = 1 + z2 / total
    centre = (p + z2 / (2 * total)) / denom
    radius = z * sqrt((p * (1 - p) + z2 / (4 * total)) / total) / denom
    return (max(0.0, centre - radius), min(1.0, centre + radius))
