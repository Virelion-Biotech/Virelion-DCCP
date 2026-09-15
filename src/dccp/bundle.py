"""Portable reproducibility bundles for DCCP evaluations."""
from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .fingerprint import canonical_json, file_hash


def environment_snapshot() -> dict[str, str]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "implementation": platform.python_implementation(),
    }


def build_bundle(
    output_dir: str | Path,
    *,
    run_id: str,
    input_files: list[str | Path],
    records: dict[str, Any] | None = None,
    producer_version: str = "unknown",
) -> dict[str, Any]:
    """Create a self-describing bundle without copying external datasets."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = []
    for raw in input_files:
        path = Path(raw)
        if not path.is_file():
            raise FileNotFoundError(path)
        files.append({"path": str(path), "sha256": file_hash(path), "size": path.stat().st_size})
    manifest = {
        "bundle_version": "1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "producer": "virelion-dccp",
        "producer_version": producer_version,
        "environment": environment_snapshot(),
        "inputs": files,
        "records": records or {},
    }
    manifest["bundle_sha256"] = __import__("hashlib").sha256(canonical_json(manifest).encode()).hexdigest()
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
