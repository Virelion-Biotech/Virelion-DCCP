# Safety & Dual-Use Boundary — Virelion-DCCP

This document is normative for the repository.

## What DCCP is allowed to represent

- **Phenotypic consequence profiles** of plausible adversarial biological challenges on cardiac tissue (and, later, other tissues).
- Host-response dimensions: inflammatory signaling, endothelial/vascular dysfunction, metabolic/mitochondrial disturbance, contractile/functional impairment, structural injury, cell death, remodeling, recovery trajectory.
- Temporal structure (onset, phases, progression) expressed only in terms of observable host effects.
- Computational hypotheses about *combinations* and *timing* of those host effects, clearly labeled as model-derived or exploratory.
- Links to public literature, historical observations, and experimentally characterized *safe proxies* that reproduce relevant response dimensions.

## Required scenario metadata

Every scenario **must** include:

1. `realism_evidence` — components supported by observation, literature, or characterized proxies.
2. `scenario_assumptions` — model-derived or exploratory components (combinations, timing, interactions).
3. `confidence` — one of `high` | `moderate` | `exploratory`.

Computational hypotheses must never be presented as experimentally established facts.

## Validation ladder

Synthetic or novel scenarios are valid only when anchored:

```text
real observation
      ↓
experimentally characterized proxy
      ↓
validated computational representation
      ↓
synthetic variation
      ↓
novel scenario
```

Free-floating invention without the first three layers is out of scope.

## Relationship to other Virelion components

- **CardiSim / digital surrogates** may implement dynamics consistent with a scenario’s phenotypic axes.
- **CardiBench** may include pathogen-*associated* cardiac phenotype evaluation; metadata remain free of operational biological instructions.
- **Biosafety-Assessment** tooling remains the reference for laboratory risk framing; DCCP itself is a computational evaluation environment.

## License note

The AGPL-3.0 license applies to the software and schemas. The safety boundary above is an additional project policy that applies regardless of license terms.
