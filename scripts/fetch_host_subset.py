"""Download a public host count matrix and freeze a small technical test subset.

No subject/condition inference is attempted. Non-module genes are summed so the
complete per-cell library size survives the reduction. This is ingestion and
normalization verification, not disease classification or empirical axis validation.
"""

from __future__ import annotations

import gzip
import hashlib
from pathlib import Path
from urllib.request import urlopen

from dccp.host_modules import all_module_genes
from dccp.serialization import write_json

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE240nnn/GSE240848/suppl/"
MAX_BYTES = 250_000_000


def download(name):
    cache = ROOT / ".data-cache"
    cache.mkdir(exist_ok=True)
    target = cache / name
    if not target.exists():
        temporary = target.with_suffix(".partial")
        try:
            with urlopen(BASE + name, timeout=60) as response, temporary.open("wb") as handle:
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise ValueError("Source exceeds download budget")
                    handle.write(chunk)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    existing = ROOT / "validation/data/GSE240848_host_subset.json"
    if existing.exists():
        from dccp.serialization import read_json

        pinned = {item["url"]: item["sha256"] for item in read_json(existing)["source_files"]}
        if pinned.get(BASE + name) != digest.hexdigest():
            raise ValueError("Downloaded source differs from pinned SHA-256")
    return target, {
        "url": BASE + name,
        "sha256": digest.hexdigest(),
        "bytes": target.stat().st_size,
    }


def main():
    feature_path, feature_source = download("GSE240848_features.tsv.gz")
    barcode_path, barcode_source = download("GSE240848_barcodes.tsv.gz")
    matrix_path, matrix_source = download("GSE240848_matrix.mtx.gz")
    with gzip.open(feature_path, "rt") as handle:
        features = [line.rstrip().split("\t")[1].upper() for line in handle]
    with gzip.open(barcode_path, "rt") as handle:
        barcodes = [line.rstrip() for line in handle]
    n_selected = 16
    selected_markers = sorted(set(features) & all_module_genes())
    marker_index = {gene: index for index, gene in enumerate(selected_markers)}
    counts = [[0] * n_selected for _ in range(len(selected_markers) + 1)]
    with gzip.open(matrix_path, "rt") as handle:
        first = handle.readline().strip()
        if first != "%%MatrixMarket matrix coordinate integer general":
            raise ValueError("Expected integer coordinate MatrixMarket counts")
        line = handle.readline()
        while line.startswith("%"):
            line = handle.readline()
        n_genes, n_cells, nnz = map(int, line.split())
        if n_genes != len(features) or n_cells != len(barcodes):
            raise ValueError("Matrix/annotation dimensions differ")
        records = 0
        for line in handle:
            row, col, value = map(int, line.split())
            if not 1 <= row <= n_genes or not 1 <= col <= n_cells or value < 0:
                raise ValueError("Invalid coordinate/count")
            records += 1
            if col <= n_selected:
                target = marker_index.get(features[row - 1], len(selected_markers))
                counts[target][col - 1] += value
        if records != nnz:
            raise ValueError("Matrix entry count differs from header")
    payload = {
        "accession": "GSE240848",
        "scope": "technical 16-column input subset; no condition/donor labels",
        "selection": "first 16 matrix columns, chosen before computing scores; not representative cohort",
        "genes": [*selected_markers, "__NON_MODULE_COUNTS__"],
        "counts": counts,
        "barcodes": barcodes[:n_selected],
        "original_shape": [n_genes, n_cells],
        "original_nnz": nnz,
        "source_files": [feature_source, barcode_source, matrix_source],
        "aggregation": "duplicate marker symbols summed; all non-module rows pooled to retain complete library totals",
        "gene_symbol_counts": {gene: features.count(gene) for gene in selected_markers},
        "empirical_axis_validation": False,
    }
    write_json(ROOT / "validation/data/GSE240848_host_subset.json", payload)
    print(
        {
            "shape": payload["original_shape"],
            "nnz": nnz,
            "selected_columns": n_selected,
            "markers": len(selected_markers),
        }
    )


if __name__ == "__main__":
    main()
