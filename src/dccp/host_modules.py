"""Host gene modules for DCCP phenotypic axes and CardiSim phenotype bridges.

These are transparent proxy marker sets for host cardiac programs — not clinical
biomarkers and not pathogen/agent features.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

DCCP_AXIS_MODULES: dict[str, tuple[str, ...]] = {
    "inflammatory": ("IL1B", "TNF", "CCL2", "S100A8", "S100A9", "NFKBIA", "CXCL2"),
    "vascular_endothelial": ("KDR", "PECAM1", "EMCN", "ENG", "ESAM", "VWF", "ANGPT1"),
    "metabolic_mitochondrial": ("PPARGC1A", "CPT1B", "ACADM", "HADHA", "TFAM", "NDUFA1", "COX5A", "ATP5F1E"),
    "contractile_functional": ("TNNT2", "TNNI3", "ACTN2", "MYH7", "MYL2", "ACTC1"),
    "structural_injury": ("COL1A1", "COL3A1", "POSTN", "DCN", "LUM", "TAGLN"),
    "cell_death": ("BAX", "BCL2", "CASP3", "XIAP", "MCL1"),
    "remodeling": ("NPPA", "NPPB", "ACTA1", "COL1A1", "POSTN", "IGFBP3"),
}

MATURITY_MODULES: dict[str, tuple[str, ...]] = {
    "sarcomere_maturity": ("MYH7", "TNNI3", "TNNT2", "MYL2", "ACTN2"),
    "calcium_maturity": ("RYR2", "ATP2A2", "PLN", "CACNA1C", "CASQ2"),
    "metabolic_maturity": ("PPARGC1A", "CPT1B", "ACADVL", "FABP3", "PDK4"),
    "electrophysiology_maturity": ("SCN5A", "KCNJ2", "KCNH2", "KCNQ1", "GJA1"),
}

AXIS_TO_CARDISIM_PHENOTYPES: dict[str, tuple[str, ...]] = {
    "inflammatory": ("inflammation", "oxidative_stress"),
    "vascular_endothelial": ("angiogenesis",),
    "metabolic_mitochondrial": ("metabolism", "mitochondrial_health", "oxidative_stress"),
    "contractile_functional": ("contractility", "calcium_handling", "electrophysiology"),
    "structural_injury": ("fibrosis",),
    "cell_death": ("viability",),
    "remodeling": ("hypertrophy", "fibrosis", "maturity"),
}

ORDINAL_LEVELS = ("none", "low", "moderate", "substantial", "high", "severe")


def module_coverage(
    genes_present: Sequence[str],
    modules: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, float]:
    """Fraction of module genes found in an expression feature list."""
    present = {str(gene).strip().upper() for gene in genes_present if str(gene).strip()}
    selected = modules or DCCP_AXIS_MODULES
    return {
        name: sum(1 for gene in markers if str(gene).strip().upper() in present) / len(markers) if markers else 0.0
        for name, markers in selected.items()
    }


def all_module_genes() -> set[str]:
    genes: set[str] = set()
    for modules in (DCCP_AXIS_MODULES, MATURITY_MODULES):
        for markers in modules.values():
            genes.update(markers)
    return genes
