"""Independent numeric checks and label-blind defensive baseline evaluation."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys

import numpy as np

from dccp import __version__
from dccp.detectors import PrototypeDetector
from dccp.evaluate import assess_scenario
from dccp.evaluation_protocol import CaseResult, summarize_cases, wilson_interval
from dccp.fingerprint import file_hash
from dccp.host_features import extract_host_features, log1p_cpm_rows
from dccp.host_modules import DCCP_AXIS_MODULES, MATURITY_MODULES
from dccp.library import load_library, materialize_challenge_set
from dccp.recovery import evaluate_recovery
from dccp.serialization import read_json, write_json

ROOT = Path(__file__).resolve().parents[1]


def validate():
    data_path = ROOT / "validation/data/GSE240848_host_subset.json"
    data = read_json(data_path)
    counts = np.asarray(data["counts"], dtype=float)
    totals = np.sum(counts, axis=0)
    exact = np.log1p(counts / totals * 10_000.0)
    actual = np.asarray(log1p_cpm_rows(data["counts"]))
    error = float(np.max(np.abs(exact - actual)))
    features = extract_host_features(data["counts"], data["genes"])
    gene_index = {gene: index for index, gene in enumerate(data["genes"])}
    module_errors = []
    for name, markers in {**DCCP_AXIS_MODULES, **MATURITY_MODULES}.items():
        rows = [gene_index[gene] for gene in markers if gene in gene_index]
        if rows:
            module_errors.append(abs(features.module_log_means[name] - float(np.mean(exact[rows]))))
    checks = {
        "real_input_normalization": {
            "passed": error < 1e-12,
            "maximum_error": error,
            "columns": int(counts.shape[1]),
            "normalization_target": 10_000,
        },
        "marker_module_means": {
            "passed": max(module_errors) < 1e-12,
            "maximum_error": max(module_errors),
            "module_count": len(module_errors),
        },
    }
    scaled = np.asarray(log1p_cpm_rows((counts * 7).tolist()))
    permuted = np.asarray(log1p_cpm_rows(counts[::-1].tolist()))[::-1]
    checks["library_scale_and_gene_order_invariance"] = {
        "passed": bool(
            np.allclose(actual, scaled, atol=1e-12, rtol=0) and np.array_equal(actual, permuted)
        ),
        "maximum_scaled_error": float(np.max(np.abs(actual - scaled))),
    }
    scenarios = [entry.scenario for entry in load_library(ROOT / "scenarios/examples")]
    detectors = {
        "heuristic": assess_scenario,
        "prototype": PrototypeDetector().fit_default_ordinary().assess,
    }
    evaluation = {}
    invariant = True
    for name, assess in detectors.items():
        rows = []
        for scenario in scenarios:
            result = assess(scenario)
            flipped = assess(replace(scenario, ood_flag=not scenario.ood_flag))
            invariant &= result.ood_suggested == flipped.ood_suggested
            rows.append(
                CaseResult(
                    scenario.scenario_id,
                    True,
                    result.abnormal,
                    score=result.abnormality_score,
                    ood_expected=scenario.ood_flag,
                    ood_predicted=result.ood_suggested,
                )
            )
        summary = summarize_cases(rows)
        summary["ood_confusion"] = summarize_cases(
            [CaseResult(r.scenario_id, r.ood_expected, r.ood_predicted) for r in rows]
        )["confusion"]
        successes = sum(row.ood_expected == row.ood_predicted for row in rows)
        summary["ood_accuracy_wilson_95"] = list(wilson_interval(successes, len(rows)))
        summary["label_scope"] = (
            "Scenario design flags only; not independent empirical OOD ground truth"
        )
        evaluation[name] = summary
    checks["ood_label_blindness"] = {
        "passed": bool(invariant),
        "paired_cases": len(scenarios) * len(detectors),
    }
    # Independently specified 50% restoration in one positive and one burden domain.
    recovery = evaluate_recovery(
        scenario_id="SYNTHETIC",
        intervention_name="numeric-check",
        baseline={"viability": 1.0, "inflammation": 0.0},
        challenged={"viability": 0.4, "inflammation": 0.8},
        rescued={"viability": 0.7, "inflammation": 0.4},
    )
    checks["analytic_recovery"] = {
        "passed": abs(recovery.overall_recovery - 0.5) < 1e-12,
        "observed": recovery.overall_recovery,
        "expected": 0.5,
    }
    lo, hi = wilson_interval(0, 10)
    checks["wilson_known_endpoint"] = {
        "passed": abs(lo) < 1e-14 and abs(hi - 0.2775401687666166) < 1e-12,
        "interval": [lo, hi],
    }
    first = materialize_challenge_set(ROOT / "scenarios/examples")
    second = materialize_challenge_set("scenarios/examples")
    checks["portable_challenge_hash"] = {
        "passed": first["set_hash"] == second["set_hash"],
        "set_hash": first["set_hash"],
    }
    files = [
        *sorted((ROOT / "src/dccp").rglob("*.py")),
        Path(__file__),
        data_path,
        *sorted((ROOT / "src/dccp/data").rglob("*.json")),
        *sorted((ROOT / "scenarios/examples").glob("*.json")),
    ]
    return {
        "version": __version__,
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__},
        "passed": all(check["passed"] for check in checks.values()),
        "scope": "Computational verification on real public counts and synthetic fixtures; no calibrated biological validation",
        "checks": checks,
        "detector_baselines": evaluation,
        "host_features": features.as_dict(),
        "input_source_files": data["source_files"],
        "source_sha256": {str(path.relative_to(ROOT)): file_hash(path) for path in files},
        "empirical_validation": {
            "status": "not_validated",
            "blockers": [
                "subject/condition mapping unresolved for test subset",
                "module directions and ordinal thresholds uncalibrated",
                "no independent clinical OOD labels",
                "no held-out biological recovery measurements",
            ],
        },
    }


if __name__ == "__main__":
    report = validate()
    write_json(ROOT / "validation/cpu/results.json", report)
    print(
        {
            "passed": report["passed"],
            "checks": report["checks"],
            "ood_accuracy": {
                name: value["ood_accuracy"] for name, value in report["detector_baselines"].items()
            },
        }
    )
    raise SystemExit(0 if report["passed"] else 1)
