"""Program tests. Engine parity uses constructed candles; no network calls."""

from __future__ import annotations

import hashlib
import json
import unittest
from collections import Counter
from decimal import Decimal
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from simcomp.engine import SimConfig, run_competition  # noqa: E402
from simcomp.kalshi_parse import Candle, Market  # noqa: E402
from simcomp.program import PROGRAM_PRIOR_WINDOW, run_universe  # noqa: E402
from simcomp.research_program import EntryTimingBand, Variant, program_variants  # noqa: E402
from simcomp.strategies import Decision, PARTICIPANTS, clone_strategies  # noqa: E402


def candle(ts, bid, ask, trade=None, volume="10"):
    return Candle(
        end_period_ts=ts,
        yes_bid_close=Decimal(bid) if bid is not None else None,
        yes_ask_close=Decimal(ask) if ask is not None else None,
        trade_close=Decimal(trade) if trade is not None else None,
        volume=Decimal(volume) if volume is not None else None,
        open_interest=Decimal("1"),
    )


def market(ticker="M1", result="", status="active", settlement_ts=None, candles=None, universe="nobel"):
    return Market(
        ticker=ticker,
        event_ticker="E1",
        series_ticker="KXTEST",
        title="Test market",
        subtitle="",
        rules_primary="If the test event happens, the market resolves to Yes.",
        status=status,
        result=result,
        market_type="binary",
        open_time=1000,
        close_time=9000,
        settlement_ts=settlement_ts,
        expected_expiration_time=9000,
        fee_type="quadratic",
        fee_multiplier="1",
        volume="10",
        tier="live",
        source_url="https://external-api.kalshi.com/trade-api/v2/markets/" + ticker,
        candle_source_url="https://example.invalid/candles",
        settlement_sources=[{"name": "Test", "url": "https://example.invalid"}],
        candles=candles or [],
        universe=universe,
    )


def parity_markets():
    uptrend = market(
        "M-UP", result="yes", status="finalized", settlement_ts=8000,
        candles=[
            candle(2000, "0.66", "0.68", "0.67", "30"),
            candle(3000, "0.70", "0.72", "0.71", "45"),
            candle(4000, "0.74", "0.77", "0.75", "60"),
            candle(5000, "0.80", "0.83", None, "25"),
        ],
    )
    choppy = market(
        "M-CHOP", result="no", status="finalized", settlement_ts=9000,
        candles=[
            candle(2000, "0.40", "0.44", "0.42", "12"),
            candle(3000, "0.30", "0.33", "0.31", "40"),
            candle(4000, "0.48", "0.52", "0.50", "9"),
            candle(5000, "0.35", "0.38", "0.36", "55"),
            candle(6000, "0.44", "0.47", None, "21"),
        ],
    )
    forward = market(
        "M-FWD",
        candles=[
            candle(2000, "0.55", "0.59", "0.57", "18"),
            candle(3000, "0.60", "0.63", "0.62", "27"),
            candle(4000, "0.52", "0.56", "0.54", "8"),
        ],
    )
    thin = market(
        "M-THIN",
        candles=[
            candle(2000, None, "0.05", None, None),  # one-sided: no YES bid
            candle(3000, "0.03", "0.07", "0.05", "3"),
        ],
    )
    return [uptrend, choppy, forward, thin]


def primary_variants() -> list[Variant]:
    """Wrap the 11 primary strategies as program variants with the same usernames."""
    by_id = {s.id: s for s in clone_strategies()}
    variants = []
    for index, (username, strategy_id, display) in enumerate(PARTICIPANTS, start=1):
        strategy = by_id[strategy_id]
        strategy.parameters = dict(strategy.parameters)
        variants.append(Variant(
            batch="parity",
            topic="parity",
            family=strategy_id,
            strategy_id=strategy_id,
            username=username,
            display_name=display,
            hypothesis="parity wrapper",
            strategy=strategy,
        ))
    return variants


def canonical_hash(rows) -> str:
    digest = hashlib.sha256()
    for row in rows:
        fields = (
            row["timestamp_unix"], row["market_ticker"], row["action"], row["side"],
            row["price"], row["quantity"], row["fee"], row["cash_after"], row["realized_pnl_this_event"],
        )
        digest.update("|".join(str(field) for field in fields).encode())
        digest.update(b"\n")
    return digest.hexdigest()


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.variants = program_variants()

    def test_at_least_one_thousand_strategies_one_by_one(self):
        self.assertGreaterEqual(len(self.variants), 2000)
        per_batch = Counter(v.batch for v in self.variants)
        self.assertEqual(len(per_batch), 20)
        for batch, count in per_batch.items():
            self.assertEqual(count, 100, batch)
        ids = [v.strategy_id for v in self.variants]
        users = [v.username for v in self.variants]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(users), len(set(users)))
        for variant in self.variants:
            self.assertTrue(variant.hypothesis.strip())
            self.assertTrue(variant.topic.strip())
            json.dumps(variant.public())  # serializable for the site

    def test_every_variant_decides_under_a_synthetic_view(self):
        from types import SimpleNamespace
        from simcomp.engine import Book, DecisionView, Position
        markets = parity_markets()
        for variant in self.variants:
            strategy = variant.strategy
            seen = 0
            decisions = 0
            for item in markets:
                book = Book(cash=Decimal("10000"), peak=Decimal("10000"))
                pos = Position()
                view = SimpleNamespace(
                    ticker=item.ticker, title=item.title, open_time=item.open_time,
                    series_ticker=item.series_ticker, event_ticker=item.event_ticker,
                )
                for index, cand in enumerate(item.candles):
                    ctx = DecisionView(
                        as_of_ts=cand.end_period_ts, market=view, candle=cand,
                        prior=tuple(item.candles[max(0, index - PROGRAM_PRIOR_WINDOW):index]),
                        position=pos, cash=book.cash, ever_traded=False, candle_index=index,
                    )
                    decision = strategy.decide(ctx)
                    self.assertIsInstance(decision, Decision)
                    decisions += 1
                    for intent in decision.intents:
                        self.assertIn(intent.action, ("buy", "sell"))
                        self.assertIn(intent.side, ("yes", "no"))
                    seen += 1
            self.assertGreater(seen, 0, variant.strategy_id)
            self.assertGreater(decisions, 0)

    def test_prior_window_contract(self):
        # The registry builder already raises if a lookback exceeds the window.
        self.assertEqual(PROGRAM_PRIOR_WINDOW, 24)


class ParityTests(unittest.TestCase):
    def test_program_engine_matches_primary_engine_line_by_line(self):
        markets = parity_markets()
        config = SimConfig(
            competition_id="parity-primary",
            title="parity",
            kind="forward_simulation",
            data_tier="live_kalshi",
        )
        primary = run_competition(markets, config, clone_strategies())
        notes = {}
        program = run_universe(markets, "nobel_forward", primary_variants(), None, notes)
        rich_by_pid: dict[str, list] = {}
        for trade in primary["trades"]:
            rich_by_pid.setdefault(trade["participant_id"], []).append(trade)
        for username, _sid, _display in PARTICIPANTS:
            self.assertIn(username, program["ledger_hashes"])
            self.assertEqual(
                canonical_hash(rich_by_pid.get(username, [])),
                program["ledger_hashes"][username],
                username,
            )
        board = {row["p"]: row for row in program["leaderboard"]}
        for row in primary["leaderboard"]:
            mine = board[row["participant_id"]]
            self.assertEqual(mine["eq"], row["ending_equity"], row["participant_id"])
            self.assertEqual(mine["cash"], row["cash"])
            self.assertEqual(mine["mtm"], row["liquidation_value"])
            self.assertEqual(mine["real"], row["realized_pnl"])
            self.assertEqual(mine["unreal"], row["unrealized_pnl"])
            self.assertEqual(mine["fees"], row["fees"])
            self.assertEqual(mine["n"], row["trade_count"])
            self.assertEqual(mine["w"], row["wins"])
            self.assertEqual(mine["l"], row["losses"])
            self.assertEqual(mine["trips"], row["settled_round_trips"])
            self.assertEqual(mine["dd"], row["max_drawdown"])
            self.assertEqual(mine["wr"], row["win_rate_settled"])

    def test_program_run_is_deterministic(self):
        markets = parity_markets()
        variants = primary_variants()
        first = run_universe(markets, "nobel_forward", variants, None)
        second = run_universe(markets, "nobel_forward", primary_variants(), None)
        self.assertEqual(first["combined_ledger_sha256"], second["combined_ledger_sha256"])
        self.assertEqual(first["leaderboard"], second["leaderboard"])


class RealSnapshotParityTests(unittest.TestCase):
    """Parity on the real stored snapshot, not only constructed candles."""

    def test_real_universe_ledgers_match_between_engines(self):
        jsonl = ROOT / "data" / "kalshi" / "markets.jsonl"
        if not jsonl.exists():
            self.skipTest("no stored Kalshi snapshot in this checkout")
        from simcomp.build import load_records, record_to_market, _bucket, _configs
        records = load_records(ROOT)
        markets = [record_to_market(record) for record in records]
        grouped = {"nobel_forward": [], "nobel_settled": [], "panel_settled": []}
        for market in markets:
            bucket = _bucket(market)
            if bucket:
                grouped[bucket].append(market)
        universe_for_comp = {
            "nobel-forward-primary": "nobel_forward",
            "nobel-settled-primary": "nobel_settled",
            "panel-settled-primary": "panel_settled",
        }
        for config, universe, _overrides in _configs():
            if universe not in ("nobel_forward", "nobel_settled", "panel_settled"):
                continue
            if not config.competition_id.endswith("-primary"):
                continue
            primary = run_competition(grouped[universe], config, clone_strategies())
            # Equal views: the huge prior window makes the program engine expose
            # the same history the primary engine passes. Then all ledgers and
            # boards must match exactly.
            program = run_universe(
                grouped[universe], universe_for_comp[config.competition_id],
                primary_variants(), None, prior_window=1_000_000,
            )
            rich_by_pid: dict[str, list] = {}
            for trade in primary["trades"]:
                rich_by_pid.setdefault(trade["participant_id"], []).append(trade)
            compared = 0
            for username, _sid, _display in PARTICIPANTS:
                self.assertEqual(
                    canonical_hash(rich_by_pid.get(username, [])),
                    program["ledger_hashes"][username],
                    f"{universe_for_comp[config.competition_id]} {username}",
                )
                compared += 1
            board = {row["p"]: row for row in program["leaderboard"]}
            for row in primary["leaderboard"]:
                mine = board[row["participant_id"]]
                self.assertEqual(mine["eq"], row["ending_equity"], f"{config.competition_id} {row['participant_id']}")
                self.assertEqual(mine["real"], row["realized_pnl"])
                self.assertEqual(mine["unreal"], row["unrealized_pnl"])
                self.assertEqual(mine["fees"], row["fees"])
            print(f"real parity {config.competition_id}: {compared} ledgers and 11 boards match")

    def test_program_registry_lookbacks_all_bounded(self):
        """Every registered variant's declared lookback fits the 24-candle
        program window, so windowing cannot change any decision. The
        first-parity failure of volume_momentum (unbounded median) is why this
        matters: only window-safe families may be registered."""
        from simcomp.research_program import _class_lookback
        variants = program_variants()
        worst = 0
        for variant in variants:
            if hasattr(variant.strategy, "required_prior"):  # phase 2 declares what it reads
                needed = variant.strategy.required_prior()
                self.assertLessEqual(needed, PROGRAM_PRIOR_WINDOW, variant.strategy_id)
                worst = max(worst, needed)
                continue
            lookback = _class_lookback(type(variant.strategy), variant.strategy.parameters)
            self.assertLessEqual(lookback + 1, PROGRAM_PRIOR_WINDOW, variant.strategy_id)
            worst = max(worst, lookback + 1)
        print("registry bounded:", len(variants), "variants, deepest lookback", worst, "of window", PROGRAM_PRIOR_WINDOW)


class ProgramLookaheadTests(unittest.TestCase):
    def test_no_trade_at_or_after_settlement(self):
        import csv
        import gzip
        import tempfile
        from simcomp.program import _CsvSinks
        item = market(
            result="yes", status="finalized", settlement_ts=4500,
            candles=[
                candle(2000, "0.40", "0.44", "0.42", "12"),
                candle(4000, "0.66", "0.68", "0.67", "30"),
                candle(8000, "0.95", "0.97", "0.96", "50"),  # post-settlement: must be invisible
            ],
        )
        with tempfile.TemporaryDirectory() as tmp:
            sink = _CsvSinks(Path(tmp), "nobel_settled")
            result = run_universe([item], "nobel_settled", primary_variants(), sink)
            files = sink.close()
            self.assertEqual(result["markets_used"], 1)
            saw_rows = False
            for path in files.values():
                with gzip.open(path, "rt", encoding="utf-8") as handle:
                    for row in csv.DictReader(handle):
                        saw_rows = True
                        if row["action"] == "settlement":
                            self.assertEqual(int(row["ts_unix"]), 4500)
                            self.assertEqual(row["fill_src"], "MR")
                        else:
                            self.assertLess(int(row["ts_unix"]), 4500)
            self.assertTrue(saw_rows)

    def test_entry_timing_ordinal(self):
        import csv
        import gzip
        import tempfile
        from simcomp.program import _CsvSinks
        item = market(candles=[
            candle(1000 + i * 1000, "0.70", "0.72", "0.71", "40") for i in range(6)
        ])
        variant = Variant(
            batch="b", topic="t", family="f", strategy_id="sid", username="sim-timing",
            display_name="d", hypothesis="h",
            strategy=EntryTimingBand(),
        )
        variant.strategy.parameters = {"entry_index": 3, "min_ask": "0.60", "max_ask": "0.92", "max_spread": "0.08"}
        with tempfile.TemporaryDirectory() as tmp:
            sink = _CsvSinks(Path(tmp), "nobel_forward")
            result = run_universe([item], "nobel_forward", [variant], sink)
            files = sink.close()
            rows = []
            for path in files.values():
                with gzip.open(path, "rt", encoding="utf-8") as handle:
                    rows.extend(csv.DictReader(handle))
            buys = [row for row in rows if row["action"] == "buy"]
            self.assertEqual(len(buys), 1)
            self.assertEqual(int(buys[0]["ts_unix"]), 3000)  # third decision candle
            self.assertEqual(result["markets_used"], 1)


if __name__ == "__main__":
    unittest.main()
