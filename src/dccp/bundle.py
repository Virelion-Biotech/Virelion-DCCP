"""Portable reproducibility bundles for DCCP evaluations."""
from __future__ import annotations

import hashlib
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
    base_dir: str | Path = ".",
) -> dict[str, Any]:
    """Create a self-describing portable manifest without copying external datasets."""
    if not str(run_id).strip():
        raise ValueError("run_id must be non-empty")
    if not str(producer_version).strip():
        raise ValueError("producer_version must be non-empty")
    base = Path(base_dir).resolve()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = (out / "manifest.json").resolve()
    files: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in sorted((Path(p) for p in input_files), key=lambda p: p.as_posix()):
        path = raw.resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        try:
            relative = path.relative_to(base).as_posix()
        except ValueError as exc:
            raise ValueError(f"input file {path} is outside base_dir {base}") from exc
        if path == manifest_path:
            raise ValueError("bundle manifest cannot be listed as an input file")
        if relative in seen:
            continue
        seen.add(relative)
        files.append({"path": relative, "sha256": file_hash(path), "size": path.stat().st_size})
    manifest = {
        "bundle_version": "1",
        "run_id": str(run_id).strip(),
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "producer": "virelion-dccp",
        "producer_version": str(producer_version).strip(),
        "base_dir": ".",
        "environment": environment_snapshot(),
        "inputs": files,
        "records": records or {},
    }
    manifest["bundle_sha256"] = hashlib.sha256(canonical_json(manifest).encode("utf-8")).hexdigest()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return manifest
