#!/usr/bin/env python3
"""Collect public Kalshi data, simulate, and verify. Standard library only."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from simcomp.build import build, load_records, record_to_market, _bucket, _configs  # noqa: E402
from simcomp.collect import collect  # noqa: E402
from simcomp.engine import attach_later_results, run_competition  # noqa: E402
from simcomp.strategies import clone_strategies  # noqa: E402


def main() -> int:
    skip_collect = "--skip-collect" in sys.argv
    skip_program = "--skip-program" in sys.argv
    if not skip_collect:
        manifest = collect(ROOT)
        if not manifest.get("nobel_series"):
            print("No Nobel series were returned. Not inventing markets.", file=sys.stderr)
            return 1
    summary = build(ROOT, skip_program=skip_program)
    if summary["data_quality"]["status"] != "ok":
        print("Simulation bundle was not built from a Kalshi snapshot.", file=sys.stderr)
        return 1
    program = summary.get("program") or {}
    if not skip_program and program.get("replay", {}).get("status") != "matched":
        print("Program replay did not match. The bundle is not trustworthy.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
