"""python -m reality_claude <cases-dir> [--out ANSWERS] [--slots 6] [--hide-outcome] [--only 1,2] [--force]"""

import argparse
from pathlib import Path

from .runner import run_all


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", type=Path, help="folder of case folders (or one file per case)")
    parser.add_argument("--out", type=Path, default=Path("ANSWERS"))
    parser.add_argument("--slots", type=int, default=6, help="cases run in parallel")
    parser.add_argument("--port", type=int, default=8188)
    parser.add_argument("--timeout", type=int, default=360, help="seconds per live agent run")
    parser.add_argument("--hide-outcome", action="store_true",
                        help="drop Overview/Outcome sections from index.md (dry runs on solved public cases)")
    parser.add_argument("--only", help="comma-separated case ids or folder names")
    parser.add_argument("--force", action="store_true", help="re-run cases that already have an ANSWER.md")
    parser.add_argument("--fallback-only", action="store_true", help="skip Managed Agents; direct model calls")
    args = parser.parse_args()
    if not args.cases.is_dir():
        parser.error(f"{args.cases} is not a folder")
    run_all(args.cases, args.out, slots=args.slots, port=args.port, timeout=args.timeout,
            hide_outcome=args.hide_outcome, only=set(args.only.split(",")) if args.only else None,
            force=args.force, live=not args.fallback_only)


if __name__ == "__main__":
    main()
