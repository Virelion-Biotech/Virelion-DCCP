# Virelion-DCCP

DCCP is a defensive computational challenge platform for human cardiac models. It constructs, audits, assesses, and materializes defensive challenge scenarios represented as phenotypic consequence profiles. It tests detection, characterization, out-of-distribution recognition, and host-resilience recovery without recreating an underlying biological threat.

## What it contains

- Scenario loading, schema validation, and policy auditing.
- Phenotypic consequence profiles and challenge scenarios.
- Defensive detectors including `HeuristicDetector` and `PrototypeDetector`.
- Simulation event specifications and cardiac-simulation payload generation.
- Recovery/resilience scoring and optional surrogate evaluation.
- Challenge-library loading and hashed challenge-set materialization.
- Host-evidence mapping from module scores to phenotypic axes.
- Canonical hashing and run provenance.
- CLI tools for validation, assessment, materialization, recovery, and evidence mapping.

## Installation

```bash
pip install -e '.[test]'
pytest -q
```

## Usage

```bash
dccp list
dccp audit-all scenarios
dccp assess scenarios/examples/SCENARIO-018.heldout-metabolic-vascular.json --detector prototype
dccp bridge scenarios/examples/SCENARIO-001.ordinary-mi.json
dccp materialize -o benchmarks/dccp-challenge-set.v1.json
dccp recovery-demo
```

Optional digital-surrogate evaluation is available when a compatible simulator installation is present:

```bash
dccp surrogate scenarios/examples/SCENARIO-001.ordinary-mi.json --rescue
```

## Inputs and outputs

**Inputs:** phenotypic scenario specifications, host-response axes, challenge-library records, detector configuration, evidence/module scores, and optional simulator/surrogate parameters.

**Outputs:** validation/audit reports, defensive assessment results, simulation event payloads, hashed challenge sets, recovery scores, host-axis mappings, canonical digests, and provenance records.

## Validation

Scenario validation checks schema and policy constraints. Assessment supports defensive detector outputs, and challenge materialization records hashes for reproducibility. The scenario ladder separates ordinary, atypical, and held-out cases. Software tests should be run with `pytest -q`.

These checks validate computational artifacts and challenge construction; they do not establish biological validity of the represented states.

## Limitations

Scenarios represent phenotypic consequences rather than complete biological mechanisms. Synthetic or proxy states can differ from real host responses. OOD performance depends on scenario construction and feature representation. Recovery scores are model-dependent. Evidence mappings depend on the quality and completeness of the underlying evidence.

## Safety

DCCP does not provide protocols for constructing, optimizing, or reproducing biological threats.

## License

GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later). See `LICENSE`.
