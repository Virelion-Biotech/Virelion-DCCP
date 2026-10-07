"""Integrity and reproducibility gates for DCCP runs."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
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


def _resolve_relative(base: Path, rel: str) -> Path | None:
    candidate = (base / rel).resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        return None
    return candidate


def verify_file_hashes(
    manifest: dict[str, Any],
    base_dir: str | Path = ".",
) -> list[IntegrityIssue]:
    """Verify manifest files; missing paths, hashes, or hash drift fail closed."""
    base = Path(base_dir).resolve()
    issues: list[IntegrityIssue] = []
    if not isinstance(manifest, dict):
        return [IntegrityIssue("<manifest>", "invalid", "manifest must be an object")]
    fields = [("manifest_sha256", "files"), ("bundle_sha256", "inputs")]
    for digest_field, _ in fields:
        if digest_field in manifest:
            payload = {key: value for key, value in manifest.items() if key != digest_field}
            try:
                actual = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
            except (ValueError, TypeError):
                return [
                    IntegrityIssue("<manifest>", "invalid", "manifest contains non-portable JSON")
                ]
            if manifest[digest_field] != actual:
                issues.append(
                    IntegrityIssue(
                        "<manifest>",
                        "manifest_hash_mismatch",
                        f"{digest_field} does not match content",
                    )
                )
    files = manifest.get("files", manifest.get("inputs"))
    if not isinstance(files, list):
        return [IntegrityIssue("<manifest>", "invalid", "manifest.files must be a list")]

    seen = set()
    for item in files:
        if not isinstance(item, dict):
            issues.append(
                IntegrityIssue(
                    "<manifest>", "invalid", "each manifest file entry must be an object"
                )
            )
            continue
        rel = str(item.get("path", ""))
        if rel in seen:
            issues.append(IntegrityIssue(rel, "duplicate_path", "manifest paths must be unique"))
        seen.add(rel)
        expected = str(item.get("sha256", "")).strip().lower()
        if not rel:
            issues.append(IntegrityIssue("<manifest>", "invalid", "file entry is missing path"))
            continue
        if (
            not expected
            or len(expected) != 64
            or any(c not in "0123456789abcdef" for c in expected)
        ):
            issues.append(
                IntegrityIssue(
                    rel, "missing_hash", "sha256 must be a 64-character hexadecimal digest"
                )
            )
            continue
        path = _resolve_relative(base, rel)
        if path is None:
            issues.append(IntegrityIssue(rel, "unsafe_path", "manifest path escapes base_dir"))
            continue
        if not path.is_file():
            issues.append(IntegrityIssue(rel, "missing", "file is not present"))
            continue
        if "size" in item and (
            type(item["size"]) is not int or item["size"] != path.stat().st_size
        ):
            issues.append(IntegrityIssue(rel, "size_mismatch", "manifest size does not match file"))
        actual = file_hash(path)
        if actual != expected:
            issues.append(
                IntegrityIssue(rel, "hash_mismatch", f"expected {expected}, got {actual}")
            )
    return issues


def manifest_for_files(
    paths: list[str | Path],
    base_dir: str | Path = ".",
) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    files: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in sorted((Path(p) for p in paths), key=lambda p: p.as_posix()):
        path = raw.resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        try:
            rel = path.relative_to(base).as_posix()
        except ValueError as exc:
            raise ValueError(f"Input path is outside base_dir: {path}") from exc
        if rel in seen:
            continue
        seen.add(rel)
        files.append({"path": rel, "sha256": file_hash(path), "size": path.stat().st_size})
    manifest = {"manifest_version": "1", "files": files}
    manifest["manifest_sha256"] = hashlib.sha256(
        canonical_json(manifest).encode("utf-8")
    ).hexdigest()
    return manifest
