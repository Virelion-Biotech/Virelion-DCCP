"""Release-readiness gates for challenge sets and benchmark artifacts."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .integrity import verify_file_hashes


def release_gate(
    registry: dict[str, Any],
    *,
    require_all_audited: bool = True,
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Validate registry structure, audit status, fingerprints, and listed files."""
    entries = registry.get("entries")
    failures: list[dict[str, Any]] = []
    if not isinstance(entries, list) or not entries:
        return {"passed": False, "n_entries": 0, "failures": [{"scenario_id": None, "reason": "empty_registry"}]}

    seen: set[str] = set()
    manifest_files: list[dict[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            failures.append({"scenario_id": None, "reason": "invalid_entry"})
            continue
        scenario_id = str(entry.get("scenario_id", "")).strip()
        if not scenario_id:
            failures.append({"scenario_id": None, "reason": "missing_scenario_id"})
        elif scenario_id in seen:
            failures.append({"scenario_id": scenario_id, "reason": "duplicate_scenario_id"})
        else:
            seen.add(scenario_id)
        path = str(entry.get("path", "")).strip()
        if not path:
            failures.append({"scenario_id": scenario_id or None, "reason": "missing_path"})
        digest = str(entry.get("content_sha256", "")).strip().lower()
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            failures.append({"scenario_id": scenario_id or None, "reason": "missing_or_invalid_fingerprint"})
        elif path:
            manifest_files.append({"path": path, "sha256": digest})
        if require_all_audited and not bool(entry.get("audit_passed", False)):
            failures.append({"scenario_id": scenario_id or None, "reason": "audit_failed"})

    if not failures:
        base = Path(base_dir if base_dir is not None else ".").resolve()
        root = Path(str(registry.get("root", ".")))
        if not root.is_absolute():
            root = (base / root).resolve()
        manifest = {
            "files": [
                {"path": str((root / item["path"]).resolve().relative_to(base)).replace("\\", "/"), "sha256": item["sha256"]}
                for item in manifest_files
            ]
        }
        for issue in verify_file_hashes(manifest, base):
            failures.append({"scenario_id": None, "reason": issue.kind, "path": issue.path, "detail": issue.detail})

    return {"passed": not failures, "n_entries": len(entries), "failures": failures}
