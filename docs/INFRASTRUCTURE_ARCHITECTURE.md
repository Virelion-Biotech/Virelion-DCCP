# DCCP infrastructure architecture

DCCP now separates the challenge domain from a reproducibility/infrastructure layer.

## Design sources

The architecture was informed by public patterns from:

- `AlexandreRees/NeuroPipeline` — reproducible scientific pipeline stages, auditability, integrity and provenance. The upstream project is MIT licensed; DCCP does not copy its source code.
- `dsfsi/datacommonsorg-schema` and the Data Commons ecosystem — explicit schemas, domain modeling and machine-readable registries. The schema repository is Apache-2.0 licensed; DCCP does not copy its source code.
- Data Commons import/tooling repositories — separation of ingestion, transformation and downstream analysis.

These are architectural references only. The DCCP implementation is original and remains AGPL-3.0-or-later.

## New infrastructure layer

```text
source artifact
    |
    v
 ingest -> normalized artifact
    |
    +--> fingerprint
    |
    +--> provenance
    |
    v
 scenario / challenge registry
    |
    +--> schema + policy audit
    +--> evaluation protocol
    +--> integrity gate
    |
    v
 reproducibility bundle
```

### Fingerprints

`dccp.fingerprint` provides canonical JSON serialization and streaming SHA-256 file hashing. Hashes are stable across dictionary key order and are suitable for manifests.

### Provenance

`dccp.provenance_v2.ArtifactProvenance` records artifact identity, type, content hash, schema version, producer version, inputs and parameters.

### Registry

`dccp.registry` discovers JSON scenarios, audits them, fingerprints their files and emits a machine-readable registry. Failed or malformed files are not silently promoted to valid entries.

### Integrity

`dccp.integrity` verifies manifest file hashes and can generate deterministic file manifests.

### Evaluation

`dccp.evaluation_protocol` provides scenario-level results, confusion metrics, F1, OOD accuracy and Wilson intervals. It is deliberately independent of any particular detector implementation.

### Bundles

`dccp.bundle` creates a self-describing run manifest containing inputs, hashes, environment metadata and result records without embedding external datasets.

### Release gate

`dccp.release_gate` provides a minimal fail-closed gate requiring an audited, fingerprinted scenario registry before release.

## Safety boundary

These components operate on defensive computational artifacts. They do not construct, optimize or reproduce biological threats, and provenance metadata does not constitute biological validation.
