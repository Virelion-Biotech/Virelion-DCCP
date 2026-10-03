"""Accession-level provenance digests and CardiBench-oriented sample policy notes.

DCCP does not materialize GEO expression matrices. Provenance here is metadata-
level: accession IDs, roles, and digests that can be attached to scenario
realism_evidence and challenge-set records. Sample-level leakage policy remains
CardiBench's responsibility when locked splits are built.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .omics_map import accession_digest, load_host_evidence_panel
from .provenance import canonical_hash


def panel_accession_records() -> list[dict[str, Any]]:
    panel = load_host_evidence_panel()
    records = []
    for ds in panel.get("datasets") or []:
        acc = ds.get("accession")
        if not acc:
            continue
        extra = {
            "organism": ds.get("organism"),
            "modality": ds.get("modality"),
            "roles": ds.get("roles"),
            "status": ds.get("status"),
            "source": ds.get("source"),
        }
        records.append(
            {
                "accession": acc,
                "digest": accession_digest(acc, extra),
                **{key: value for key, value in extra.items() if value is not None},
            }
        )
    return records


def evidence_bundle_for_accessions(accessions: Sequence[str]) -> dict[str, Any]:
    """Provenance bundle linking listed accessions to panel digests."""
    normalized = [str(accession).strip() for accession in accessions]
    if any(not accession for accession in normalized):
        raise ValueError("accessions must be non-empty strings")
    by_acc = {record["accession"]: record for record in panel_accession_records()}
    linked = []
    missing = []
    for accession in normalized:
        if accession in by_acc:
            linked.append(by_acc[accession])
        else:
            missing.append(accession)
            linked.append({"accession": accession, "digest": accession_digest(accession), "status": "not_in_panel"})
    bundle = {
        "accessions": normalized,
        "records": linked,
        "missing_from_panel": missing,
        "leakage_policy_note": (
            "Accession digests are metadata-level only. Sample/donor/subject separation "
            "for model evaluation must be enforced in CardiBench split policies before "
            "any expression-level training or testing."
        ),
    }
    bundle["bundle_hash"] = canonical_hash(
        {"accessions": normalized, "digests": [record["digest"] for record in linked]}
    )
    return bundle


def attach_accession_provenance(
    scenario_dict: Mapping[str, Any],
    accessions: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Return a scenario copy with accession provenance nested in realism_evidence."""
    out = dict(scenario_dict)
    evidence = dict(out.get("realism_evidence") or {})
    acc = [str(accession).strip() for accession in (accessions or [])]
    if any(not accession for accession in acc):
        raise ValueError("accessions must be non-empty strings")
    if not acc:
        acc = [str(accession).strip() for accession in (out.get("_evidence_accessions") or [])]
        acc = [accession for accession in acc if accession]
        if not acc:
            for ref in evidence.get("references") or []:
                if "acc=" in ref:
                    accession = ref.split("acc=", 1)[1].split("&", 1)[0].strip()
                    if accession:
                        acc.append(accession)
    evidence["host_omics_provenance"] = evidence_bundle_for_accessions(acc)
    out["realism_evidence"] = evidence
    return out
