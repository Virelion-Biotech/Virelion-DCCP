"""Command-line interface for Virelion-DCCP."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .audit import audit_scenario
from .cardisim_bridge import scenario_to_cardisim_payload
from .evaluate import assess_scenario
from .provenance import scenario_digest
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
    digest = scenario_digest(data)
    print(digest)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dccp",
        description="Virelion-DCCP — defensive phenotypic challenge platform tools",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_val = sub.add_parser("validate", help="Validate a scenario against the JSON Schema")
    p_val.add_argument("path", help="Path to scenario JSON")
    p_val.set_defaults(func=_cmd_validate)

    p_aud = sub.add_parser("audit", help="Schema + policy audit of a scenario")
    p_aud.add_argument("path", help="Path to scenario JSON")
    p_aud.set_defaults(func=_cmd_audit)

    p_show = sub.add_parser("show", help="Pretty-print a validated scenario")
    p_show.add_argument("path", help="Path to scenario JSON")
    p_show.set_defaults(func=_cmd_show)

    p_all = sub.add_parser("audit-all", help="Audit all JSON files under a directory")
    p_all.add_argument("root", nargs="?", default="scenarios", help="Root directory (default: scenarios)")
    p_all.set_defaults(func=_cmd_audit_all)

    p_assess = sub.add_parser("assess", help="Defensive assessment (abnormality / mechanism / OOD)")
    p_assess.add_argument("path", help="Path to scenario JSON")
    p_assess.add_argument("--json", action="store_true", help="Emit JSON")
    p_assess.set_defaults(func=_cmd_assess)

    p_bridge = sub.add_parser("bridge", help="Emit CardiSim-compatible event payload")
    p_bridge.add_argument("path", help="Path to scenario JSON")
    p_bridge.add_argument("-o", "--output", help="Write JSON to file instead of stdout")
    p_bridge.set_defaults(func=_cmd_bridge)

    p_hash = sub.add_parser("hash", help="Canonical SHA-256 of a scenario JSON")
    p_hash.add_argument("path", help="Path to scenario JSON")
    p_hash.set_defaults(func=_cmd_hash)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
