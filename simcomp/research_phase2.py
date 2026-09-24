"""Phase-2 registry: batches 011-020, 100 simulated participants each.

Each row is (family, parameters, factory, hypothesis, display). ``factory`` is
called with the parameters and returns a fresh Strategy. Families are described
by research cards in simcomp/research_cards.py (question, mechanism, sources,
channels, predicted sign, falsification rule); the registry refuses a family
without a card.

Matched placebos: for a chosen representative grid point of an entry family,
``placebo_<family>`` runs the identical rule and replaces only the side with a
seeded coin. Same markets, same timestamps, same size rule. The family minus its
placebo is the value of the side choice, separated from trigger timing.
"""

from __future__ import annotations

import hashlib
from itertools import product

from simcomp.strategies_phase2 import (
    Ablation,
    ActivitySignal,
    CalibrationPrior,
    Composite,
    EventStructure,
    GatedEntry,
    LadderEntry,
    ManagedExit,
    MatchedPlacebo,
    PoolLearner,
    PreCloseExit,
    SizedEntry,
    SplitEntry,
    TrendSignal,
)

PHASE2_TOPICS = {
    "batch-011": (
        "Event structure",
        "Test: do the other contracts of the same Kalshi event carry information about this one? "
        "Normalized event probabilities, over/under-round sums, leader and rank rules, field "
        "baskets, concentration, leader changes, rotation. Reads ctx.event only at or before T.",
    ),
    "batch-012": (
        "Literature calibration priors",
        "Test: fixed, predeclared calibration curves suggested by the favorite-longshot and "
        "probability-weighting literature (logit slope, Prelec inverse, longshot NO writing, "
        "high-favorite YES), with and without the fee hurdle. Nothing is fitted.",
    ),
    "batch-013": (
        "Walk-forward learning",
        "Test: calibration tables, base rates, and a fitted logit slope estimated only from "
        "markets whose official result settled strictly before the decision (ctx.settled).",
    ),
    "batch-014": (
        "Time, age, and schedule",
        "Test: does the same entry behave differently by market age, by hours to Kalshi's "
        "published strike_date, by UTC hour, or by weekday? Includes an exit-before-close rule.",
    ),
    "batch-015": (
        "Liquidity, volume, open interest",
        "Test: open-interest changes, volume spikes, dormant markets waking, liquidity gates, "
        "spread compression, stale quotes, and turnover as entry conditions.",
    ),
    "batch-016": (
        "Trend and reversal constructions",
        "Test: moving-average crosses, time-series momentum windows, big-move follow/fade, RSI, "
        "bands, runs, range position, dips and rallies. Single entry, hold to settlement.",
    ),
    "batch-017": (
        "Position sizing",
        "Test: holding entry fixed and varying only size: fractional Kelly, fixed contracts, "
        "edge-scaled, cash fraction, payout target, cash reserve, ladders, split entries.",
    ),
    "batch-018": (
        "Exits and holding period",
        "Test: holding entry fixed and varying only the exit: time and clock stops, trailing, "
        "breakeven, targets, model-edge exit, stop-and-reverse, volatility stop, partial and "
        "ladder takes, max loss, hold control, random-exit control.",
    ),
    "batch-019": (
        "Information and timing ablations",
        "Test: sensitivity to information: lagged signals, delayed entries, the reference-price "
        "source, decision frequency, spread tolerance, injected noise, coarse price grids, "
        "no-rule first-quote entries, truncated windows, trade-print gates.",
    ),
    "batch-020": (
        "Ensembles and a second null",
        "Test: votes across simple signals, regime switches, model+momentum agreement and "
        "conflict, composite event/learning rules, and a matched-rate random null that fires "
        "at controlled rates with fixed or random side.",
    ),
}


def _seed(tag: str, index: int) -> str:
    return hashlib.sha256(f"simcomp-p2-{tag}-{index:03d}".encode()).hexdigest()[:12]


def _cls(cls):
    def build(parameters):
        strategy = cls()
        strategy.parameters = dict(parameters)
        return strategy
    build.cls = cls
    return build


def _placebo(inner_cls, inner_params):
    def build(parameters):
        inner = inner_cls()
        inner.parameters = dict(inner_params)
        strategy = MatchedPlacebo(inner=inner, seed=parameters["placebo_seed"])
        strategy.parameters = dict(parameters)
        return strategy
    build.cls = MatchedPlacebo
    return build


def _fmt(params: dict, skip=("mode",)) -> str:
    return " ".join(f"{k}={v}" for k, v in params.items() if k not in skip)


class _Rows:
    def __init__(self):
        self.rows = []

    def add(self, family, cls, params, display=None):
        self.rows.append((family, dict(params), _cls(cls), _fmt(params), display or f"{family.replace('_', ' ')} {_fmt(params)}"))

    def placebos(self, inner_family, inner_cls, inner_params, count, tag):
        for i in range(1, count + 1):
            seed = _seed(tag, i)
            params = dict(inner_params)
            params.update({"placebo_of": inner_family, "placebo_seed": seed})
            self.rows.append((
                f"placebo_{inner_family}", params, _placebo(inner_cls, inner_params),
                f"matched placebo of {inner_family} ({_fmt(inner_params)}), seed {seed}",
                f"placebo {inner_family.replace('_', ' ')} seed {seed[:6]}",
            ))


FAV = {"fav_lo": "0.65", "fav_hi": "0.92"}


def _batch_011(r: _Rows):
    for (lo, hi), edge, sides in product((("0.80", "1.20"), ("0.90", "1.10")), ("0.02", "0.04", "0.06", "0.08"), ("yes", "both")):
        r.add("event_normalized", EventStructure, {"mode": "normalized", "mass_lo": lo, "mass_hi": hi, "edge": edge, "sides": sides, "min_n": 3, "max_spread": "0.10"})
    for margin, leg in product(("0.02", "0.05", "0.10", "0.20"), ("0.10", "0.25", "0.50")):
        r.add("event_overround_no", EventStructure, {"mode": "overround_no", "margin": margin, "max_leg_ask": leg, "min_n": 3})
    for margin, mass_lo in product(("0.00", "0.02", "0.05"), ("0.85", "0.95")):
        r.add("event_underround_yes", EventStructure, {"mode": "underround_yes", "margin": margin, "mass_lo": mass_lo, "min_n": 2})
    for gap, min_mid, min_n in product(("0.00", "0.05", "0.10", "0.20"), ("0.30", "0.50"), (3, 5)):
        r.add("event_leader", EventStructure, {"mode": "leader", "gap": gap, "min_mid": min_mid, "min_n": min_n, "max_spread": "0.08"})
    for k, cap in product((2, 3, 4), ("0.20", "0.35", "0.50")):
        r.add("event_rank_k", EventStructure, {"mode": "rank_k", "k": k, "cap": cap, "min_n": 3, "max_spread": "0.08"})
    for k, cap in product((3, 5, 8), ("0.05", "0.10", "0.20")):
        r.add("event_field_no", EventStructure, {"mode": "field_no", "k": k, "cap": cap, "min_n": 3})
    for direction, h in (("high", "0.25"), ("high", "0.40"), ("high", "0.55"), ("high", "0.70"),
                         ("low", "0.10"), ("low", "0.15"), ("low", "0.25")):
        r.add("event_concentration", EventStructure, {"mode": "concentration", "dir": direction, "h": h, "min_n": 3, "max_spread": "0.08"})
    for gap, min_mid in product(("0.00", "0.05", "0.10"), ("0.20", "0.40")):
        r.add("event_leader_change", EventStructure, {"mode": "leader_change", "gap": gap, "min_mid": min_mid, "min_n": 3, "max_spread": "0.10"})
    for m, x in product(("0.03", "0.05", "0.10"), ("0.02", "0.05", "0.10")):
        r.add("event_rotation", EventStructure, {"mode": "rotation", "m": m, "x": x, "min_n": 3, "max_spread": "0.10"})
    r.placebos("event_leader", EventStructure, {"mode": "leader", "gap": "0.05", "min_mid": "0.30", "min_n": 3, "max_spread": "0.08"}, 5, "leader")
    r.placebos("event_field_no", EventStructure, {"mode": "field_no", "k": 5, "cap": "0.10", "min_n": 3}, 5, "fieldno")


def _batch_012(r: _Rows):
    for k, edge, sides in product(("1.15", "1.25", "1.40", "1.60"), ("0.01", "0.02", "0.04", "0.06"), ("both", "yes")):
        r.add("logit_scale", CalibrationPrior, {"mode": "logit", "k": k, "edge": edge, "sides": sides, "max_spread": "0.08"})
    for k, edge, sides in product(("0.80", "0.90"), ("0.02", "0.04"), ("both", "yes")):
        r.add("logit_reverse", CalibrationPrior, {"mode": "logit", "k": k, "edge": edge, "sides": sides, "max_spread": "0.08"})
    for cap, spread in product(("0.03", "0.05", "0.08", "0.10", "0.15", "0.20"), ("0.03", "0.06", "1.00")):
        r.add("longshot_no_writer", CalibrationPrior, {"mode": "longshot_no", "cap": cap, "max_spread": spread})
    for lo, spread in product(("0.85", "0.90", "0.93", "0.95"), ("0.02", "0.04", "1.00")):
        r.add("high_favorite_yes", CalibrationPrior, {"mode": "high_favorite", "lo": lo, "max_spread": spread})
    for alpha, edge in product(("0.65", "0.75", "0.85"), ("0.02", "0.04")):
        r.add("prelec_inverse", CalibrationPrior, {"mode": "prelec", "alpha": alpha, "edge": edge, "sides": "both", "max_spread": "0.08"})
    for k, edge, sides in product(("1.25", "1.40", "1.60"), ("0.00", "0.01", "0.02"), ("both", "yes")):
        r.add("fee_aware_logit", CalibrationPrior, {"mode": "fee_aware", "k": k, "edge": edge, "sides": sides, "max_spread": "0.08"})
    r.placebos("logit_scale", CalibrationPrior, {"mode": "logit", "k": "1.40", "edge": "0.02", "sides": "both", "max_spread": "0.08"}, 3, "logit")
    r.placebos("longshot_no_writer", CalibrationPrior, {"mode": "longshot_no", "cap": "0.10", "max_spread": "0.06"}, 3, "lsno")


def _batch_013(r: _Rows):
    base = {"max_spread": "0.10", "prior": "2"}
    for width, scope, min_n, edge in product(("0.10", "0.20"), ("series", "category", "all"), (3, 8), ("0.03", "0.06")):
        r.add("learned_bucket_calibration", PoolLearner, {"mode": "bucket", "width": width, "scope": scope, "min_n": min_n, "edge": edge, "sides": "both", **base})
    for scope, edge in product(("series", "category", "all"), ("0.03", "0.06")):
        r.add("learned_bucket_calibration", PoolLearner, {"mode": "bucket", "width": "0.05", "scope": scope, "min_n": 3, "edge": edge, "sides": "both", **base})
    for scope, min_n, edge in product(("series", "category", "all"), (5, 15), ("0.05", "0.10")):
        r.add("learned_base_rate", PoolLearner, {"mode": "base_rate", "scope": scope, "min_n": min_n, "edge": edge, "sides": "both", "max_spread": "0.10"})
    for scope in ("series", "category", "all"):
        r.add("learned_base_rate", PoolLearner, {"mode": "base_rate", "scope": scope, "min_n": 5, "edge": "0.05", "sides": "no", "max_spread": "0.10"})
    for scope in ("series", "category", "all"):
        r.add("learned_base_rate", PoolLearner, {"mode": "base_rate", "scope": scope, "min_n": 5, "edge": "0.15", "sides": "both", "max_spread": "0.10"})
    for scope, edge, min_pairs in product(("series", "category", "all"), ("0.02", "0.04"), (30, 100)):
        r.add("learned_logit_slope", PoolLearner, {"mode": "fitted_slope", "scope": scope, "edge": edge, "min_pairs": min_pairs, "sides": "both", "max_spread": "0.10"})
    for scope, edge in product(("series", "category", "all"), ("0.02", "0.04")):
        r.add("learned_logit_slope", PoolLearner, {"mode": "fitted_slope", "scope": scope, "edge": edge, "min_pairs": 30, "sides": "no", "max_spread": "0.10"})
    for scope, half in product(("series", "all"), (5, 20)):
        r.add("learned_recency_rate", PoolLearner, {"mode": "recency_rate", "scope": scope, "half_life": half, "min_n": 5, "edge": "0.05", "sides": "both", "max_spread": "0.10"})
    for edge in ("0.03", "0.08"):
        r.add("learned_recency_rate", PoolLearner, {"mode": "recency_rate", "scope": "series", "half_life": 10, "min_n": 5, "edge": edge, "sides": "both", "max_spread": "0.10"})
    for scope, split in (("series", 7), ("series", 30), ("all", 7), ("all", 30), ("category", 7), ("category", 30)):
        r.add("learned_age_calibration", PoolLearner, {"mode": "age_bucket", "width": "0.20", "age_split_d": split, "scope": scope, "min_n": 3, "edge": "0.04", "sides": "both", **base})
    for w, edge in product(("0.10", "0.20", "0.30", "0.50"), ("0.02", "0.05")):
        r.add("uniform_field_prior", PoolLearner, {"mode": "uniform_prior", "w": w, "edge": edge, "sides": "both", "max_spread": "0.10"})
    r.placebos("learned_bucket_calibration", PoolLearner, {"mode": "bucket", "width": "0.10", "scope": "all", "min_n": 3, "edge": "0.03", "sides": "both", **base}, 7, "bucket")
    r.placebos("learned_base_rate", PoolLearner, {"mode": "base_rate", "scope": "series", "min_n": 5, "edge": "0.05", "sides": "both", "max_spread": "0.10"}, 7, "baserate")


def _batch_014(r: _Rows):
    common = {**FAV, "ls_cap": "0.15", "mom": "0.03", "max_spread": "0.08"}
    for hours, entry in product(("24", "72", "168", "336", "720"), ("fav", "longshot_no", "longshot_yes")):
        if entry == "longshot_yes" and hours == "336":
            continue
        r.add("time_age_min", GatedEntry, {"gate": "age_ge", "hours": hours, "entry": entry, **common})
    for hours, entry in product(("6", "24", "72"), ("fav", "longshot_no", "momentum", "longshot_yes")):
        r.add("time_age_max", GatedEntry, {"gate": "age_le", "hours": hours, "entry": entry, **common})
    for hours, entry in product(("2", "6", "24", "72", "168"), ("fav", "longshot_no", "momentum", "longshot_yes")):
        r.add("time_horizon_near", GatedEntry, {"gate": "horizon_le", "hours": hours, "entry": entry, **common})
    for hours, entry in product(("24", "168", "720"), ("fav", "longshot_no", "momentum", "longshot_yes")):
        r.add("time_horizon_far", GatedEntry, {"gate": "horizon_ge", "hours": hours, "entry": entry, **common})
    for (lo, hi), entry in product(((0, 6), (6, 12), (12, 18), (18, 24)), ("fav", "longshot_no", "momentum", "longshot_yes")):
        r.add("time_utc_hour", GatedEntry, {"gate": "utc_hour", "h_lo": lo, "h_hi": hi, "entry": entry, **common})
    for days, entry in product(("weekday", "weekend"), ("fav", "longshot_no", "momentum", "longshot_yes")):
        r.add("time_weekday", GatedEntry, {"gate": "weekday", "days": days, "entry": entry, **common})
    for hours, lo in product(("1", "6", "24", "72", "168"), ("0.55", "0.65")):
        r.add("time_pre_close_exit", PreCloseExit, {"hours": hours, "fav_lo": lo, "fav_hi": "0.92", "max_spread": "0.08"})
    r.placebos("time_horizon_near", GatedEntry, {"gate": "horizon_le", "hours": "24", "entry": "fav", **common}, 4, "horizon")
    r.placebos("time_age_min", GatedEntry, {"gate": "age_ge", "hours": "72", "entry": "longshot_no", **common}, 4, "age")


def _batch_015(r: _Rows):
    for w, g, m in product((1, 3, 6), ("0.05", "0.20"), ("0.01", "0.03")):
        r.add("oi_growth_follow", ActivitySignal, {"mode": "oi_follow", "w": w, "g": g, "m": m, "max_spread": "0.10"})
    for g in ("0.05", "0.20"):
        r.add("oi_growth_follow", ActivitySignal, {"mode": "oi_follow", "w": 12, "g": g, "m": "0.03", "max_spread": "0.10"})
    for w, g, m in product((3, 6), ("0.05", "0.20"), ("0.01", "0.03")):
        r.add("oi_decline_fade", ActivitySignal, {"mode": "oi_fade", "w": w, "g": g, "m": m, "max_spread": "0.10"})
    for mode, w, k, m in product(("spike_follow", "spike_fade"), (6, 12), ("2", "4"), ("0.01", "0.03")):
        r.add(f"volume_{mode}", ActivitySignal, {"mode": mode, "w": w, "k": k, "m": m, "max_spread": "0.10"})
    for mode, m in product(("spike_follow", "spike_fade"), ("0.01", "0.03")):
        r.add(f"volume_{mode}", ActivitySignal, {"mode": mode, "w": 6, "k": "8", "m": m, "max_spread": "0.10"})
    for n, m in product((2, 4, 8, 12), ("0", "0.02")):
        r.add("dormant_wakeup", ActivitySignal, {"mode": "dormant", "n": n, "m": m, "max_spread": "0.12"})
    for v, entry in product(("100", "1000", "10000"), ("fav", "longshot_no")):
        r.add("liquidity_gate", ActivitySignal, {"mode": "liquid", "v": v, "oi": "0", "entry": entry, **FAV, "ls_cap": "0.15", "max_spread": "0.08"})
    for entry in ("fav", "longshot_no"):
        r.add("liquidity_gate", ActivitySignal, {"mode": "liquid", "v": "1000", "oi": "1000", "entry": entry, **FAV, "ls_cap": "0.15", "max_spread": "0.08"})
    for v, entry in product(("0", "50", "500"), ("fav", "longshot_no")):
        r.add("illiquidity_gate", ActivitySignal, {"mode": "illiquid", "v": v, "entry": entry, **FAV, "ls_cap": "0.15", "max_spread": "0.12"})
    for w, x in product((3, 6, 12), ("0.01", "0.03")):
        r.add("spread_compression", ActivitySignal, {"mode": "spread_compression", "w": w, "x": x, "max_spread": "0.10"})
    for n, m in product((2, 4, 6), ("0.02", "0.05")):
        r.add("stale_quote_drift", ActivitySignal, {"mode": "stale_quote", "n": n, "m": m, "max_spread": "0.10"})
    for ratio, m in product(("0.1", "0.5", "1.0", "2.0"), ("0.02", "0.05")):
        r.add("turnover_fade", ActivitySignal, {"mode": "turnover_fade", "r": ratio, "m": m, "max_spread": "0.10"})
    r.placebos("oi_growth_follow", ActivitySignal, {"mode": "oi_follow", "w": 3, "g": "0.20", "m": "0.03", "max_spread": "0.10"}, 4, "oi")
    r.placebos("volume_spike_follow", ActivitySignal, {"mode": "spike_follow", "w": 6, "k": "4", "m": "0.03", "max_spread": "0.10"}, 4, "spike")
    r.placebos("liquidity_gate", ActivitySignal, {"mode": "liquid", "v": "1000", "oi": "0", "entry": "fav", **FAV, "ls_cap": "0.15", "max_spread": "0.08"}, 4, "liquid")
    r.placebos("dormant_wakeup", ActivitySignal, {"mode": "dormant", "n": 4, "m": "0", "max_spread": "0.12"}, 4, "dormant")


def _batch_016(r: _Rows):
    s = {"max_spread": "0.10"}
    for (short, long_), gap in product(((2, 5), (3, 8), (5, 13), (3, 12)), ("0", "0.01", "0.03")):
        r.add("ma_crossover", TrendSignal, {"mode": "ma_cross", "short": short, "long": long_, "gap": gap, **s})
    for w, m in product((3, 6, 12, 20), ("0.02", "0.05", "0.10", "0.15")):
        r.add("tsmom_window", TrendSignal, {"mode": "tsmom", "w": w, "m": m, **s})
    for m, direction in product(("0.05", "0.10", "0.15", "0.20", "0.30"), ("follow", "fade")):
        r.add(f"big_move_{direction}", TrendSignal, {"mode": "big_move", "m": m, "dir": direction, **s})
    for w, hi in product((6, 12, 20), ("70", "80", "90")):
        r.add("rsi_fade", TrendSignal, {"mode": "rsi", "w": w, "hi": hi, **s})
    for w, z in product((6, 12, 20), ("1.5", "2", "2.5")):
        r.add("bollinger_revert", TrendSignal, {"mode": "bollinger", "w": w, "z": z, **s})
    r.add("bollinger_revert", TrendSignal, {"mode": "bollinger", "w": 3, "z": "1.5", **s})
    for mode, n in product(("run_follow", "run_fade"), (2, 3, 4, 5)):
        r.add(mode, TrendSignal, {"mode": mode, "n": n, **s})
    for w, direction in product((3, 6, 12, 20), ("revert", "breakout")):
        r.add(f"range_{direction}", TrendSignal, {"mode": "range_pos", "w": w, "dir": direction, **s})
    for mode, w, d in product(("dip", "rally_fade"), (6, 12), ("0.05", "0.10", "0.20")):
        r.add("buy_the_dip" if mode == "dip" else "fade_the_rally", TrendSignal, {"mode": mode, "w": w, "d": d, **s})
    r.placebos("tsmom_window", TrendSignal, {"mode": "tsmom", "w": 6, "m": "0.05", **s}, 5, "tsmom")
    r.placebos("big_move_fade", TrendSignal, {"mode": "big_move", "m": "0.10", "dir": "fade", **s}, 5, "bigmove")
    r.placebos("bollinger_revert", TrendSignal, {"mode": "bollinger", "w": 12, "z": "2", **s}, 5, "boll")


def _batch_017(r: _Rows):
    base = {**FAV, "ls_cap": "0.15", "edge": "0.02", "max_spread": "0.08"}
    for frac, k in product(("0.05", "0.10", "0.25", "0.50", "1.00"), ("1.25", "1.40", "1.60")):
        r.add("kelly_fraction", SizedEntry, {"entry": "logit", "sizing": "kelly", "frac": frac, "k": k, **base})
    r.add("kelly_fraction", SizedEntry, {"entry": "logit", "sizing": "kelly", "frac": "2.00", "k": "1.40", **base})
    for qty, entry in product((1, 5, 10, 25, 50, 100, 200, 500), ("fav", "longshot_no")):
        r.add("fixed_contracts", SizedEntry, {"entry": entry, "sizing": "fixed", "qty": qty, **base})
    for scale, k in product(("10", "25", "50", "100"), ("1.25", "1.60")):
        r.add("edge_scaled_size", SizedEntry, {"entry": "logit", "sizing": "edge_scaled", "scale": scale, "k": k, **base})
    for f, entry in product(("0.001", "0.0025", "0.005", "0.01"), ("fav", "logit")):
        r.add("cash_fraction_size", SizedEntry, {"entry": entry, "sizing": "cash_fraction", "f": f, "k": "1.25", **base})
    for x, entry in product(("10", "50", "100", "250"), ("fav", "longshot_no")):
        r.add("payout_target_size", SizedEntry, {"entry": entry, "sizing": "payout", "x": x, **base})
    for reserve, entry in product(("0.25", "0.50", "0.75", "0.90"), ("fav", "logit")):
        r.add("cash_reserve_gate", SizedEntry, {"entry": entry, "sizing": "reserve", "r": reserve, "k": "1.25", **base})
    for direction, step, adds in product(("down", "up"), ("0.03", "0.05", "0.10", "0.20"), (1, 2)):
        r.add("ladder_average_down" if direction == "down" else "ladder_pyramid", LadderEntry, {"dir": direction, "step": step, "adds": adds, **FAV, "max_spread": "0.08"})
    for n, s in product((2, 3, 4, 6), (1, 3)):
        r.add("split_entry", SplitEntry, {"n": n, "s": s, **FAV, "max_spread": "0.08"})
    r.placebos("kelly_fraction", SizedEntry, {"entry": "logit", "sizing": "kelly", "frac": "0.25", "k": "1.40", **base}, 6, "kelly")
    r.placebos("fixed_contracts", SizedEntry, {"entry": "fav", "sizing": "fixed", "qty": 25, **base}, 6, "fixed")


def _batch_018(r: _Rows):
    fav = {"entry": "fav", **FAV, "max_spread": "0.08"}
    logit = {"entry": "logit", "k": "1.25", "edge": "0.02", "max_spread": "0.08"}
    entries = (("fav", fav), ("logit", logit))
    for n, (_name, entry) in product((1, 2, 3, 5, 8, 13, 21), entries):
        r.add("exit_time_stop", ManagedExit, {"exit": "time", "n": n, **entry})
    for hours in ("6", "24", "72", "168", "336"):
        r.add("exit_clock_stop", ManagedExit, {"exit": "clock", "hours": hours, **fav})
    for hours in ("24", "72"):
        r.add("exit_clock_stop", ManagedExit, {"exit": "clock", "hours": hours, **logit})
    for x, (_name, entry) in product(("0.03", "0.05", "0.10", "0.20"), entries):
        r.add("exit_trailing_stop", ManagedExit, {"exit": "trailing", "x": x, **entry})
    for g, (_name, entry) in product(("0.03", "0.05", "0.10"), entries):
        r.add("exit_breakeven_stop", ManagedExit, {"exit": "breakeven", "g": g, **entry})
    for level, (_name, entry) in product(("0.85", "0.90", "0.95", "0.97", "0.99"), entries):
        r.add("exit_price_target", ManagedExit, {"exit": "target", "level": level, **entry})
    for thr, k in product(("0", "0.01", "0.02"), ("1.25", "1.60")):
        r.add("exit_edge_gone", ManagedExit, {"exit": "edge_gone", "thr": thr, **{**logit, "k": k}})
    for x, (_name, entry) in product(("0.05", "0.10", "0.20"), entries):
        r.add("exit_stop_and_reverse", ManagedExit, {"exit": "stop_reverse", "x": x, **entry})
    for w, z in product((6, 12), ("1", "2", "3")):
        r.add("exit_volatility_stop", ManagedExit, {"exit": "vol_stop", "w": w, "z": z, **fav})
    for g, (_name, entry) in product(("0.03", "0.05", "0.10"), entries):
        r.add("exit_partial_take", ManagedExit, {"exit": "partial", "g": g, **entry})
    for g, (_name, entry) in product(("0.02", "0.04"), entries):
        r.add("exit_ladder_take", ManagedExit, {"exit": "ladder_take", "g": g, **entry})
    for dollars, (_name, entry) in product(("10", "25", "50"), entries):
        r.add("exit_max_loss", ManagedExit, {"exit": "max_loss", "dollars": dollars, **entry})
    for lo in ("0.55", "0.65", "0.75"):
        r.add("exit_hold_control", ManagedExit, {"exit": "hold", **{**fav, "fav_lo": lo}})
    for k in ("1.25", "1.60"):
        r.add("exit_hold_control", ManagedExit, {"exit": "hold", **{**logit, "k": k}})
    for p_exit, i in product(("0.05", "0.20"), range(1, 6)):
        r.add("exit_random_control", ManagedExit, {"exit": "random", "p_exit": p_exit, "seed": _seed("randexit", i), **fav})
    for p_exit, i in product(("0.05", "0.20"), range(6, 9)):
        r.add("exit_random_control", ManagedExit, {"exit": "random", "p_exit": p_exit, "seed": _seed("randexit", i), **logit})


def _batch_019(r: _Rows):
    base = {**FAV, "ls_cap": "0.15", "mom": "0.03"}
    for d, m in product((0, 1, 2, 3, 5, 8), ("0.03", "0.05")):
        r.add("ablation_lagged_signal", Ablation, {"mode": "lagged_momentum", "d": d, "m": m, "max_spread": "0.10"})
    for d, entry in product((0, 1, 2, 4, 8), ("fav", "longshot_no")):
        r.add("ablation_delayed_entry", Ablation, {"mode": "delayed", "d": d, "entry": entry, **base, "max_spread": "0.10"})
    for source, m in product(("trade", "mid", "bid", "ask"), ("0.02", "0.05")):
        r.add("ablation_price_source", Ablation, {"mode": "source", "source": source, "m": m, "max_spread": "0.10"})
    for k, entry in product((1, 2, 4, 8), ("fav", "momentum", "longshot_no")):
        r.add("ablation_decision_frequency", Ablation, {"mode": "frequency", "k": k, "entry": entry, **base, "max_spread": "0.08"})
    for entry, spread in product(("fav", "longshot_no"), ("0.02", "0.05", "0.10", "0.20", "1.00")):
        r.add("ablation_spread_tolerance", Ablation, {"mode": "spread_cap", "entry": entry, **base, "max_spread": spread})
    for sigma, entry in product(("0", "0.01", "0.03", "0.05", "0.10", "0.20"), ("fav", "momentum")):
        r.add("ablation_noisy_price", Ablation, {"mode": "noisy", "sigma": sigma, "entry": entry, "seed": _seed("noise", 1), "max_spread": "0.10"})
    for grid, entry in product(("0.01", "0.05", "0.10", "0.25"), ("fav", "momentum")):
        r.add("ablation_coarse_grid", Ablation, {"mode": "grid", "grid": grid, "entry": entry, "max_spread": "0.10"})
    for side, spread in product(("yes", "no"), ("0.05", "0.10", "1.00")):
        r.add("ablation_first_quote", Ablation, {"mode": "first_quote", "side": side, "max_spread": spread})
    for L, dev in product((2, 4, 8, 16), ("0.03", "0.06")):
        r.add("ablation_window_truncation", Ablation, {"mode": "window_trunc", "L": L, "dev": dev, "max_spread": "0.10"})
    for prints, entry in product(("require", "absent"), ("fav", "longshot_no", "momentum")):
        r.add("ablation_trade_print_gate", Ablation, {"mode": "trade_gate", "prints": prints, "entry": entry, **base, "max_spread": "0.10"})
    r.placebos("ablation_delayed_entry", Ablation, {"mode": "delayed", "d": 2, "entry": "fav", **base, "max_spread": "0.10"}, 4, "delay")
    r.placebos("ablation_decision_frequency", Ablation, {"mode": "frequency", "k": 2, "entry": "momentum", **base, "max_spread": "0.08"}, 4, "freq")


def _batch_020(r: _Rows):
    s = {"max_spread": "0.10"}
    for k, sides in product((1, 2, 3, 4), ("yes", "both")):
        r.add("ensemble_vote", Composite, {"mode": "vote", "k": k, "sides": sides, **s})
    for k, m in product((2, 3), ("0.05", "0.10")):
        r.add("ensemble_crowd_fade", Composite, {"mode": "crowd_fade", "k": k, "m": m, **s})
    for w, vol, m in product((6, 12), ("0.02", "0.04"), ("0.03", "0.06")):
        r.add("regime_switch", Composite, {"mode": "regime", "w": w, "s": vol, "m": m, **s})
    for k, m in product(("1.25", "1.60"), ("0.01", "0.03")):
        r.add("logit_momentum_agree", Composite, {"mode": "logit_mom", "k": k, "edge": "0.02", "m": m, **s})
    for policy, k in product(("skip_conflict", "only_conflict"), ("1.25", "1.60")):
        r.add(f"logit_{policy}", Composite, {"mode": "conflict", "policy": policy, "k": k, "edge": "0.02", "m": "0.03", **s})
    for gap, g in product(("0.05", "0.10"), ("0.05", "0.20")):
        r.add("event_leader_oi", Composite, {"mode": "leader_oi", "gap": gap, "g": g, "w": 3, **s})
    for k in (1, 2, 3):
        r.add("consensus_favorite", Composite, {"mode": "consensus_fav", "k": k, **FAV, **s})
    for vol_cap, gap in product(("0.01", "0.03"), ("0", "0.05", "0.10")):
        r.add("calm_event_favorite", Composite, {"mode": "fav_calm_leader", "vol_cap": vol_cap, "gap": gap, **FAV, **s})
    for mom, v in product(("0.03", "0.05"), ("100", "1000")):
        r.add("momentum_liquidity", Composite, {"mode": "mom_liquidity", "mom": mom, "v": v, "w": 24, **s})
    for i in range(1, 11):
        r.add("rule_mixture_control", Composite, {"mode": "mixture", "seed": _seed("mixture", i), **FAV, "ls_cap": "0.15", "mom": "0.03", **s})
    for per_mille, side, i in product((10, 30, 60), ("coin", "yes", "no"), (1, 2)):
        r.add("null_matched_rate", Composite, {"mode": "null_rate", "per_mille": per_mille, "side": side, "seed": _seed(f"nullrate{per_mille}{side}", i), **s})
    for per_mille, i in product((10, 30, 60), (3, 4, 5)):
        r.add("null_matched_rate", Composite, {"mode": "null_rate", "per_mille": per_mille, "side": "coin", "seed": _seed(f"nullrate{per_mille}coin", i), **s})
    for scope, edge in product(("series", "all"), ("0.03", "0.06")):
        r.add("learned_plus_structure", Composite, {"mode": "learned_structure", "scope": scope, "edge": edge, **s})
    for hours, scope in product(("24", "168"), ("series", "all")):
        r.add("horizon_learned", Composite, {"mode": "horizon_learned", "hours": hours, "scope": scope, "edge": "0.04", **s})
    r.placebos("ensemble_vote", Composite, {"mode": "vote", "k": 2, "sides": "both", **s}, 5, "vote")
    r.placebos("logit_momentum_agree", Composite, {"mode": "logit_mom", "k": "1.25", "edge": "0.02", "m": "0.01", **s}, 5, "logitmom")


BUILDERS = {
    "batch-011": _batch_011,
    "batch-012": _batch_012,
    "batch-013": _batch_013,
    "batch-014": _batch_014,
    "batch-015": _batch_015,
    "batch-016": _batch_016,
    "batch-017": _batch_017,
    "batch-018": _batch_018,
    "batch-019": _batch_019,
    "batch-020": _batch_020,
}


def phase2_rows(batch: str) -> list:
    rows = _Rows()
    BUILDERS[batch](rows)
    return rows.rows
