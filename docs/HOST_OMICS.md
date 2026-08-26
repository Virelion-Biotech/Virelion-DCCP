# Host multi-omics → DCCP phenotypic axes

## Scope

This pipeline maps **host** cardiac multi-omics signals to DCCP ordinal axes and optional CardiSim phenotype proxies.

It does **not** accept or emit pathogen genome designs, agent feature edits, or operational biological instructions.

## Flow

```text
public GEO accession (metadata in host_evidence_panel.json)
        │
        ▼
expression matrix supplied by caller (not redistributed in-repo)
        │
        ▼
host gene modules (host_modules.py)
        │
        ├── DCCP axis continuous scores
        ├── maturity module scores
        └── CardiSim-oriented proxies
        │
        ▼
ordinal axes (omics_map.score_to_ordinal)
        │
        ▼
scenario draft + realism_evidence (GEO links)
        │
        ▼
accession digests (accession_provenance.py)
        │
        ▼
CardiBench: sample/subject leakage policy on locked splits
```

## Evidence panel

`data/reference/host_evidence_panel.json` lists public accessions (GSE185289, GSE240848, GSE135310, GSE153480, GSE216211, GSE269054) and which DCCP axes they can support. Status is **metadata_locked** — matrices are fetched/analyzed outside the repo.

## Feature engineering

| Feature set | Module source | Use |
|-------------|---------------|-----|
| Axis modules | `DCCP_AXIS_MODULES` | Ordinal phenotypic axes |
| Maturity | `MATURITY_MODULES` | RegenAtlas / CardiLearn-style host maturity abstracts |
| Hub aggregate | `grn_hub_score` | Simple TF/hub mean — not full GRN inference |
| CardiSim proxy | `AXIS_TO_CARDISIM_PHENOTYPES` | Continuous bridge scores |

## CLI

```bash
dccp host-panel
dccp map-scores --scores inflammatory=0.7,contractile_functional=0.6,...
dccp accession-digest GSE135310
```

## Provenance & leakage

- **Accession digests** are metadata hashes for realism_evidence and challenge sets.
- **Sample-level** train/test separation (donor, study, species, timepoint) is enforced in **CardiBench** when expression-level benchmarks are locked — DCCP only records the policy note.
