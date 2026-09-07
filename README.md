# Virelion-DCCP

**Defensive Computational Challenge Platform for human cardiac models**

DCCP is a computational platform for constructing, auditing, assessing, and materializing defensive biological challenge scenarios represented as phenotypic consequence profiles. It is designed to test detection, characterization, out-of-distribution recognition, and host-resilience recovery without recreating an underlying biological threat.

> Central research question  
> *Can a human cardiac digital surrogate and defensive AI system detect, characterize, and respond to plausible adversarial biological challenge states—including deliberately atypical and previously unseen states—without requiring direct recreation of the underlying threat?*

**Version 0.3.0**

---

## Design principle: two worlds

### 1. Scenario world
Structured **phenotypic consequence** profiles using host-response axes.

### 2. Laboratory / digital surrogate world
Safe digital or experimental proxies that reproduce relevant response dimensions for detector and countermeasure tests.

See [`docs/DESIGN.md`](docs/DESIGN.md) and [`docs/SAFETY.md`](docs/SAFETY.md).

---

## Core questions

1. Detection of unconventional insult (`normal → ordinary → atypical → novel`)
2. Abnormality recognition outside ordinary disease labels
3. Mechanism-oriented multi-axis characterization
4. OOD detection on held-out scenarios
5. Countermeasure / host-resilience recovery scoring
6. Full audit and provenance of evidence, assumptions, and hashes

---

## Install & CLI

```bash
pip install -e '.[test]'
pytest -q

dccp list
dccp audit-all scenarios
dccp assess scenarios/examples/SCENARIO-018.heldout-metabolic-vascular.json --detector prototype
dccp bridge scenarios/examples/SCENARIO-001.ordinary-mi.json
dccp materialize -o benchmarks/dccp-challenge-set.v1.json
dccp recovery-demo
# optional if a CardiSim installation is available:
dccp surrogate scenarios/examples/SCENARIO-001.ordinary-mi.json --rescue
```

| Command | Purpose |
|---------|---------|
| `validate` / `audit` / `audit-all` | Schema and policy checks |
| `show` / `list` | Inspect the scenario library |
| `assess [--detector heuristic\|prototype]` | Defensive assessment |
| `bridge` | Emit a cardiac-simulation event payload |
| `hash` | Canonical SHA-256 |
| `materialize` | Write a hashed challenge set |
| `recovery-demo` | Host-resilience recovery score |
| `surrogate [--rescue]` | Run an optional digital surrogate |
| `host-panel` | Inspect the host evidence panel |
| `map-scores` | Map host module scores to scenario axes |
| `accession-digest` | Generate accession-level provenance |

---

## Scenario ladder

| ID | Role |
|----|------|
| `SCENARIO-001` | Ordinary MI-like |
| `SCENARIO-002` | Ordinary hypoxia-like |
| `SCENARIO-010` | Atypical multi-axis |
| `SCENARIO-017` | Held-out multiphasic |
| `SCENARIO-018` | Held-out metabolic–vascular |
| `SCENARIO-019` | Held-out delayed structural |

---

## Package surface (`dccp`)

- **Scenario** loading, validation, and auditing
- **Simulation payloads** through `axes_to_effects` and scenario event specifications
- **Detectors**: `HeuristicDetector`, `PrototypeDetector`
- **Recovery**: `evaluate_recovery`, optional surrogate/rescue evaluation
- **Library**: scenario loading and challenge-set materialization
- **Provenance**: canonical hashes and run records
- **Host evidence mapping**: module scores, phenotypic axes, and accession-level evidence records

## Safety boundary

DCCP represents phenotypic consequences and defensive assessment states. It does not provide protocols for constructing, optimizing, or reproducing biological threats.

## Status

**v0.3.0** — Scenario library, OOD ladder, defensive detectors, simulation payload generation, optional surrogate/rescue evaluation, recovery scoring, challenge-set materialization, host-evidence mapping, provenance, audit, and CI.

## License

GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later). See `LICENSE`.
