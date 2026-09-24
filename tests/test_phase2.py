"""Phase-2 tests: registry and research cards, decision-time channels, lookahead
guards, reset determinism, placebos, Decimal math, and verdict rules. No network."""

from __future__ import annotations

import sys
import unittest
from collections import Counter
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_program import candle, market, parity_markets  # noqa: E402

from simcomp.analysis import MIN_EVENTS, MIN_TRADED_VARIANTS, _verdict, analyse  # noqa: E402
from simcomp.context import EventIndex, SettledPool, build_settled_records, parse_schedule  # noqa: E402
from simcomp.engine import decision_candles  # noqa: E402
from simcomp.program import run_universe  # noqa: E402
from simcomp.research_cards import CHANNELS, card_for  # noqa: E402
from simcomp.research_program import Variant, program_variants  # noqa: E402
from simcomp.research_sources import SOURCES  # noqa: E402
from simcomp.strategies import Decision, Strategy  # noqa: E402
from simcomp.strategies_phase2 import (  # noqa: E402
    EventStructure,
    ManagedExit,
    MatchedPlacebo,
    logit_model,
    prelec_inverse,
)


def channels_for(markets, strike="1970-01-01T02:30:00Z"):
    events = {"E1": {"event_ticker": "E1", "mutually_exclusive": True, "strike_date": strike, "category": "Test"}}
    records = build_settled_records(markets, decision_candles, {"KXTEST": "Test"})
    return {"events_by_ticker": events, "settled_pool": SettledPool(records), "categories": {"KXTEST": "Test"}}


def variant(strategy, username="sim-x", family="f"):
    return Variant(batch="b", topic="t", family=family, strategy_id=username, username=username,
                   display_name="d", hypothesis="h", strategy=strategy)


class Spy(Strategy):
    """Records every view's channels; never trades."""

    id = "spy"

    def __init__(self):
        super().__init__()
        self.seen = []

    def decide(self, ctx):
        self.seen.append(ctx)
        return Decision(note="spy")


class RegistryAndCards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.variants = program_variants()

    def test_twenty_batches_of_one_hundred(self):
        self.assertEqual(len(self.variants), 2000)
        per_batch = Counter(v.batch for v in self.variants)
        self.assertEqual(sorted(per_batch), [f"batch-{i:03d}" for i in range(1, 21)])
        self.assertTrue(all(count == 100 for count in per_batch.values()))

    def test_every_family_has_a_complete_card_with_verified_sources(self):
        for family in {v.family for v in self.variants}:
            card = card_for(family)
            for key in ("question", "mechanism", "sources", "channels", "predicts", "falsified_if", "kind"):
                self.assertTrue(card.get(key), f"{family} {key}")
            for source in card["sources"]:
                self.assertIn(source, SOURCES, family)
            for channel in card["channels"]:
                self.assertIn(channel, CHANNELS, family)

    def test_sources_have_citation_url_and_claim(self):
        for key, src in SOURCES.items():
            self.assertTrue(src.get("citation"), key)
            self.assertTrue(src.get("claim_used"), key)
            if not key.startswith("none-"):
                self.assertTrue(str(src.get("url", "")).startswith("https://"), key)

    def test_placebos_sit_in_the_same_batch_as_their_family(self):
        families_by_batch = {}
        for v in self.variants:
            families_by_batch.setdefault(v.batch, set()).add(v.family)
        for v in self.variants:
            if v.family.startswith("placebo_"):
                parent = v.family[len("placebo_"):]
                self.assertIn(parent, families_by_batch[v.batch], v.strategy_id)
                self.assertEqual(v.strategy.parameters["placebo_of"], parent)

    def test_all_variants_run_with_channels_on_synthetic_markets(self):
        markets = parity_markets()
        settled = [m for m in markets if m.settled_result]
        result = run_universe(settled, "nobel_settled", self.variants, None, None, **channels_for(markets))
        self.assertEqual(len(result["leaderboard"]), 2000)
        forward = [m for m in markets if not m.settled_result]
        result = run_universe(forward, "nobel_forward", self.variants, None, None, **channels_for(markets))
        self.assertEqual(len(result["leaderboard"]), 2000)


class ChannelLookahead(unittest.TestCase):
    def test_event_view_shows_only_candles_at_or_before_t_in_any_visit_order(self):
        a = market("A", candles=[candle(1000, "0.40", "0.44"), candle(3000, "0.50", "0.54")])
        b = market("B", candles=[candle(1000, "0.30", "0.34"), candle(2000, "0.20", "0.24"), candle(3000, "0.10", "0.14")])
        index = EventIndex([(a, a.candles), (b, b.candles)], {})
        view = index.view("E1", 2000)
        by = {q.ticker: q for q in view.quotes}
        self.assertEqual(by["A"].end_ts, 1000)  # A's 3000 candle is in the future
        self.assertEqual(by["B"].end_ts, 2000)  # B's candle closing at T is public at T
        spy = Spy()
        run_universe([b, a], "nobel_forward", [variant(spy)], None)
        for ctx in spy.seen:
            self.assertTrue(all(q.end_ts <= ctx.as_of_ts for q in ctx.event.quotes))
            if ctx.as_of_ts == 3000:
                self.assertEqual({q.ticker: q.end_ts for q in ctx.event.quotes}, {"A": 3000, "B": 3000})

    def test_settled_pool_is_strictly_before_t(self):
        early = market("S1", result="yes", status="finalized", settlement_ts=2000,
                       candles=[candle(1000, "0.60", "0.62")])
        tie = market("S2", result="no", status="finalized", settlement_ts=3000,
                     candles=[candle(1000, "0.30", "0.32")])
        pool = SettledPool(build_settled_records([early, tie], decision_candles))
        self.assertEqual([r.ticker for r in pool.view(3000).records], ["S1"])  # S2 settles at T: excluded
        self.assertEqual([r.ticker for r in pool.view(3001).records], ["S1", "S2"])
        self.assertEqual(pool.view(2000).records, ())
        live = market("L", candles=[candle(2000, "0.5", "0.52"), candle(3000, "0.5", "0.52"), candle(4000, "0.5", "0.52")])
        spy = Spy()
        run_universe([live], "nobel_forward", [variant(spy)], None, settled_pool=pool)
        for ctx in spy.seen:
            self.assertTrue(all(r.settlement_ts < ctx.as_of_ts for r in ctx.settled.records))

    def test_schedule_refuses_close_time_style_stamps(self):
        self.assertEqual(parse_schedule({"strike_date": "2026-01-06T04:59:00Z"})[0], 1767675540)
        self.assertIsNone(parse_schedule({"strike_date": "2025-10-17T00:29:40.415884Z"})[0])
        self.assertIsNone(parse_schedule({"strike_date": ""})[0])
        self.assertIsNone(parse_schedule(None)[0])

    def test_decision_view_never_carries_result_or_close_time(self):
        spy = Spy()
        m = market("R", result="yes", status="finalized", settlement_ts=9000, candles=[candle(2000, "0.5", "0.52")])
        run_universe([m], "nobel_settled", [variant(spy)], None, **channels_for([m]))
        ctx = spy.seen[0]
        for leaked in ("result", "close_time", "settlement_ts", "expected_expiration_time"):
            self.assertFalse(hasattr(ctx.market, leaked), leaked)


class ResetAndPlacebo(unittest.TestCase):
    def _stateful(self):
        change = EventStructure()
        change.parameters = {"mode": "leader_change", "gap": "0", "min_mid": "0.10", "min_n": 2}
        trail = ManagedExit()
        trail.parameters = {"exit": "trailing", "x": "0.03", "entry": "fav", "fav_lo": "0.60", "fav_hi": "0.95", "max_spread": "0.10"}
        return [variant(change, "sim-change"), variant(trail, "sim-trail")]

    def test_reusing_instances_reproduces_ledgers(self):
        swap_a = market("SWAP-A", candles=[candle(1000, "0.58", "0.62"), candle(2000, "0.38", "0.42"), candle(3000, "0.36", "0.40")])
        swap_b = market("SWAP-B", candles=[candle(1000, "0.38", "0.42"), candle(2000, "0.58", "0.62"), candle(3000, "0.62", "0.66")])
        markets = parity_markets() + [swap_a, swap_b]
        stateful = self._stateful()
        first = run_universe(markets, "nobel_forward", stateful, None, None, **channels_for(markets))
        second = run_universe(markets, "nobel_forward", stateful, None, None, **channels_for(markets))
        fresh = run_universe(markets, "nobel_forward", self._stateful(), None, None, **channels_for(markets))
        self.assertEqual(first["ledger_hashes"], second["ledger_hashes"])
        self.assertEqual(first["ledger_hashes"], fresh["ledger_hashes"])
        fills = {row["p"]: row["n"] for row in first["leaderboard"]}
        self.assertGreater(fills["sim-change"], 0)  # the leader change actually fired
        self.assertGreater(fills["sim-trail"], 0)

    def test_placebo_trades_same_markets_and_times_as_its_family(self):
        rising = market("P1", candles=[candle(1000 + i * 1000, "0.60", "0.62") for i in range(3)])
        rising.candles.append(candle(4000, "0.70", "0.72"))
        other = market("P2", candles=[candle(1000 + i * 1000, "0.20", "0.22") for i in range(4)])
        params = {"mode": "leader", "gap": "0.05", "min_mid": "0.30", "min_n": 2, "max_spread": "0.08"}
        inner = EventStructure()
        inner.parameters = dict(params)
        inner_twin = EventStructure()
        inner_twin.parameters = dict(params)
        placebo = MatchedPlacebo(inner=inner_twin, seed="abc")
        placebo.parameters = {**params, "placebo_of": "event_leader", "placebo_seed": "abc"}
        out = run_universe([rising, other], "nobel_forward", [variant(inner, "sim-in"), variant(placebo, "sim-pl")], None, None,
                           **channels_for([rising, other]))
        board = {row["p"]: row for row in out["leaderboard"]}
        self.assertEqual(board["sim-in"]["mkts"], board["sim-pl"]["mkts"])
        self.assertEqual(board["sim-in"]["t0"], board["sim-pl"]["t0"])


class DecimalMath(unittest.TestCase):
    def test_logit_identity_and_direction(self):
        self.assertEqual(logit_model(Decimal("0.5"), Decimal("1.4")), Decimal("0.5"))
        self.assertLess(logit_model(Decimal("0.10"), Decimal("1.4")), Decimal("0.10"))
        self.assertGreater(logit_model(Decimal("0.90"), Decimal("1.4")), Decimal("0.90"))
        self.assertEqual(logit_model(Decimal("0.37"), Decimal("1.25")), logit_model(Decimal("0.37"), Decimal("1.25")))

    def test_prelec_fixed_point_at_one_over_e(self):
        one_over_e = Decimal(-1).exp()
        self.assertAlmostEqual(float(prelec_inverse(one_over_e, Decimal("0.65"))), float(one_over_e), places=12)
        self.assertLess(prelec_inverse(Decimal("0.05"), Decimal("0.65")), Decimal("0.05"))


class VerdictRules(unittest.TestCase):
    def test_inaction_is_not_evidence_and_low_power_is_flagged(self):
        markets = parity_markets()
        settled = [m for m in markets if m.settled_result]
        variants = [v for v in program_variants([1, 12])]
        out = run_universe(settled, "nobel_settled", variants, None, None, **channels_for(markets))
        research = analyse({"nobel_settled": out}, variants)
        for fam in research["families"]:
            s = fam["universes"]["nobel_settled"]
            if s["entered"] == 0:
                self.assertIn(s["verdict"], ("NOT TESTED", "REFERENCE"))
                self.assertIsNone(s["median_eq"])
            elif fam["card"]["kind"] == "signal":
                # One settled synthetic event (E1): below MIN_EVENTS, so no family can be "supported".
                self.assertEqual(s["verdict"], "INCONCLUSIVE-LOW-POWER", fam["family"])
        self.assertGreater(MIN_EVENTS, 2)

    def test_verdict_boundaries_on_hand_built_stats(self):
        null = {"median": 9500.0, "p95": 10100.0}
        card = {"kind": "signal"}

        def stats(**kw):
            base = {"entered": 10, "settled_events_touched": 5, "yes_events_touched": 3, "median_eq": 10300.0,
                    "placebo_median_eq": None, "loo_worst_median_eq": 10050.0, "loo_worst_event": "E"}
            base.update(kw)
            return base

        self.assertEqual(_verdict("nobel_settled", card, stats(), null)[0], "SUPPORTED-ON-SNAPSHOT")
        # Two traded variants cannot make a family median, however good they look.
        self.assertEqual(_verdict("nobel_settled", card, stats(entered=MIN_TRADED_VARIANTS - 1), null)[0],
                         "INCONCLUSIVE-LOW-POWER")
        self.assertEqual(_verdict("nobel_settled", card, stats(yes_events_touched=0), null)[0], "INCONCLUSIVE-LOW-POWER")
        self.assertEqual(_verdict("nobel_settled", card, stats(median_eq=9500.0), null)[0], "NOT SUPPORTED")
        # Beats the null p95 but not its own placebo -> not supported.
        self.assertEqual(_verdict("nobel_settled", card, stats(placebo_median_eq=10400.0), null)[0], "INCONCLUSIVE")
        # Result hinges on one event -> not supported.
        self.assertEqual(_verdict("nobel_settled", card, stats(loo_worst_median_eq=9400.0), null)[0], "INCONCLUSIVE")
        # Above p95 but below starting cash (a losing null) -> not supported.
        self.assertEqual(_verdict("nobel_settled", card, stats(median_eq=9990.0), {"median": 9000.0, "p95": 9900.0})[0],
                         "INCONCLUSIVE")
        self.assertEqual(_verdict("nobel_forward", card, stats(), null)[0], "UNSETTLED")
        self.assertEqual(_verdict("nobel_settled", {"kind": "placebo"}, stats(), null)[0], "REFERENCE")


if __name__ == "__main__":
    unittest.main()
