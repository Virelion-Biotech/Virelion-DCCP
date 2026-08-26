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
                **{k: v for k, v in extra.items() if v is not None},
            }
        )
    return records


def evidence_bundle_for_accessions(accessions: Sequence[str]) -> dict[str, Any]:
    """Provenance bundle linking listed accessions to panel digests."""
    by_acc = {r["accession"]: r for r in panel_accession_records()}
    linked = []
    missing = []
    for a in accessions:
        if a in by_acc:
            linked.append(by_acc[a])
        else:
            missing.append(a)
            linked.append({"accession": a, "digest": accession_digest(a), "status": "not_in_panel"})
    bundle = {
        "accessions": list(accessions),
        "records": linked,
        "missing_from_panel": missing,
        "leakage_policy_note": (
            "Accession digests are metadata-level only. Sample/donor/subject separation "
            "for model evaluation must be enforced in CardiBench split policies before "
            "any expression-level training or testing."
        ),
    }
    bundle["bundle_hash"] = canonical_hash(
        {"accessions": list(accessions), "digests": [r["digest"] for r in linked]}
    )
    return bundle


def attach_accession_provenance(
    scenario_dict: Mapping[str, Any],
    accessions: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Return a copy of scenario_dict with provenance block for host accessions."""
    out = dict(scenario_dict)
    acc = list(accessions or [])
    if not acc:
        # try from _evidence_accessions or parse references
        acc = list(out.get("_evidence_accessions") or [])
        if not acc:
            for ref in (out.get("realism_evidence") or {}).get("references") or []:
                if "acc=" in ref:
                    acc.append(ref.split("acc=")[-1].split("&")[0])
    out["host_omics_provenance"] = evidence_bundle_for_accessions(acc)
    return out
