from __future__ import annotations

import argparse
import json
import logging
import sys

from .orchestration import run_once


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run application reminders through OpenClaw.")
    parser.add_argument("--slot", required=True, choices=["morning", "evening"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--print-only", action="store_true")
    parser.add_argument("--force-fallback", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(levelname)s %(message)s")

    try:
        result = run_once(
            args.slot,
            dry_run=args.dry_run,
            print_only=args.print_only,
            force_fallback=args.force_fallback,
        )
    except Exception as exc:
        print(f"application-notifier failed: {exc}", file=sys.stderr)
        return 1

    if result.skipped_locked:
        print("lock already held; exiting successfully")
        return 0

    if args.dry_run or args.print_only:
        print(json.dumps(result.payload, ensure_ascii=False, indent=2))
        print()
        print(result.fallback_text)
        return 0

    print("reminder dispatched")
    if result.bridge_stdout:
        print(result.bridge_stdout.rstrip())
    if result.bridge_stderr:
        print(result.bridge_stderr.rstrip(), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

