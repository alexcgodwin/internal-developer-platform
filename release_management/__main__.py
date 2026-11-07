"""Release management CLI. All operations are local; no cloud API calls."""
import argparse
import json
import sys
from pathlib import Path

from .core import Ledger, ReleaseError, inventory, prepare, read_json, validate_request


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Offline release preparation and operator-attested inventory")
    p.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root (default current directory)")
    sub = p.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("prepare", help="Preflight and optionally write candidate desired release manifest")
    pre.add_argument("--request", required=True, type=Path)
    pre.add_argument("--write", action="store_true", help="Write Git-tracked candidate; otherwise dry run")
    pre.add_argument("--replace", action="store_true", help="Allow replacing existing candidate")
    pre.add_argument("--allow-production-preparation", action="store_true", help="Allow production intent file only, not deployment")

    rec = sub.add_parser("record-observation", help="Record explicitly unverified operator observation")
    rec.add_argument("--request", required=True, type=Path)
    rec.add_argument("--outcome", required=True, choices=["succeeded", "failed"])
    rec.add_argument("--evidence-url", required=True, help="External HTTPS log or deployment evidence URL")
    rec.add_argument("--operator", required=True)

    sub.add_parser("inventory", help="Compare candidate desired releases with recorded operator claims")
    sub.add_parser("audit", help="Validate local ledger chain integrity")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = args.root.resolve()
    ledger = Ledger(root / ".local" / "release-tracking" / "observations.jsonl")
    try:
        if args.command == "prepare":
            result = prepare(root, read_json(args.request), write=args.write,
                             allow_production=args.allow_production_preparation, replace=args.replace)
        elif args.command == "record-observation":
            result = ledger.append_observation(validate_request(read_json(args.request)), outcome=args.outcome,
                                               evidence=args.evidence_url, operator=args.operator)
        elif args.command == "inventory":
            result = {"source": "local release intent and unverified operator assertions",
                      "runtime_query_performed": False, "releases": inventory(root, ledger)}
        else:
            result = {"ledger_verified": True, "record_count": len(ledger.read()),
                      "meaning": "Hash continuity only; not authentication or independent deployment verification"}
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (ReleaseError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
