"""Integrity and reproducibility gates for DCCP runs."""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .fingerprint import canonical_json, file_hash


@dataclass(frozen=True)
class IntegrityIssue:
    path: str
    kind: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def verify_file_hashes(manifest: dict[str, Any], base_dir: str | Path = ".") -> list[IntegrityIssue]:
    """Verify files listed in a manifest; missing files and hash drift fail closed."""
    base = Path(base_dir)
    issues: list[IntegrityIssue] = []
    for item in manifest.get("files", []):
        rel = str(item.get("path", ""))
        expected = str(item.get("sha256", ""))
        path = base / rel
        if not path.is_file():
            issues.append(IntegrityIssue(rel, "missing", "file is not present"))
            continue
        actual = file_hash(path)
        if expected and actual != expected:
            issues.append(IntegrityIssue(rel, "hash_mismatch", f"expected {expected}, got {actual}"))
    return issues


def manifest_for_files(paths: list[str | Path], base_dir: str | Path = ".") -> dict[str, Any]:
    base = Path(base_dir).resolve()
    files = []
    for raw in sorted((Path(p) for p in paths), key=lambda p: p.as_posix()):
        path = raw.resolve()
        try:
            rel = path.relative_to(base).as_posix()
        except ValueError:
            rel = path.as_posix()
        files.append({"path": rel, "sha256": file_hash(path), "size": path.stat().st_size})
    manifest = {"manifest_version": "1", "files": files}
    manifest["manifest_sha256"] = __import__("hashlib").sha256(canonical_json(manifest).encode()).hexdigest()
    return manifest
