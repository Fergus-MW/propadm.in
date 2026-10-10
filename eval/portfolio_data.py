"""Generate, validate and import a large synthetic portfolio for Propadmin."""

import argparse
import json
from pathlib import Path

from portfolio.build import build
from portfolio.check import read_pack


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("build")
    generate.add_argument("--out", type=Path, required=True)
    generate.add_argument("--properties", type=int, default=120)
    generate.add_argument("--seed", type=int, default=20261010)
    validate = commands.add_parser("validate")
    validate.add_argument("--pack", type=Path, required=True)
    ingest = commands.add_parser("ingest")
    ingest.add_argument("--pack", type=Path, required=True)
    ingest.add_argument("--platform-root", type=Path, required=True)
    ingest.add_argument("--out", type=Path, required=True)
    ingest.add_argument("--mode", choices=["sharded", "combined"], default="sharded")
    ingest.add_argument("--property", action="append", default=[])
    ingest.add_argument("--save-state", action="store_true")
    args = parser.parse_args()
    if args.command == "build":
        print(json.dumps(build(args.out, args.properties, args.seed), indent=2))
    elif args.command == "validate":
        manifest, _ = read_pack(args.pack)
        print(json.dumps({"status": "passed", "source_files": manifest["source_files"], "properties": manifest["properties"]}))
    else:
        from portfolio.load import load
        report = load(args.pack, args.platform_root, args.out, mode=args.mode,
                      selected=args.property, save_state=args.save_state)
        print(json.dumps({"passed": report["passed"], "errors": report["errors"]}))
        return int(bool(report["errors"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
