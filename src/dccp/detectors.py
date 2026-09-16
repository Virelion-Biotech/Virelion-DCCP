"""Pluggable defensive detectors behind the DefensiveAssessment contract."""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .evaluate import DefensiveAssessment, _NORMAL, _ORDINARY_TEMPLATES, assess_scenario
from .scenario import Scenario

_LEVEL_IDX = {"none": 0, "low": 1, "moderate": 2, "substantial": 3, "high": 4, "severe": 5}
_FEATURE_KEYS = ("inflammatory", "vascular_endothelial", "metabolic_mitochondrial", "contractile_functional", "structural_injury", "cell_death", "remodeling")


def axes_to_vector(axes: Mapping[str, str]) -> list[float]:
    vector: list[float] = []
    for key in _FEATURE_KEYS:
        level = axes.get(key, "none")
        if level not in _LEVEL_IDX:
            raise ValueError(f"unknown phenotypic axis level for {key}: {level!r}")
        vector.append(float(_LEVEL_IDX[level]))
    return vector


def _euclid(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError("prototype vectors must have equal dimensions")
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


class Detector(ABC):
    @abstractmethod
    def assess(self, scenario: Scenario) -> DefensiveAssessment:
        ...

    def name(self) -> str:
        return self.__class__.__name__


class HeuristicDetector(Detector):
    def __init__(self, ood_threshold: float = 1.5) -> None:
        if not math.isfinite(float(ood_threshold)) or ood_threshold < 0:
            raise ValueError("ood_threshold must be finite and non-negative")
        self.ood_threshold = float(ood_threshold)

    def assess(self, scenario: Scenario) -> DefensiveAssessment:
        return assess_scenario(scenario, ood_threshold=self.ood_threshold)


@dataclass
class PrototypeDetector(Detector):
    """Nearest-centroid detector over ordinal axis vectors."""

    prototypes: dict[str, list[float]] = field(default_factory=dict)
    ood_radius: float = 2.5
    abnormal_radius: float = 0.8

    def __post_init__(self) -> None:
        self.ood_radius = float(self.ood_radius)
        self.abnormal_radius = float(self.abnormal_radius)
        if not math.isfinite(self.ood_radius) or self.ood_radius < 0:
            raise ValueError("ood_radius must be finite and non-negative")
        if not math.isfinite(self.abnormal_radius) or self.abnormal_radius < 0:
            raise ValueError("abnormal_radius must be finite and non-negative")
        for name, vector in self.prototypes.items():
            if len(vector) != len(_FEATURE_KEYS):
                raise ValueError(f"prototype {name!r} has invalid dimension")
            if not all(math.isfinite(float(value)) for value in vector):
                raise ValueError(f"prototype {name!r} contains non-finite values")

    def fit(self, scenarios: Sequence[Scenario], labels: Sequence[str] | None = None) -> PrototypeDetector:
        if labels is not None and len(labels) != len(scenarios):
            raise ValueError("labels must have the same length as scenarios")
        groups: dict[str, list[list[float]]] = {}
        for index, scenario in enumerate(scenarios):
            if scenario.ood_flag:
                continue
            label = labels[index].strip() if labels is not None else "ordinary"
            if not label:
                raise ValueError("prototype labels must be non-empty")
            groups.setdefault(label, []).append(axes_to_vector(scenario.phenotypic_axes))
        self.prototypes = {label: [sum(vector[i] for vector in vectors) / len(vectors) for i in range(len(_FEATURE_KEYS))] for label, vectors in groups.items()}
        for name, template in _ORDINARY_TEMPLATES.items():
            self.prototypes.setdefault(name, axes_to_vector(template))
        self.prototypes.setdefault("normal", axes_to_vector(_NORMAL))
        return self

    def fit_default_ordinary(self) -> PrototypeDetector:
        return self.fit([])

    def assess(self, scenario: Scenario) -> DefensiveAssessment:
        if not self.prototypes:
            self.fit_default_ordinary()
        vector = axes_to_vector(scenario.phenotypic_axes)
        normal_vector = self.prototypes.get("normal", axes_to_vector(_NORMAL))
        normalized_abnormality = _euclid(vector, normal_vector) / max(len(vector) ** 0.5, 1.0)
        candidate_prototypes = {name: proto for name, proto in self.prototypes.items() if name != "normal"}
        if not candidate_prototypes:
            raise ValueError("at least one non-normal prototype is required for assessment")
        best_name, best_distance = min(candidate_prototypes.items(), key=lambda item: _euclid(vector, item[1]))
        best_distance = _euclid(vector, candidate_prototypes[best_name])
        distance_ordinal = best_distance / max(len(vector) ** 0.5, 1.0)
        ood = bool(scenario.ood_flag) or best_distance >= self.ood_radius
        notes = [f"detector={self.name()}"]
        if scenario.ood_flag:
            notes.append("scenario.ood_flag is set")
        if best_distance >= self.ood_radius:
            notes.append(f"distance to nearest prototype {best_name}={best_distance:.2f} >= {self.ood_radius}")
        return DefensiveAssessment(
            scenario_id=scenario.scenario_id,
            abnormal=normalized_abnormality > 0.25,
            abnormality_score=float(normalized_abnormality),
            mechanism_profile={k: v for k, v in scenario.phenotypic_axes.items() if k != "recovery_profile"},
            nearest_ordinary=best_name,
            distance_to_nearest_ordinary=float(distance_ordinal),
            ood_suggested=ood,
            notes=notes,
        )

    def to_dict(self) -> dict[str, Any]:
        return {"type": "PrototypeDetector", "prototypes": {k: list(v) for k, v in self.prototypes.items()}, "ood_radius": self.ood_radius, "abnormal_radius": self.abnormal_radius}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PrototypeDetector:
        raw = data.get("prototypes") or {}
        if not isinstance(raw, Mapping):
            raise TypeError("prototypes must be an object")
        prototypes = {str(key): [float(value) for value in vector] for key, vector in raw.items()}
        return cls(prototypes=prototypes, ood_radius=float(data.get("ood_radius", 2.5)), abnormal_radius=float(data.get("abnormal_radius", 0.8)))
