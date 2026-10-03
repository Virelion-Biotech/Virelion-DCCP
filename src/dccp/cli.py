"""Command-line interface for Virelion-DCCP."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .accession_provenance import evidence_bundle_for_accessions
from .audit import audit_scenario
from .bundle import build_bundle
from .cardisim_bridge import scenario_to_cardisim_payload
from .detectors import PrototypeDetector
from .evaluate import assess_scenario
from .integrity import verify_file_hashes
from .library import load_library, materialize_challenge_set
from .omics_map import draft_scenario_from_scores, load_host_evidence_panel, map_module_scores_to_axes
from .provenance import scenario_digest
from .recovery import evaluate_recovery
from .registry import write_registry
from .release_gate import release_gate
from .scenario import load_scenario, validate_scenario


def _read_json(path: str | Path):
    path = Path(path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"unable to read JSON {path}: {exc}") from exc


def _write_json(path: str | Path, payload) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _cmd_validate(args: argparse.Namespace) -> int:
    errors = validate_scenario(_read_json(args.path))
    if errors:
        print(f"INVALID: {args.path}")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"VALID: {args.path}")
    return 0


def _cmd_audit(args: argparse.Namespace) -> int:
    result = audit_scenario(_read_json(args.path))
    print(f"{'PASS' if result.passed else 'FAIL'}: {result.scenario_id} ({args.path})")
    for error in result.schema_errors:
        print(f"  schema: {error}")
    for error in result.policy_errors:
        print(f"  policy-error: {error}")
    for warning in result.policy_warnings:
        print(f"  warning: {warning}")
    return 0 if result.passed else 1


def _cmd_show(args: argparse.Namespace) -> int:
    scenario = load_scenario(args.path)
    print(f"scenario_id : {scenario.scenario_id}")
    print(f"title       : {scenario.title}")
    print(f"tissue      : {scenario.tissue}")
    print(f"onset       : {scenario.onset}")
    print(f"progression : {scenario.progression}")
    print(f"confidence  : {scenario.confidence}")
    print(f"ood_flag    : {scenario.ood_flag}")
    print("phenotypic axes:")
    for key, value in scenario.mechanism_summary().items():
        print(f"  {key:28s} {value}")
    return 0


def _cmd_audit_all(args: argparse.Namespace) -> int:
    root = Path(args.root)
    if not root.is_dir():
        print(f"Directory not found: {root}", file=sys.stderr)
        return 2
    paths = sorted(root.rglob("*.json"))
    if not paths:
        print(f"No JSON files under {root}")
        return 1
    failed = 0
    for path in paths:
        result = audit_scenario(_read_json(path))
        print(f"{'PASS' if result.passed else 'FAIL'}: {path}")
        if not result.passed:
            failed += 1
            for error in result.schema_errors + result.policy_errors:
                print(f"  - {error}")
    print(f"\n{len(paths) - failed}/{len(paths)} passed")
    return 1 if failed else 0


def _cmd_assess(args: argparse.Namespace) -> int:
    scenario = load_scenario(args.path)
    assessment = PrototypeDetector().fit_default_ordinary().assess(scenario) if args.detector == "prototype" else assess_scenario(scenario)
    if args.json:
        print(json.dumps(assessment.as_dict(), indent=2, allow_nan=False))
        return 0
    data = assessment.as_dict()
    print(f"scenario_id     : {data['scenario_id']}")
    print(f"abnormal        : {data['abnormal']} (score={data['abnormality_score']})")
    print(f"nearest ordinary: {data['nearest_ordinary']} (dist={data['distance_to_nearest_ordinary']})")
    print(f"ood_suggested   : {data['ood_suggested']}")
    for key, value in data["mechanism_profile"].items():
        print(f"  {key:28s} {value}")
    for note in data["notes"]:
        print(f"note: {note}")
    return 0


def _cmd_bridge(args: argparse.Namespace) -> int:
    payload = scenario_to_cardisim_payload(load_scenario(args.path))
    if args.output:
        _write_json(args.output, payload)
        print(f"Wrote CardiSim payload -> {args.output}")
    else:
        print(json.dumps(payload, indent=2, allow_nan=False))
    return 0


def _cmd_hash(args: argparse.Namespace) -> int:
    print(scenario_digest(_read_json(args.path)))
    return 0


def _cmd_materialize(args: argparse.Namespace) -> int:
    payload = materialize_challenge_set(args.root)
    _write_json(args.output, payload)
    print(f"Wrote challenge set -> {args.output}")
    print(f"cases={payload['n_cases']} ood={payload['n_ood']} set_hash={payload['set_hash'][:16]}...")
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    for entry in load_library(args.root):
        flag = "OOD" if entry.scenario.ood_flag else "   "
        print(f"{entry.scenario.scenario_id:16s} {flag}  {entry.scenario.confidence:12s}  {entry.path.name}")
    return 0


def _cmd_recovery_demo(args: argparse.Namespace) -> int:
    baseline = _read_json(args.baseline) if args.baseline else {"contractility": 0.62, "viability": 0.96, "inflammation": 0.10, "mitochondrial_health": 0.63, "oxidative_stress": 0.15, "fibrosis": 0.08, "metabolism": 0.55}
    challenged = _read_json(args.challenged) if args.challenged else {"contractility": 0.28, "viability": 0.55, "inflammation": 0.72, "mitochondrial_health": 0.30, "oxidative_stress": 0.58, "fibrosis": 0.40, "metabolism": 0.32}
    rescued = _read_json(args.rescued) if args.rescued else {"contractility": 0.48, "viability": 0.78, "inflammation": 0.35, "mitochondrial_health": 0.50, "oxidative_stress": 0.28, "fibrosis": 0.28, "metabolism": 0.45}
    report = evaluate_recovery(scenario_id=args.scenario_id, intervention_name=args.intervention, baseline=baseline, challenged=challenged, rescued=rescued)
    print(json.dumps(report.as_dict(), indent=2, allow_nan=False))
    return 0


def _cmd_surrogate(args: argparse.Namespace) -> int:
    from .surrogate import run_challenge_with_rescue, run_scenario_surrogate

    scenario = load_scenario(args.path)
    if args.rescue:
        _, rescued, report = run_challenge_with_rescue(scenario, duration=args.duration, n_cells=args.cells, seed=args.seed)
        output = {"rescued": rescued, "recovery": report.as_dict()}
    else:
        output = run_scenario_surrogate(scenario, duration=args.duration, n_cells=args.cells, seed=args.seed)
    if args.output:
        _write_json(args.output, output)
        print(f"Wrote -> {args.output}")
    else:
        print(json.dumps(output, indent=2, allow_nan=False))
    return 0


def _parse_scores(raw: str) -> dict[str, float]:
    scores: dict[str, float] = {}
    for part in raw.split(","):
        item = part.strip()
        if not item:
            continue
        if item.count("=") != 1:
            raise ValueError(f"invalid score item {item!r}; expected axis=value")
        key, value = (piece.strip() for piece in item.split("=", 1))
        if not key or key in scores:
            raise ValueError(f"invalid or duplicate score axis: {key!r}")
        score = float(value)
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"score for {key} must be within [0, 1]")
        scores[key] = score
    if not scores:
        raise ValueError("at least one score is required")
    return scores


def _cmd_host_panel(args: argparse.Namespace) -> int:
    panel = load_host_evidence_panel()
    if args.json:
        print(json.dumps(panel, indent=2, allow_nan=False))
        return 0
    for dataset in panel.get("datasets") or []:
        print(f"{dataset['accession']:12s}  {dataset.get('organism', ''):28s}  {', '.join(dataset.get('roles') or [])}")
    print("\naxis -> accessions:")
    for axis, meta in (panel.get("axis_evidence") or {}).items():
        print(f"  {axis:28s} {', '.join(meta.get('accessions') or [])}")
    return 0


def _cmd_map_scores(args: argparse.Namespace) -> int:
    scores = _parse_scores(args.scores)
    mapped = map_module_scores_to_axes(scores)
    if not args.draft_id:
        print(json.dumps(mapped.as_dict(), indent=2, allow_nan=False))
        return 0
    draft = draft_scenario_from_scores(scores, scenario_id=args.draft_id, title=args.title or f"Host-derived {args.draft_id}", ood_flag=args.ood, confidence=args.confidence)
    if args.output:
        _write_json(args.output, draft)
        print(f"Wrote scenario draft -> {args.output}")
    else:
        print(json.dumps(draft, indent=2, allow_nan=False))
    return 0


def _cmd_accession_digest(args: argparse.Namespace) -> int:
    print(json.dumps(evidence_bundle_for_accessions(args.accessions), indent=2, allow_nan=False))
    return 0


def _cmd_registry(args: argparse.Namespace) -> int:
    payload = write_registry(args.root, args.output)
    print(f"Wrote registry -> {args.output} ({payload['n_audited']}/{payload['n_entries']} audited)")
    return 0


def _cmd_release_gate(args: argparse.Namespace) -> int:
    result = release_gate(_read_json(args.registry), base_dir=args.base)
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result["passed"] else 1


def _cmd_integrity(args: argparse.Namespace) -> int:
    issues = verify_file_hashes(_read_json(args.manifest), args.base)
    print(json.dumps({"passed": not issues, "issues": [issue.as_dict() for issue in issues]}, indent=2, allow_nan=False))
    return 0 if not issues else 1


def _cmd_bundle(args: argparse.Namespace) -> int:
    manifest = build_bundle(args.output_dir, run_id=args.run_id, input_files=args.input_files, producer_version=args.producer_version)
    print(json.dumps(manifest, indent=2, allow_nan=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="dccp", description="Virelion-DCCP defensive phenotypic challenge platform tools")
    root.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = root.add_subparsers(dest="command", required=True)

    parser = sub.add_parser("validate", help="Validate a scenario against the JSON Schema")
    parser.add_argument("path"); parser.set_defaults(func=_cmd_validate)
    parser = sub.add_parser("audit", help="Schema + policy audit of a scenario")
    parser.add_argument("path"); parser.set_defaults(func=_cmd_audit)
    parser = sub.add_parser("show", help="Pretty-print a validated scenario")
    parser.add_argument("path"); parser.set_defaults(func=_cmd_show)
    parser = sub.add_parser("audit-all", help="Audit all JSON files under a directory")
    parser.add_argument("root", nargs="?", default="scenarios"); parser.set_defaults(func=_cmd_audit_all)

    parser = sub.add_parser("assess", help="Defensive assessment")
    parser.add_argument("path"); parser.add_argument("--json", action="store_true"); parser.add_argument("--detector", choices=("heuristic", "prototype"), default="heuristic"); parser.set_defaults(func=_cmd_assess)
    parser = sub.add_parser("bridge", help="Emit CardiSim-compatible event payload")
    parser.add_argument("path"); parser.add_argument("-o", "--output"); parser.set_defaults(func=_cmd_bridge)
    parser = sub.add_parser("hash", help="Canonical SHA-256 of a scenario JSON")
    parser.add_argument("path"); parser.set_defaults(func=_cmd_hash)
    parser = sub.add_parser("materialize", help="Write hashed challenge set")
    parser.add_argument("--root", default="scenarios"); parser.add_argument("-o", "--output", default="benchmarks/dccp-challenge-set.v1.json"); parser.set_defaults(func=_cmd_materialize)
    parser = sub.add_parser("list", help="List scenarios in the library")
    parser.add_argument("--root", default="scenarios"); parser.set_defaults(func=_cmd_list)
    parser = sub.add_parser("recovery-demo", help="Score recovery from state dicts")
    parser.add_argument("--baseline"); parser.add_argument("--challenged"); parser.add_argument("--rescued"); parser.add_argument("--scenario-id", default="DEMO"); parser.add_argument("--intervention", default="host_resilience_intervention"); parser.set_defaults(func=_cmd_recovery_demo)
    parser = sub.add_parser("surrogate", help="Run CardiSim surrogate")
    parser.add_argument("path"); parser.add_argument("--rescue", action="store_true"); parser.add_argument("--duration", type=float, default=28.0); parser.add_argument("--cells", type=int, default=64); parser.add_argument("--seed", type=int, default=7); parser.add_argument("-o", "--output"); parser.set_defaults(func=_cmd_surrogate)
    parser = sub.add_parser("host-panel", help="Show host multi-omics evidence panel")
    parser.add_argument("--json", action="store_true"); parser.set_defaults(func=_cmd_host_panel)
    parser = sub.add_parser("map-scores", help="Map continuous host module scores to ordinal axes")
    parser.add_argument("--scores", required=True); parser.add_argument("--draft-id"); parser.add_argument("--title"); parser.add_argument("--ood", action="store_true"); parser.add_argument("--confidence", choices=("high", "moderate", "exploratory"), default="moderate"); parser.add_argument("-o", "--output"); parser.set_defaults(func=_cmd_map_scores)
    parser = sub.add_parser("accession-digest", help="Accession-level provenance bundle")
    parser.add_argument("accessions", nargs="+"); parser.set_defaults(func=_cmd_accession_digest)
    parser = sub.add_parser("registry", help="Build deterministic scenario registry")
    parser.add_argument("--root", default="scenarios"); parser.add_argument("-o", "--output", default="benchmarks/scenario-registry.v1.json"); parser.set_defaults(func=_cmd_registry)
    parser = sub.add_parser("release-gate", help="Evaluate a scenario registry release gate")
    parser.add_argument("registry"); parser.add_argument("--base", default="."); parser.set_defaults(func=_cmd_release_gate)
    parser = sub.add_parser("integrity", help="Verify files listed in a manifest")
    parser.add_argument("manifest"); parser.add_argument("--base", default="."); parser.set_defaults(func=_cmd_integrity)
    parser = sub.add_parser("bundle", help="Create a reproducibility manifest bundle")
    parser.add_argument("--output-dir", required=True); parser.add_argument("--run-id", required=True); parser.add_argument("--producer-version", default=__version__); parser.add_argument("--input-files", nargs="+", required=True); parser.set_defaults(func=_cmd_bundle)
    return root


def main(argv: list[str] | None = None) -> int:
    root = build_parser()
    try:
        args = root.parse_args(argv)
        return args.func(args)
    except (OSError, ValueError, ImportError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
