# Design Notes — Virelion-DCCP

## Motivation

Ordinary disease-phenotype simulators are insufficient for defensive evaluation. Adversarial biological scenarios may be deliberately unusual, combined, timed, or otherwise outside stereotypical disease presentations. A defensive AI system must be tested on:

- normal physiology,
- ordinary pathology,
- atypical but still “naturalistic” challenges,
- and deliberately novel / held-out adversarial phenotypes.

DCCP supplies the **challenge** side of that ladder while remaining strictly inside a defensive, threat-agnostic modeling boundary.

## Two-world model

| World | Responsibility |
|-------|----------------|
| **Scenario world** | Structured description of plausible *effects* an adversary could cause (phenotypic axes, onset, progression, recovery). |
| **Surrogate / proxy world** | Safe digital or experimental systems that reproduce the *relevant response dimensions* so detectors and countermeasures can be evaluated. |

The surrogate is never claimed to *be* the attack.

## Scenario representation

Canonical schema: `schemas/scenario.schema.json`.

Key fields:

- `scenario_id`, `title`, `tissue`
- `onset`, `progression`
- `phenotypic_axes` (inflammatory, vascular_endothelial, metabolic_mitochondrial, contractile_functional, structural_injury, cell_death, remodeling, recovery_profile)
- `temporal_profile` (optional phases)
- `realism_evidence` + `scenario_assumptions` (mandatory separation)
- `confidence`, `ood_flag`

## Six evaluation questions

1. Detection of deliberately unconventional biological insult.
2. Recognition of abnormality despite failure of ordinary disease classification.
3. Mechanism-oriented multi-axis characterization (not binary threat labels).
4. OOD detection on completely held-out scenarios.
5. Countermeasure / host-resilience testing on unfamiliar challenges.
6. Full auditability and reconstructibility of every scenario.

## Intended integration points

- **CardiSim** — digital surrogate dynamics conditioned on scenario axes.
- **CardiTrace / ElectroTrace** — multimodal measurement streams.
- **CardiBench** — leakage-aware, versioned evaluation sets that can include DCCP-derived challenge cases.
- **CardiLearn** — representation learning and defensive models under evaluation.

## Implementation roadmap (high level)

1. Scenario schema + example library (done in scaffold).
2. Scenario loader, validator, and audit helpers (`src/dccp`).
3. Interface contracts for “challenge → surrogate state” and “surrogate state → defensive model input”.
4. Minimal defensive evaluation harness (detection, mechanism scores, OOD flag).
5. Countermeasure / recovery evaluation hooks.
6. Provenance and canonical hashing for scenario + run artifacts.

## Non-goals

- Agent design, optimization, or operational planning.
- Claims that any proxy *is* a real-world attack.
- Unanchored synthetic scenarios that lack realism-evidence grounding.
