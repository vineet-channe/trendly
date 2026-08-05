"""CLI runner for the Trendly agent (Phase 5).

Usage:
  python -m app.cli
  python -m app.cli --message "where is TR-4525?"
  python -m app.cli --message "..." --trace

Defaults to a frozen clock at 2026-08-04 (NFR-3) so delay/return Done-when
checks stay stable; pass --live-clock to use wall time.
"""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime

from dotenv import load_dotenv

import app.config as config
from app.agent.loop import run_turn

REFERENCE_NOW = datetime(2026, 8, 4, 12, 0, 0)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Trendly support agent CLI")
    p.add_argument("--message", "-m", help="One-shot user message")
    p.add_argument("--session", "-s", default=None, help="Session id")
    p.add_argument("--trace", action="store_true", help="Print tool trace")
    p.add_argument(
        "--live-clock", action="store_true",
        help="Use wall-clock time instead of 2026-08-04",
    )
    return p.parse_args()


def _print_result(result: dict, show_trace: bool) -> None:
    print(result["reply"])
    if show_trace and result["trace"]:
        print("\n--- trace ---")
        print(json.dumps(result["trace"], indent=2, default=str))


def main() -> None:
    load_dotenv()
    args = _parse_args()
    if not args.live_clock:
        config.set_now_override(lambda: REFERENCE_NOW)

    session_id = args.session or str(uuid.uuid4())
    if args.message:
        _print_result(run_turn(session_id, args.message), args.trace)
        return

    print(f"Trendly CLI  session={session_id}  (empty line or Ctrl-D to quit)")
    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            break
        result = run_turn(session_id, line)
        print(f"agent> {result['reply']}")
        if args.trace and result["trace"]:
            print(json.dumps(result["trace"], indent=2, default=str))


if __name__ == "__main__":
    main()
