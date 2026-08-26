# Virelion-DCCP

**Defensive Computational Challenge Platform for human cardiac models**

A computational adversarial biological challenge platform that lets defensive AI systems detect, characterize, and respond to *plausible* adversarial biological challenge states—including deliberately atypical and previously unseen phenotypes—without requiring direct recreation of any underlying threat.

> Central research question  
> *Can a human cardiac digital surrogate and defensive AI system detect, characterize, and respond to plausible adversarial biological challenge states—including deliberately atypical and previously unseen states—without requiring direct recreation of the underlying threat?*

Licensed under the **GNU Affero General Public License v3.0** (AGPL-3.0).

---

## Design principle: two worlds

### 1. Scenario world
Represents what an adversary *could plausibly cause* at the level of **phenotypic consequences** the defensive system would encounter.

Not “average hypoxia”, but structured challenge descriptors such as:

```text
SCENARIO-017
Adversarial biological challenge
        │
        ├── affected tissue: cardiac
        ├── onset: rapid
        ├── progression: multiphasic
        ├── inflammatory component: substantial
        ├── vascular component: substantial
        ├── metabolic component: moderate
        ├── structural injury: delayed
        ├── functional impairment: progressive
        └── recovery profile: atypical
```

The platform encodes **observable consequence profiles**, never engineering or optimization instructions for any biological agent.

### 2. Laboratory / digital surrogate world
Answers: *Can we reproduce those consequences safely enough to test the detector?*

```text
Plausible threat scenario
          ↓
Threat-effect model
          ↓
 ┌─────────────────────────┐
 │ Digital phenotype       │
 │ Experimental proxy      │
 │ Historical observation  │
 └────────────┬────────────┘
              ↓
       Cardiac model
              ↓
      Detection system
```

The proxy is never claimed to *be* the attack; it is validated to reproduce the **relevant biological response dimensions**.

---

## Six core questions the platform is built to answer

1. **Detection of unconventional insult**  
   Benchmark ladder: `normal → ordinary disease → unusual challenge → novel challenge`.

2. **Recognition of abnormality outside ordinary disease**  
   The model must flag biological abnormality even when standard disease classification fails.

3. **Mechanism-oriented characterization**  
   Output is a multi-axis cardiac state assessment (inflammatory signaling, endothelial dysfunction, mitochondrial disturbance, contractile dysfunction, structural remodeling, cell death, …), not a binary “threat / no-threat”.

4. **Out-of-distribution (OOD) detection**  
   Held-out scenarios that were never seen during training must produce:  
   *“This is biologically abnormal and does not adequately match known states.”*

5. **Countermeasure / host-resilience testing**  
   Measure restoration of morphology, viability, contractility, molecular state, tissue organization and cellular composition after intervention on an unfamiliar challenge.

6. **Full reconstructibility and audit**  
   Every scenario carries separate `REALISM EVIDENCE` and `SCENARIO ASSUMPTIONS` blocks with explicit confidence labels (high / moderate / exploratory).

---

## Architecture overview

```text
                 ADVERSARIAL SCENARIO LIBRARY
                           │
                           ▼
                ┌─────────────────────┐
                │ Threat Scenario      │
                │ Representation       │
                └──────────┬──────────┘
                           │
             realistic biological effects
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
      Existing evidence            Computational
      / observations               scenario synthesis
             │                           │
             └─────────────┬─────────────┘
                           ▼
                 CARDIAC DIGITAL SURROGATE
                           │
                           ▼
              SAFE EXPERIMENTAL PROXIES
                           │
                           ▼
                MULTIMODAL MEASUREMENTS
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
          Imaging        Omics       Function
             └─────────────┼─────────────┘
                           ▼
                  DEFENSIVE AI ENGINE
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
          Detection     Mechanism       OOD
                         inference      detection
             └─────────────┼─────────────┘
                           ▼
                  COUNTERMEASURE TEST
                           │
                           ▼
                  RECOVERY / RESCUE
                           │
                           ▼
                    AUDIT + PROVENANCE
```

## Validation ladder (synthetic scenarios are never free-floating)

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

All synthetic material is anchored to the first three layers.

---

## Safety & dual-use boundary (non-negotiable)

- The repository **does not** contain instructions, parameters, or methods for engineering, optimizing, propagating, or deploying any biological agent.
- Scenario descriptors describe only **host-response and phenotypic consequences** that a defensive system would observe.
- Experimental proxies are limited to safe, publicly documented, or computationally synthesized response profiles.
- All scenario files must include explicit realism-evidence and assumption blocks so computational hypotheses are never presented as experimentally established facts.

See [`docs/SAFETY.md`](docs/SAFETY.md) for the normative policy.

---

## Relationship to the rest of the Virelion cardiac stack

| Component | Role relative to DCCP |
|-----------|------------------------|
| **Virelion-CardiSim** | Cardiac digital surrogate & dynamics engine |
| **Virelion-CardiTrace / ElectroTrace** | Multimodal measurement & annotation layer |
| **Virelion-CardiBench** | Versioned, leakage-aware evaluation benchmarks |
| **Virelion-CardiLearn** | Model training / representation learning |
| **Virelion-DCCP** (this repo) | Adversarial scenario library + defensive AI evaluation harness |

DCCP supplies the *challenge* side; the other repositories supply the *surrogate*, *measurement*, *benchmark*, and *model* sides.

---

## Install & CLI

```bash
pip install -e '.[test]'
pytest -q

dccp audit-all scenarios
dccp assess scenarios/examples/SCENARIO-017.example.json
dccp bridge scenarios/examples/SCENARIO-001.ordinary-mi.json
dccp hash scenarios/examples/SCENARIO-001.ordinary-mi.json
```

| Command | Purpose |
|---------|---------|
| `dccp validate PATH` | JSON Schema validation |
| `dccp audit PATH` | Schema + dual-use policy audit |
| `dccp audit-all [DIR]` | Audit all scenario JSON under a tree |
| `dccp show PATH` | Pretty-print axes |
| `dccp assess PATH` | Abnormality / mechanism / OOD heuristic assessment |
| `dccp bridge PATH` | Emit CardiSim-compatible event payload |
| `dccp hash PATH` | Canonical SHA-256 of scenario JSON |

---

## Scenario ladder (examples)

| ID | Role |
|----|------|
| `SCENARIO-001` | Ordinary MI-like pathology anchor |
| `SCENARIO-002` | Hypoxia-like ordinary metabolic-vascular anchor |
| `SCENARIO-010` | Atypical multi-axis combination |
| `SCENARIO-017` | Held-out / novel multiphasic challenge (`ood_flag: true`) |

---

## Repository layout

```text
Virelion-DCCP/
├── LICENSE
├── README.md
├── pyproject.toml
├── schemas/scenario.schema.json
├── scenarios/examples/
│   ├── SCENARIO-001.ordinary-mi.json
│   ├── SCENARIO-002.hypoxia-like.json
│   ├── SCENARIO-010.atypical-combo.json
│   └── SCENARIO-017.example.json
├── src/dccp/
│   ├── scenario.py          # load + schema validate
│   ├── audit.py             # policy audit
│   ├── evaluate.py          # defensive assessment heuristics
│   ├── cardisim_bridge.py   # axes → CardiSim event specs
│   ├── provenance.py        # canonical hashing
│   └── cli.py
├── docs/DESIGN.md
├── docs/SAFETY.md
└── tests/
```

---

## Status

**v0.1.0 — working scaffold.**  
Scenario schema, policy audit, example ladder, CardiSim bridge, defensive assessment heuristics, provenance hashing, CLI, and CI are in place. Countermeasure/recovery evaluation and learned defensive models are next.

---

## License

Copyright (c) 2026 Virelion Biotech  
This project is licensed under the GNU Affero General Public License v3.0.  
See [LICENSE](LICENSE) and <https://www.gnu.org/licenses/agpl-3.0.html>.
