"""Command-line interface for Virelion-DCCP."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .accession_provenance import evidence_bundle_for_accessions, panel_accession_records
from .audit import audit_scenario
from .cardisim_bridge import scenario_to_cardisim_payload
from .detectors import PrototypeDetector
from .evaluate import assess_scenario
from .library import load_library, materialize_challenge_set, write_challenge_set
from .omics_map import draft_scenario_from_scores, load_host_evidence_panel, map_module_scores_to_axes
from .provenance import scenario_digest
from .recovery import evaluate_recovery
from .scenario import load_scenario, validate_scenario


def _cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_scenario(data)
    if errors:
        print(f"INVALID: {path}")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"VALID: {path}")
    return 0


def _cmd_audit(args: argparse.Namespace) -> int:
    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    result = audit_scenario(data)
    status = "PASS" if result.passed else "FAIL"
    print(f"{status}: {result.scenario_id} ({path})")
    for e in result.schema_errors:
        print(f"  schema: {e}")
    for e in result.policy_errors:
        print(f"  policy-error: {e}")
    for w in result.policy_warnings:
        print(f"  warning: {w}")
    return 0 if result.passed else 1


def _cmd_show(args: argparse.Namespace) -> int:
    sc = load_scenario(args.path)
    print(f"scenario_id : {sc.scenario_id}")
    print(f"title       : {sc.title}")
    print(f"tissue      : {sc.tissue}")
    print(f"onset       : {sc.onset}")
    print(f"progression : {sc.progression}")
    print(f"confidence  : {sc.confidence}")
    print(f"ood_flag    : {sc.ood_flag}")
    print("phenotypic axes:")
    for k, v in sc.mechanism_summary().items():
        print(f"  {k:28s} {v}")
    return 0


def _cmd_audit_all(args: argparse.Namespace) -> int:
    root = Path(args.root)
    paths = sorted(root.rglob("*.json"))
    if not paths:
        print(f"No JSON files under {root}")
        return 1
    failed = 0
    for p in paths:
        data = json.loads(p.read_text(encoding="utf-8"))
        result = audit_scenario(data)
        status = "PASS" if result.passed else "FAIL"
        print(f"{status}: {p}")
        if not result.passed:
            failed += 1
            for e in result.schema_errors + result.policy_errors:
                print(f"  - {e}")
    print(f"\n{len(paths) - failed}/{len(paths)} passed")
    return 1 if failed else 0


def _cmd_assess(args: argparse.Namespace) -> int:
    sc = load_scenario(args.path)
    if args.detector == "prototype":
        assessment = PrototypeDetector().fit_default_ordinary().assess(sc)
    else:
        assessment = assess_scenario(sc)
    if args.json:
        print(json.dumps(assessment.as_dict(), indent=2))
    else:
        d = assessment.as_dict()
        print(f"scenario_id     : {d['scenario_id']}")
        print(f"abnormal        : {d['abnormal']} (score={d['abnormality_score']})")
        print(f"nearest ordinary: {d['nearest_ordinary']} (dist={d['distance_to_nearest_ordinary']})")
        print(f"ood_suggested   : {d['ood_suggested']}")
        print("mechanism profile:")
        for k, v in d["mechanism_profile"].items():
            print(f"  {k:28s} {v}")
        for n in d["notes"]:
            print(f"note: {n}")
    return 0


def _cmd_bridge(args: argparse.Namespace) -> int:
    sc = load_scenario(args.path)
    payload = scenario_to_cardisim_payload(sc)
    text = json.dumps(payload, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"Wrote CardiSim payload → {args.output}")
    else:
        print(text)
    return 0


def _cmd_hash(args: argparse.Namespace) -> int:
    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    print(scenario_digest(data))
    return 0


def _cmd_materialize(args: argparse.Namespace) -> int:
    out = Path(args.output)
    write_challenge_set(out, args.root)
    payload = materialize_challenge_set(args.root)
    print(f"Wrote challenge set → {out}")
    print(f"cases={payload['n_cases']} ood={payload['n_ood']} set_hash={payload['set_hash'][:16]}…")
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    for e in load_library(args.root):
        flag = "OOD" if e.scenario.ood_flag else "   "
        print(f"{e.scenario.scenario_id:16s} {flag}  {e.scenario.confidence:12s}  {e.path.name}")
    return 0


def _cmd_recovery_demo(args: argparse.Namespace) -> int:
    if args.baseline and args.challenged and args.rescued:
        baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        challenged = json.loads(Path(args.challenged).read_text(encoding="utf-8"))
        rescued = json.loads(Path(args.rescued).read_text(encoding="utf-8"))
    else:
        baseline = {
            "contractility": 0.62,
            "viability": 0.96,
            "inflammation": 0.10,
            "mitochondrial_health": 0.63,
            "oxidative_stress": 0.15,
            "fibrosis": 0.08,
            "metabolism": 0.55,
        }
        challenged = {
            "contractility": 0.28,
            "viability": 0.55,
            "inflammation": 0.72,
            "mitochondrial_health": 0.30,
            "oxidative_stress": 0.58,
            "fibrosis": 0.40,
            "metabolism": 0.32,
        }
        rescued = {
            "contractility": 0.48,
            "viability": 0.78,
            "inflammation": 0.35,
            "mitochondrial_health": 0.50,
            "oxidative_stress": 0.28,
            "fibrosis": 0.28,
            "metabolism": 0.45,
        }
    report = evaluate_recovery(
        scenario_id=args.scenario_id,
        intervention_name=args.intervention,
        baseline=baseline,
        challenged=challenged,
        rescued=rescued,
    )
    print(json.dumps(report.as_dict(), indent=2))
    return 0


def _cmd_surrogate(args: argparse.Namespace) -> int:
    sc = load_scenario(args.path)
    from .surrogate import run_challenge_with_rescue, run_scenario_surrogate

    try:
        if args.rescue:
            challenged, rescued, report = run_challenge_with_rescue(
                sc,
                duration=args.duration,
                n_cells=args.cells,
                seed=args.seed,
            )
            out = {
                "challenged": challenged,
                "rescued": rescued,
                "recovery": report.as_dict(),
            }
        else:
            out = run_scenario_surrogate(
                sc, duration=args.duration, n_cells=args.cells, seed=args.seed
            )
    except ImportError as e:
        print(str(e), file=sys.stderr)
        return 2
    text = json.dumps(out, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"Wrote → {args.output}")
    else:
        print(text)
    return 0


def _cmd_host_panel(args: argparse.Namespace) -> int:
    panel = load_host_evidence_panel()
    if args.json:
        print(json.dumps(panel, indent=2))
    else:
        for ds in panel.get("datasets") or []:
            print(f"{ds['accession']:12s}  {ds.get('organism', ''):28s}  {', '.join(ds.get('roles') or [])}")
        print("\naxis → accessions:")
        for axis, meta in (panel.get("axis_evidence") or {}).items():
            print(f"  {axis:28s} {', '.join(meta.get('accessions') or [])}")
    return 0


def _cmd_map_scores(args: argparse.Namespace) -> int:
    scores: dict[str, float] = {}
    for part in args.scores.split(","):
        part = part.strip()
        if not part:
            continue
        k, v = part.split("=")
        scores[k.strip()] = float(v.strip())
    mapped = map_module_scores_to_axes(scores)
    if args.draft_id:
        draft = draft_scenario_from_scores(
            scores,
            scenario_id=args.draft_id,
            title=args.title or f"Host-derived {args.draft_id}",
            ood_flag=args.ood,
            confidence=args.confidence,
        )
        clean = {k: v for k, v in draft.items() if not k.startswith("_")}
        text = json.dumps(clean, indent=2)
        if args.output:
            Path(args.output).write_text(text + "\n", encoding="utf-8")
            print(f"Wrote scenario draft → {args.output}")
        else:
            print(text)
    else:
        print(json.dumps(mapped.as_dict(), indent=2))
    return 0


def _cmd_accession_digest(args: argparse.Namespace) -> int:
    bundle = evidence_bundle_for_accessions(args.accessions)
    print(json.dumps(bundle, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dccp",
        description="Virelion-DCCP — defensive phenotypic challenge platform tools",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_val = sub.add_parser("validate", help="Validate a scenario against the JSON Schema")
    p_val.add_argument("path")
    p_val.set_defaults(func=_cmd_validate)

    p_aud = sub.add_parser("audit", help="Schema + policy audit of a scenario")
    p_aud.add_argument("path")
    p_aud.set_defaults(func=_cmd_audit)

    p_show = sub.add_parser("show", help="Pretty-print a validated scenario")
    p_show.add_argument("path")
    p_show.set_defaults(func=_cmd_show)

    p_all = sub.add_parser("audit-all", help="Audit all JSON files under a directory")
    p_all.add_argument("root", nargs="?", default="scenarios")
    p_all.set_defaults(func=_cmd_audit_all)

    p_assess = sub.add_parser("assess", help="Defensive assessment (abnormality / mechanism / OOD)")
    p_assess.add_argument("path")
    p_assess.add_argument("--json", action="store_true")
    p_assess.add_argument("--detector", choices=("heuristic", "prototype"), default="heuristic")
    p_assess.set_defaults(func=_cmd_assess)

    p_bridge = sub.add_parser("bridge", help="Emit CardiSim-compatible event payload")
    p_bridge.add_argument("path")
    p_bridge.add_argument("-o", "--output")
    p_bridge.set_defaults(func=_cmd_bridge)

    p_hash = sub.add_parser("hash", help="Canonical SHA-256 of a scenario JSON")
    p_hash.add_argument("path")
    p_hash.set_defaults(func=_cmd_hash)

    p_mat = sub.add_parser("materialize", help="Write hashed challenge set for evaluation / CardiBench")
    p_mat.add_argument("--root", default="scenarios")
    p_mat.add_argument("-o", "--output", default="benchmarks/dccp-challenge-set.v1.json")
    p_mat.set_defaults(func=_cmd_materialize)

    p_list = sub.add_parser("list", help="List scenarios in the library")
    p_list.add_argument("--root", default="scenarios")
    p_list.set_defaults(func=_cmd_list)

    p_rec = sub.add_parser("recovery-demo", help="Score recovery from state dicts (or built-in demo)")
    p_rec.add_argument("--baseline")
    p_rec.add_argument("--challenged")
    p_rec.add_argument("--rescued")
    p_rec.add_argument("--scenario-id", default="DEMO")
    p_rec.add_argument("--intervention", default="host_resilience_intervention")
    p_rec.set_defaults(func=_cmd_recovery_demo)

    p_sur = sub.add_parser("surrogate", help="Run CardiSim surrogate (requires cardisim)")
    p_sur.add_argument("path")
    p_sur.add_argument("--rescue", action="store_true")
    p_sur.add_argument("--duration", type=float, default=28.0)
    p_sur.add_argument("--cells", type=int, default=64)
    p_sur.add_argument("--seed", type=int, default=7)
    p_sur.add_argument("-o", "--output")
    p_sur.set_defaults(func=_cmd_surrogate)

    p_hp = sub.add_parser("host-panel", help="Show host multi-omics evidence panel (GEO metadata)")
    p_hp.add_argument("--json", action="store_true")
    p_hp.set_defaults(func=_cmd_host_panel)

    p_ms = sub.add_parser("map-scores", help="Map continuous host module scores → ordinal axes / scenario draft")
    p_ms.add_argument(
        "--scores",
        required=True,
        help="Comma list axis=float in [0,1], e.g. inflammatory=0.7,contractile_functional=0.6",
    )
    p_ms.add_argument("--draft-id", help="If set, emit full scenario JSON with this scenario_id")
    p_ms.add_argument("--title")
    p_ms.add_argument("--ood", action="store_true")
    p_ms.add_argument("--confidence", default="moderate")
    p_ms.add_argument("-o", "--output")
    p_ms.set_defaults(func=_cmd_map_scores)

    p_ad = sub.add_parser("accession-digest", help="Accession-level provenance bundle (CardiBench leakage note)")
    p_ad.add_argument("accessions", nargs="+")
    p_ad.set_defaults(func=_cmd_accession_digest)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
