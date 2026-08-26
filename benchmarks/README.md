# DCCP challenge sets

Materialized phenotypic challenge sets for defensive evaluation and hand-off to **CardiBench** / **CardiLearn**.

Generate or refresh:

```bash
dccp materialize --root scenarios -o benchmarks/dccp-challenge-set.v1.json
```

Each case includes scenario metadata, phenotypic axes, canonical digest, ladder role, audit status, and a heuristic defensive assessment. **No agent construction parameters** are included.

Integration note for CardiBench: treat this file as a *challenge catalog* (phenotype-level cases), not a GEO sample registry. Map `scenario_id` into your evaluation manifests as synthetic / computational challenge cases under the existing `cardivex-challenge-evaluation` family if desired.
