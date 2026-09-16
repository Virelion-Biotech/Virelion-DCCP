"""Tests for reproducibility, registry, bundle, and evaluation infrastructure."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from dccp.bundle import build_bundle
from dccp.evaluation_protocol import CaseResult, summarize_cases, wilson_interval
from dccp.fingerprint import canonical_json, content_hash
from dccp.library import discover_scenarios, load_library
from dccp.registry import build_registry, write_registry


def test_canonical_hash_is_order_independent():
    assert canonical_json({"b": 2, "a": 1}) == canonical_json({"a": 1, "b": 2})
    assert content_hash({"b": 2, "a": 1}) == content_hash({"a": 1, "b": 2})


def test_canonical_json_rejects_non_finite_values():
    with pytest.raises(ValueError):
        canonical_json({"value": float("nan")})


def test_evaluation_summary_counts_confusion_matrix():
    result = summarize_cases(
        [
            CaseResult("A", True, True),
            CaseResult("B", True, False),
            CaseResult("C", False, True),
            CaseResult("D", False, False),
        ]
    )
    assert result["confusion"] == {"tp": 1, "tn": 1, "fp": 1, "fn": 1}
    assert result["accuracy"] == 0.5
    assert result["f1"] == 0.5


def test_wilson_interval_is_bounded():
    low, high = wilson_interval(8, 10)
    assert 0 <= low <= high <= 1


def test_discover_and_load_library_require_real_directory(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        discover_scenarios(tmp_path / "missing")
    with pytest.raises(FileNotFoundError):
        load_library(tmp_path / "missing")


def test_registry_can_ignore_its_generated_output(tmp_path: Path):
    source = Path(__file__).resolve().parents[1] / "scenarios" / "examples"
    for path in source.glob("*.json"):
        (tmp_path / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    output = tmp_path / "registry.json"
    first = write_registry(tmp_path, output)
    second = write_registry(tmp_path, output)
    assert first["n_entries"] == second["n_entries"]
    assert not any(entry["path"] == "registry.json" for entry in second["entries"])
    assert len(build_registry(tmp_path, exclude_paths=(output,))) == first["n_entries"]


def test_bundle_records_relative_paths_and_deduplicates(tmp_path: Path):
    source = tmp_path / "input.json"
    source.write_text(json.dumps({"x": 1}), encoding="utf-8")
    manifest = build_bundle(
        tmp_path / "bundle",
        run_id="RUN-1",
        input_files=[source, source],
        base_dir=tmp_path,
    )
    assert manifest["inputs"] == [{
        "path": "input.json",
        "sha256": manifest["inputs"][0]["sha256"],
        "size": source.stat().st_size,
    }]
    assert json.loads((tmp_path / "bundle" / "manifest.json").read_text(encoding="utf-8"))["bundle_sha256"] == manifest["bundle_sha256"]


def test_bundle_rejects_inputs_outside_base_dir(tmp_path: Path):
    outside = tmp_path.parent / "dccp-outside-input.json"
    outside.write_text("{}", encoding="utf-8")
    try:
        with pytest.raises(ValueError):
            build_bundle(tmp_path / "bundle", run_id="RUN-2", input_files=[outside], base_dir=tmp_path)
    finally:
        outside.unlink(missing_ok=True)
