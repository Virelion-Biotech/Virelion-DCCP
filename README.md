# Virelion-DCCP

**Defensive Computational Challenge Platform for human cardiac models**

A computational adversarial biological challenge platform that lets defensive AI systems detect, characterize, and respond to *plausible* adversarial biological challenge states—including deliberately atypical and previously unseen phenotypes—without requiring direct recreation of any underlying threat.

> Central research question  
> *Can a human cardiac digital surrogate and defensive AI system detect, characterize, and respond to plausible adversarial biological challenge states—including deliberately atypical and previously unseen states—without requiring direct recreation of the underlying threat?*

Licensed under the **GNU Affero General Public License v3.0** (AGPL-3.0).

**Version 0.2.0**

---

## Design principle: two worlds

### 1. Scenario world
Structured **phenotypic consequence** profiles (host-response axes only).

### 2. Laboratory / digital surrogate world
Safe digital (CardiSim) or experimental proxies that reproduce relevant response dimensions for detector and countermeasure tests.

See [`docs/DESIGN.md`](docs/DESIGN.md), [`docs/SAFETY.md`](docs/SAFETY.md), [`docs/INTEGRATION.md`](docs/INTEGRATION.md).

---

## Six core questions

1. Detection of unconventional insult (`normal → ordinary → atypical → novel`)
2. Abnormality recognition outside ordinary disease labels
3. Mechanism-oriented multi-axis characterization
4. OOD detection on held-out scenarios
5. Countermeasure / host-resilience recovery scoring
6. Full audit + provenance (evidence vs assumptions, hashes)

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
# optional if Virelion-CardiSim is installed:
dccp surrogate scenarios/examples/SCENARIO-001.ordinary-mi.json --rescue
```

| Command | Purpose |
|---------|---------|
| `validate` / `audit` / `audit-all` | Schema + dual-use policy |
| `show` / `list` | Inspect library |
| `assess [--detector heuristic\|prototype]` | Defensive assessment |
| `bridge` | CardiSim event payload |
| `hash` | Canonical SHA-256 |
| `materialize` | Hashed challenge set (CardiBench hand-off) |
| `recovery-demo` | Host-resilience recovery score |
| `surrogate [--rescue]` | CardiSim run (optional dependency) |

---

## Scenario ladder (examples)

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

- **Scenario** load / validate / audit  
- **CardiSim bridge** (`axes_to_effects`, `scenario_to_cardisim_payload`)  
- **Detectors**: `HeuristicDetector`, `PrototypeDetector` (fit on ordinary, OOD radius)  
- **Recovery**: `evaluate_recovery`, optional `run_challenge_with_rescue`  
- **Library**: `load_library`, `materialize_challenge_set`  
- **Provenance**: canonical hashes, run records  

---

## Stack

| Component | Role |
|-----------|------|
| CardiSim | Digital surrogate |
| CardiTrace / ElectroTrace | Measurements |
| CardiBench | Leakage-aware benchmarks |
| CardiLearn | Learned models |
| **DCCP** | Challenge library + defensive harness |

---

## Status

**v0.2.0** — Full defensive loop scaffold: scenario library, OOD ladder, detectors, CardiSim bridge + optional surrogate/rescue, recovery scoring, challenge-set materialization, audit, CI.

---

## License

Copyright (c) 2026 Virelion Biotech  
GNU Affero General Public License v3.0 — see [LICENSE](LICENSE).
