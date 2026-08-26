"""Pluggable defensive detectors behind the DefensiveAssessment contract.

- HeuristicDetector: pure axis-distance logic (default).
- PrototypeDetector: nearest-centroid style on ordinal feature vectors;
  can be "fit" on ordinary scenarios and score held-out ones as OOD.

No heavy ML dependencies; prototypes are explicit and auditable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .evaluate import (
    DefensiveAssessment,
    _NORMAL,
    _ORDINARY_TEMPLATES,
    _axis_distance,
    assess_scenario,
)
from .scenario import Scenario

_LEVEL_IDX = {
    "none": 0,
    "low": 1,
    "moderate": 2,
    "substantial": 3,
    "high": 4,
    "severe": 5,
}
_FEATURE_KEYS = [
    "inflammatory",
    "vascular_endothelial",
    "metabolic_mitochondrial",
    "contractile_functional",
    "structural_injury",
    "cell_death",
    "remodeling",
]


def axes_to_vector(axes: Mapping[str, str]) -> list[float]:
    return [float(_LEVEL_IDX.get(axes.get(k, "none"), 0)) for k in _FEATURE_KEYS]


def _euclid(a: Sequence[float], b: Sequence[float]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


class Detector(ABC):
    @abstractmethod
    def assess(self, scenario: Scenario) -> DefensiveAssessment:
        ...

    def name(self) -> str:
        return self.__class__.__name__


class HeuristicDetector(Detector):
    """Wraps evaluate.assess_scenario."""

    def __init__(self, ood_threshold: float = 1.5) -> None:
        self.ood_threshold = ood_threshold

    def assess(self, scenario: Scenario) -> DefensiveAssessment:
        return assess_scenario(scenario, ood_threshold=self.ood_threshold)


@dataclass
class PrototypeDetector(Detector):
    """Nearest-centroid detector over ordinal axis vectors.

    Fit on ordinary (non-OOD) scenarios; points far from all centroids
    are flagged OOD. Still returns the full DefensiveAssessment schema.
    """

    prototypes: dict[str, list[float]] = field(default_factory=dict)
    ood_radius: float = 2.5
    abnormal_radius: float = 0.8  # distance from normal vector

    def fit(self, scenarios: Sequence[Scenario], labels: Sequence[str] | None = None) -> "PrototypeDetector":
        groups: dict[str, list[list[float]]] = {}
        for i, sc in enumerate(scenarios):
            label = labels[i] if labels else (sc.scenario_id if not sc.ood_flag else "ood_skip")
            if sc.ood_flag or label == "ood_skip":
                continue
            groups.setdefault(label, []).append(axes_to_vector(sc.phenotypic_axes))
        self.prototypes = {}
        for label, vecs in groups.items():
            n = len(vecs)
            dim = len(vecs[0])
            mean = [sum(v[j] for v in vecs) / n for j in range(dim)]
            self.prototypes[label] = mean
        # always include built-in ordinary templates
        for name, tmpl in _ORDINARY_TEMPLATES.items():
            if name not in self.prototypes:
                self.prototypes[name] = axes_to_vector(tmpl)
        if "normal" not in self.prototypes:
            self.prototypes["normal"] = axes_to_vector(_NORMAL)
        return self

    def fit_default_ordinary(self) -> "PrototypeDetector":
        return self.fit([])

    def assess(self, scenario: Scenario) -> DefensiveAssessment:
        if not self.prototypes:
            self.fit_default_ordinary()
        vec = axes_to_vector(scenario.phenotypic_axes)
        normal_v = self.prototypes.get("normal", axes_to_vector(_NORMAL))
        abn = _euclid(vec, normal_v) / (len(vec) ** 0.5)

        best_name = None
        best_dist = float("inf")
        for name, proto in self.prototypes.items():
            if name == "normal":
                continue
            d = _euclid(vec, proto)
            if d < best_dist:
                best_dist = d
                best_name = name

        # normalize distance roughly to ordinal scale used by heuristic
        dist_ord = best_dist / max(len(vec) ** 0.5, 1.0)
        ood = bool(scenario.ood_flag) or best_dist >= self.ood_radius
        notes: list[str] = [f"detector={self.name()}"]
        if scenario.ood_flag:
            notes.append("scenario.ood_flag is set")
        if best_dist >= self.ood_radius:
            notes.append(f"distance to nearest prototype {best_name}={best_dist:.2f} ≥ {self.ood_radius}")

        return DefensiveAssessment(
            scenario_id=scenario.scenario_id,
            abnormal=abn >= self.abnormal_radius / max(len(vec) ** 0.5, 1.0) or abn > 0.25,
            abnormality_score=float(abn),
            mechanism_profile={
                k: v for k, v in scenario.phenotypic_axes.items() if k != "recovery_profile"
            },
            nearest_ordinary=best_name,
            distance_to_nearest_ordinary=float(dist_ord),
            ood_suggested=ood,
            notes=notes,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "PrototypeDetector",
            "prototypes": self.prototypes,
            "ood_radius": self.ood_radius,
            "abnormal_radius": self.abnormal_radius,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PrototypeDetector":
        return cls(
            prototypes={k: list(v) for k, v in (data.get("prototypes") or {}).items()},
            ood_radius=float(data.get("ood_radius", 2.5)),
            abnormal_radius=float(data.get("abnormal_radius", 0.8)),
        )
