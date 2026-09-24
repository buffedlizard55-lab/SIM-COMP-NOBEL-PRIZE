"""Engine tests use constructed candles. They do not call Kalshi."""

from __future__ import annotations

import unittest
from decimal import Decimal
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from simcomp.engine import SimConfig, attach_later_results, run_competition  # noqa: E402
from simcomp.kalshi_parse import Candle, Market  # noqa: E402
from simcomp.money import taker_fee  # noqa: E402
from simcomp.strategies import HoldCash, LongshotHold, Momentum, clone_strategies  # noqa: E402


def candle(ts, bid, ask, trade=None, volume="10"):
    return Candle(
        end_period_ts=ts,
        yes_bid_close=Decimal(bid) if bid is not None else None,
        yes_ask_close=Decimal(ask) if ask is not None else None,
        trade_close=Decimal(trade) if trade is not None else None,
        volume=Decimal(volume),
        open_interest=Decimal("1"),
    )


def market(ticker="M1", result="", status="active", settlement_ts=None, candles=None, universe="nobel"):
    item = Market(
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
    return item


class FeeTests(unittest.TestCase):
    def test_schedule_range_matches_published_band(self):
        # Official fee schedule page, 2026-09-24: $0.07–$1.75 per 100 contracts, multiplier 1.
        at_half = taker_fee(1, 100, Decimal("0.50"))
        at_cent = taker_fee(1, 100, Decimal("0.01"))
        self.assertEqual(at_half, Decimal("1.75"))
        self.assertEqual(at_cent, Decimal("0.07"))

    def test_zero_price_is_not_a_fill_price(self):
        self.assertEqual(taker_fee(1, 10, Decimal("0")), Decimal("0"))


class LookaheadTests(unittest.TestCase):
    def test_post_settlement_candle_is_not_tradable(self):
        candles = [
            candle(2000, "0.40", "0.42", "0.41"),
            candle(3000, "0.70", "0.72", "0.71"),  # would look like a favorite, but it is after settlement
        ]
        item = market(result="yes", status="finalized", settlement_ts=2500, candles=candles)
        config = SimConfig(
            competition_id="t-lookahead",
            title="t",
            kind="historical_backtest",
            data_tier="historical_kalshi",
        )
        result = run_competition([item], config, clone_strategies())
        favorite_trades = [
            row for row in result["trades"]
            if row["strategy_id"] == "favorite_hold" and row["action"] == "buy"
        ]
        self.assertEqual(favorite_trades, [])
        for row in result["trades"]:
            if row["action"] != "settlement":
                self.assertLess(row["timestamp_unix"], 2500)
                self.assertFalse(row["outcome_known_at_decision"])

    def test_decision_view_has_no_result_attribute(self):
        seen = {}

        class Probe(HoldCash):
            id = "hold_cash"

            def decide(self, ctx):
                seen["has_result"] = hasattr(ctx.market, "result")
                seen["prior"] = len(ctx.prior)
                seen["as_of"] = ctx.as_of_ts
                return super().decide(ctx)

        strategies = clone_strategies()
        strategies[0] = Probe()
        item = market(candles=[candle(2000, "0.40", "0.42", "0.41"), candle(3000, "0.41", "0.43", "0.42")])
        config = SimConfig("t-view", "t", "forward_simulation", "live_kalshi")
        run_competition([item], config, strategies)
        self.assertFalse(seen["has_result"])
        self.assertEqual(seen["as_of"], 3000)
        self.assertEqual(seen["prior"], 1)

    def test_missing_settlement_timestamp_blocks_trades(self):
        item = market(
            result="yes",
            status="finalized",
            settlement_ts=None,
            candles=[candle(2000, "0.10", "0.12", "0.11")],
        )
        config = SimConfig("t-missing", "t", "historical_backtest", "historical_kalshi")
        result = run_competition([item], config, clone_strategies())
        self.assertEqual(result["trades"], [])
        self.assertTrue(any(flag["code"] == "settled_without_timestamp" for flag in result["flags"]))


class AccountingTests(unittest.TestCase):
    def test_longshot_settlement_identity(self):
        candles = [candle(2000, "0.10", "0.12", "0.11", "20")]
        item = market(result="yes", status="finalized", settlement_ts=5000, candles=candles, universe="nobel")
        config = SimConfig("t-acct", "t", "historical_backtest", "historical_kalshi")
        strategies = clone_strategies()
        result = attach_later_results(run_competition([item], config, strategies), [item])
        longshot = [row for row in result["trades"] if row["participant_id"] == "sim-cleo-longshot"]
        self.assertEqual(len(longshot), 2)
        buy, settle = longshot
        self.assertEqual(buy["action"], "buy")
        self.assertEqual(buy["side"], "yes")
        self.assertEqual(buy["price"], "0.1200")
        self.assertFalse(buy["later_result_used_in_decision"])
        self.assertEqual(buy["later_official_result"], "yes")
        qty = buy["quantity"]
        fee = Decimal(buy["fee"])
        self.assertEqual(fee, taker_fee(1, qty, Decimal("0.12")))
        cost = Decimal("0.12") * qty + fee
        self.assertEqual(Decimal(buy["cash_after"]), Decimal("10000") - cost)
        self.assertEqual(settle["action"], "settlement")
        self.assertEqual(Decimal(settle["cash_after"]), Decimal("10000") - cost + qty)
        row = next(item for item in result["leaderboard"] if item["participant_id"] == "sim-cleo-longshot")
        self.assertEqual(Decimal(row["ending_equity"]), Decimal(settle["cash_after"]))
        self.assertEqual(Decimal(row["realized_pnl"]), Decimal(row["ending_equity"]) - Decimal("10000"))
        hold = next(item for item in result["leaderboard"] if item["participant_id"] == "sim-ada-hold")
        self.assertEqual(hold["ending_equity"], "10000.0000")
        self.assertEqual(hold["trade_count"], 0)

    def test_no_fill_when_ask_missing(self):
        item = market(candles=[candle(2000, "0.10", None, None)])
        config = SimConfig("t-empty", "t", "forward_simulation", "live_kalshi")
        result = run_competition([item], config, [LongshotHold()])
        # Longshot is not in PARTICIPANTS mapping unless we pass strategies that match PARTICIPANTS.
        # The engine only runs PARTICIPANTS whose strategy id is in the provided list.
        self.assertEqual(result["trades"], [])

    def test_momentum_does_not_use_high_as_fill(self):
        candles = [
            candle(2000, "0.40", "0.42", "0.41"),
            candle(3000, "0.44", "0.46", "0.45"),
        ]
        candles[1].yes_ask_low = Decimal("0.20")  # a better price inside the bar; must not be the fill
        item = market(candles=candles)
        config = SimConfig("t-high", "t", "forward_simulation", "live_kalshi")
        result = run_competition([item], config, clone_strategies())
        buys = [
            row for row in result["trades"]
            if row["participant_id"] == "sim-dmitri-momentum" and row["action"] == "buy"
        ]
        self.assertTrue(buys)
        self.assertEqual(buys[0]["price"], "0.4600")
        self.assertEqual(buys[0]["fill_price_source"], "yes_ask.close")

    def test_same_start_and_replay(self):
        candles = [
            candle(2000, "0.40", "0.42", "0.41"),
            candle(3000, "0.46", "0.48", "0.47"),
            candle(4000, "0.44", "0.47", "0.45"),
        ]
        item = market(result="no", status="finalized", settlement_ts=8000, candles=candles)
        config = SimConfig("t-replay", "t", "historical_backtest", "historical_kalshi")
        first = run_competition([item], config, clone_strategies())
        second = run_competition([item], config, clone_strategies())
        self.assertEqual(first["trades"], second["trades"])
        starts = {row["starting_cash"] for row in first["leaderboard"]}
        self.assertEqual(starts, {"10000.0000"})
        self.assertEqual(len(first["leaderboard"]), 11)

    def test_zero_bid_is_not_a_sell_price(self):
        candles = [candle(2000, "0.10", "0.12", "0.11"), candle(3000, "0", "0.90", "0.11")]
        item = market(candles=candles)
        config = SimConfig("t-zero", "t", "forward_simulation", "live_kalshi")
        result = run_competition([item], config, clone_strategies())
        sells = [row for row in result["trades"] if row["action"] == "sell" and row["price"] == "0.0000"]
        self.assertEqual(sells, [])


class StrategySeparationTests(unittest.TestCase):
    def test_only_matching_strategy_trades(self):
        candles = [candle(2000, "0.10", "0.12", "0.11")]
        item = market(candles=candles)
        config = SimConfig("t-sep", "t", "forward_simulation", "live_kalshi")
        result = run_competition([item], config, clone_strategies())
        buyers = {row["strategy_id"] for row in result["trades"] if row["action"] == "buy"}
        self.assertIn("longshot_hold", buyers)
        self.assertNotIn("favorite_hold", buyers)
        self.assertNotIn("hold_cash", buyers)
        self.assertTrue(all(row["simulated"] is True and row["real_order"] is False for row in result["trades"]))


class IntervalTests(unittest.TestCase):
    def test_market_opened_today_uses_hourly(self):
        from simcomp.collect import choose_interval
        raw = {"open_time": "2026-09-24T14:00:00Z", "close_time": "2026-10-14T03:59:00Z"}
        self.assertEqual(choose_interval(raw, 1790270972), 60)

    def test_short_settled_market_uses_hourly(self):
        from simcomp.collect import choose_interval
        raw = {
            "open_time": "2025-10-10T18:00:00Z",
            "settlement_ts": "2025-10-17T01:33:10Z",
            "close_time": "2025-10-17T00:33:07Z",
        }
        self.assertEqual(choose_interval(raw, 1790270972), 60)


class NobelCatalogTests(unittest.TestCase):
    def test_catalog_counts_and_no_invented_nominees(self):
        import json
        catalog_path = ROOT / "data" / "nobel" / "catalog.json"
        self.assertTrue(catalog_path.exists())
        catalog = json.loads(catalog_path.read_text())
        counts = catalog["meta"]["counts"]
        self.assertEqual(counts["prizeRecords"], 682)
        self.assertEqual(counts["awardedPrizeRecords"], 633)
        self.assertEqual(counts["unawardedPrizeRecords"], 49)
        self.assertEqual(counts["laureateEntities"], 1018)
        self.assertEqual(counts["laureateSlots"], 1026)
        self.assertEqual(len(catalog["prizes"]), 682)
        self.assertEqual(len(catalog["laureates"]), 1018)
        years = {prize["year"] for prize in catalog["prizes"]}
        self.assertNotIn(2026, years)
        self.assertNotIn("2026", years)
        sealed = [p for p in catalog["prizes"] if p["nomination"]["status"] == "sealed_or_not_published"]
        self.assertTrue(sealed)
        for prize in sealed:
            self.assertEqual(prize["nomination"]["nominees"], [])
        economics = [p for p in catalog["prizes"] if p["category"] == "economics"]
        self.assertTrue(economics)
        self.assertTrue(all(p["inAlfredNobelsWill"] is False for p in economics))
        physics_2025 = next(p for p in catalog["prizes"] if p["key"] == "physics-2025")
        names = [row["displayName"] for row in physics_2025["laureates"]]
        self.assertEqual(names, ["John Clarke", "Michel H. Devoret", "John M. Martinis"])
        self.assertIn("macroscopic quantum mechanical tunnelling", physics_2025["laureates"][0]["motivation"])
        self.assertEqual(physics_2025["links"]["apiPrize"], "https://api.nobelprize.org/2/nobelPrize/phy/2025")


if __name__ == "__main__":
    unittest.main()
