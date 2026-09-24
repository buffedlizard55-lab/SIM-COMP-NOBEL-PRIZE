#!/usr/bin/env python3
"""Re-run one program batch (or all) and compare ledger hashes with the manifest.

Usage:
    python scripts/verify_program.py batch-004
    python scripts/verify_program.py global        # all ten batches, slow
    python scripts/verify_program.py batch-001 --universe panel_settled

This is the manual-review replay: it rebuilds the batch from the stored Kalshi
candles and the registry in simcomp/research_program.py, recomputes the
per-participant ledger hashes, and compares them with
data/sim/program/ledger_hashes.json. A match reproduces the simulated ledger.
It is not evidence about Kalshi fills; no real orders exist.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from simcomp.build import load_records, record_to_market, _bucket  # noqa: E402
from simcomp.program import UNIVERSES, run_universe  # noqa: E402
from simcomp.research_program import program_variants  # noqa: E402


def main() -> int:
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    batch = args[0] if args else ""
    universe_arg = ""
    if "--universe" in sys.argv:
        index = sys.argv.index("--universe")
        if index + 1 < len(sys.argv):
            universe_arg = sys.argv[index + 1]
    variants = program_variants()
    if batch == "global":
        selected = variants
    elif batch:
        selected = [v for v in variants if v.batch == batch]
    else:
        print(__doc__)
        return 2
    if not selected:
        print(f"No variants for {batch}", file=sys.stderr)
        return 2
    hashes_path = ROOT / "data" / "sim" / "program" / "ledger_hashes.json"
    if not hashes_path.exists():
        print("data/sim/program/ledger_hashes.json is missing. Run python scripts/refresh.py first.", file=sys.stderr)
        return 1
    recorded = json.loads(hashes_path.read_text(encoding="utf-8"))
    records = load_records(ROOT)
    markets = [record_to_market(record) for record in records]
    grouped = {"nobel_forward": [], "nobel_settled": [], "panel_settled": []}
    for market in markets:
        bucket = _bucket(market)
        if bucket:
            grouped[bucket].append(market)
    universes = [universe_arg] if universe_arg else list(UNIVERSES)
    mismatches = 0
    checked = 0
    for universe in universes:
        result = run_universe(grouped.get(universe) or [], universe, selected, None)
        for pid, digest in result["ledger_hashes"].items():
            checked += 1
            if recorded.get(universe, {}).get(pid) != digest:
                mismatches += 1
                print(f"MISMATCH {universe} {pid}: rerun {digest} recorded {recorded.get(universe, {}).get(pid)}")
    if mismatches:
        print(f"{checked} participant ledgers checked, {mismatches} mismatches.")
        return 1
    scope = "all batches" if batch == "global" else batch
    print(f"OK: {checked} participant ledgers in {scope} reproduce the stored hashes across {len(universes)} universes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
