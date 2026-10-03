# Integration — CardiSim, CardiBench, detectors

## CardiSim (digital surrogate)

```python
from dccp import load_scenario, scenario_to_cardisim_payload
from dccp.surrogate import run_scenario_surrogate, run_challenge_with_rescue

sc = load_scenario("scenarios/examples/SCENARIO-001.ordinary-mi.json")
payload = scenario_to_cardisim_payload(sc)  # events for ChallengeEvent

# Requires cardisim installed:
summary = run_scenario_surrogate(sc, n_cells=64, seed=7)
challenged, rescued, recovery = run_challenge_with_rescue(sc)
print(recovery.overall_recovery)
```

CLI:

```bash
dccp bridge scenarios/examples/SCENARIO-001.ordinary-mi.json
dccp surrogate scenarios/examples/SCENARIO-001.ordinary-mi.json --rescue
```

## Recovery without CardiSim

```python
from dccp import evaluate_recovery

report = evaluate_recovery(
    scenario_id="X",
    intervention_name="host_resilience_intervention",
    baseline={...}, challenged={...}, rescued={...},
)
```

```bash
dccp recovery-demo
```

## Detectors

```python
from dccp import HeuristicDetector, PrototypeDetector, load_library

lib = load_library("scenarios")
ordinary = [e.scenario for e in lib if not e.scenario.ood_flag]
det = PrototypeDetector().fit(ordinary)
print(det.assess(lib[0].scenario).as_dict())
```

## CardiBench hand-off

```bash
dccp materialize -o benchmarks/dccp-challenge-set.v1.json
```

Use the resulting JSON as a versioned challenge catalog (`set_hash` for provenance). Pair with CardiBench manifests under `cardivex-challenge-evaluation` without mixing GEO sample leakage policies with synthetic scenario IDs.
