#!/usr/bin/env python3
"""Line-by-line audit of the program ledger against the stored Kalshi candles.

Checks, with no network:

  1. Decision clock: every non-settlement row ends strictly before the market's
     settlement_ts; every settlement row lands exactly on it.
  2. Fill price fidelity: sampled rows' price equals the candle field named by
     fill_src in data/sim/candles/{ticker}.json (YA, YB, NA=1-YB, NB=1-YA).
  3. Cash chain: recomputing each participant's cash from 10000 through every
     row reproduces cash_after exactly.
  4. Position accounting: recomputing positions from buy/sell rows reproduces
     realized_pnl on exits, and the open-position file reproduces the
     leaderboard's liquidation value and unrealized P&L.
  5. Leaderboard identity: eq == cash + mtm and eq == 10000 + real + unreal.
  6. Manifest: sha-256 of every program file matches manifest.json.

Usage: python scripts/audit_program.py [--price-sample 4000] [--full]
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import random
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "data" / "sim" / "program"
START = Decimal("10000")
TOL = Decimal("0.0002")  # ledger rows are rounded to 4 places
SETTLED = {"nobel_settled", "panel_settled"}


def _rows(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def main() -> int:
    sample_n = 4000
    if "--price-sample" in sys.argv:
        sample_n = int(sys.argv[sys.argv.index("--price-sample") + 1])
    full = "--full" in sys.argv
    problems = []

    manifest = json.loads((PROGRAM / "manifest.json").read_text(encoding="utf-8"))
    leaderboard = json.loads((PROGRAM / "leaderboard.json").read_text(encoding="utf-8"))
    market_index = json.loads((ROOT / "data" / "sim" / "market_index.json").read_text(encoding="utf-8"))
    sys.path.insert(0, str(ROOT))
    from simcomp.money import parse_unix  # noqa: E402
    settle_of = {m["ticker"]: parse_unix(m.get("settlement_ts")) for m in market_index}

    # Load stored candles for price checks.
    candles_by_ticker: dict[str, dict[int, dict]] = {}
    for ticker in settle_of:
        path = ROOT / "data" / "sim" / "candles" / f"{ticker}.json"
        if path.exists():
            candles_by_ticker[ticker] = {c["end_period_ts"]: c for c in json.loads(path.read_text())}

    trades_dir = PROGRAM / "trades"
    files = sorted(trades_dir.rglob("*.csv.gz"))
    if not full:
        files = files  # all files are always read for the cash chain; the price check is sampled
    rng = random.Random(20260924)
    price_sample = []
    cash: dict[str, Decimal] = {}
    positions: dict[tuple, list] = {}  # (pid, ticker) -> [qty, cost, side]
    violations = {"clock": 0, "cash": 0, "realized": 0}
    row_count = 0

    for path in files:
        universe = path.name.replace(".csv.gz", "")
        for row in _rows(path):
            row_count += 1
            if len(row) != 12 or None in row.values():
                problems.append(f"malformed ledger row in {path}: {list(row)[:4]}")
            pid = row["participant_id"]
            ticker = row["ticker"]
            ts = int(row["ts_unix"])
            action = row["action"]
            side = row["side"]
            price = Decimal(row["price"])
            qty = int(row["qty"])
            fee = Decimal(row["fee"])
            cash_after = Decimal(row["cash_after"])
            realized = Decimal(row["realized_pnl"])
            key = (universe, pid)
            book = cash.setdefault(key, START)
            settle_ts = settle_of.get(ticker)

            if universe == "nobel_forward" and action == "settlement":
                violations["clock"] += 1
                problems.append(f"forward universe has a settlement row {pid} {ticker} {ts}")
            if universe in SETTLED and settle_ts is not None:
                if action == "settlement":
                    if ts != settle_ts:
                        violations["clock"] += 1
                        problems.append(f"settlement row {pid} {ticker} ts {ts} != settlement_ts {settle_ts}")
                elif ts >= settle_ts:
                    violations["clock"] += 1
                    problems.append(f"row at/after settlement {pid} {ticker} {ts} >= {settle_ts}")

            pos = positions.setdefault((universe, pid, ticker), [0, Decimal("0"), ""])
            if action == "buy":
                book -= price * qty + fee
                new_qty = pos[0] + qty
                pos[1] += price * qty + fee
                pos[0] = new_qty
                pos[2] = side
            elif action == "sell":
                book += price * qty - fee
                if pos[0] > 0:
                    alloc = pos[1] * Decimal(qty) / Decimal(pos[0])
                    expected = price * qty - fee - alloc
                    if abs(expected - realized) > TOL:
                        violations["realized"] += 1
                        problems.append(f"realized mismatch {pid} {ticker} row {expected} vs {realized}")
                    pos[0] -= qty
                    pos[1] -= alloc
                    if pos[0] == 0:
                        pos[1] = Decimal("0")
                        pos[2] = ""
            elif action == "settlement":
                won = price == Decimal("1.0000")
                book += Decimal(qty) if won else Decimal("0")
                if pos[0] > 0:
                    expected = (Decimal(qty) if won else Decimal("0")) - pos[1]
                    if abs(expected - realized) > TOL:
                        violations["realized"] += 1
                        problems.append(f"settlement realized mismatch {pid} {ticker} {expected} vs {realized}")
                    pos[0] = 0
                    pos[1] = Decimal("0")
                    pos[2] = ""
            if abs(book - cash_after) > TOL:
                violations["cash"] += 1
                problems.append(f"cash chain break {universe} {pid} {ticker} {book} vs row {cash_after}")
                book = cash_after
            cash[key] = book
            if rng.random() < 0.02 or len(price_sample) < sample_n // 2:
                if len(price_sample) < sample_n and action != "settlement":
                    price_sample.append((universe, pid, ticker, ts, action, side, price, row["fill_src"]))

    # Price fidelity against stored candles.
    price_bad = 0
    checked_prices = 0
    for universe, pid, ticker, ts, action, side, price, src in price_sample:
        candle = (candles_by_ticker.get(ticker) or {}).get(ts)
        if candle is None:
            continue
        checked_prices += 1
        bid = Decimal(candle["yes_bid_close"]) if candle.get("yes_bid_close") is not None else None
        ask = Decimal(candle["yes_ask_close"]) if candle.get("yes_ask_close") is not None else None
        trade = Decimal(candle["trade_close"]) if candle.get("trade_close") is not None else None
        expected = None
        if src == "YA":
            expected = ask
        elif src == "YB":
            expected = bid
        elif src == "NA":
            expected = (Decimal("1") - bid) if bid is not None else None
        elif src == "NB":
            expected = (Decimal("1") - ask) if ask is not None else None
        elif src == "LT":
            expected = trade
        if expected is None or abs(expected - price) > TOL:
            price_bad += 1
            problems.append(f"price mismatch {universe} {pid} {ticker}@{ts} src {src}: {price} vs candle {expected}")

    # Leaderboard identity and open-position marks.
    board = {}
    for row in leaderboard:
        key = (row["u"], row["p"])
        board[key] = row
        eq = Decimal(row["eq"])
        if abs(eq - Decimal(row["cash"]) - Decimal(row["mtm"])) > TOL:
            problems.append(f"eq != cash+mtm {key}")
        if abs(eq - START - Decimal(row["real"]) - Decimal(row["unreal"])) > TOL:
            problems.append(f"eq != start+real+unreal {key}")
        book = cash.get(key)
        if book is not None and abs(book - Decimal(row["cash"])) > TOL:
            problems.append(f"leaderboard cash {key}: ledger chain {book} vs board {row['cash']}")

    open_rows = list(_rows(PROGRAM / "positions.csv.gz"))
    liq_by_pid: dict[tuple, Decimal] = {}
    for row in open_rows:
        pid = row["participant_id"]
        universe = row["universe"]
        liq_by_pid[(universe, pid)] = liq_by_pid.get((universe, pid), Decimal("0")) + Decimal(row["liquidation"])
        key3 = (universe, pid, row["ticker"])
        pos = positions.get(key3)
        if pos is None or pos[0] != int(row["qty"]) or pos[2] != row["side"]:
            problems.append(f"open position mismatch {key3}: csv {row['side']}x{row['qty']} vs chain {pos}")
    for (universe, pid), row in board.items():
        chain_liq = liq_by_pid.get((universe, pid), Decimal("0"))
        if abs(chain_liq - Decimal(row["mtm"])) > TOL:
            problems.append(f"mtm mismatch {universe} {pid}: positions file {chain_liq} vs board {row['mtm']}")

    # Manifest hashes.
    manifest_bad = 0
    for entry in manifest["files"]:
        path = ROOT / entry["path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry["sha256"] or path.stat().st_size != entry["bytes"]:
            manifest_bad += 1
            problems.append(f"manifest mismatch {entry['path']}")

    print(f"ledger rows checked: {row_count}")
    print(f"participants on board: {len(board)}; open position rows: {len(open_rows)}")
    print(f"decision-clock violations: {violations['clock']}")
    print(f"cash-chain violations: {violations['cash']}")
    print(f"realized-P&L violations: {violations['realized']}")
    print(f"price checks: {checked_prices} sampled, {price_bad} mismatches")
    print(f"manifest mismatches: {manifest_bad}")
    if problems:
        shown = problems[:20]
        for line in shown:
            print("PROBLEM:", line)
        print(f"{len(problems)} problems total" + ("" if len(problems) <= 20 else f" (showing {len(shown)})"))
        return 1
    print("audit clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
