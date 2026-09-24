"""Strategy research program: 1000+ parameterized variants in 10 batches of 100.

Each batch is one research topic. Each variant is one testable hypothesis with
predeclared parameters. Nothing here looks past the decision candle: every rule
below reads only ctx.candle, ctx.prior (the bounded window the engine exposes),
and the participant's own simulated cash/position.

Batch plan (fixed before any run):

  batch-001  Null models. Random valid entries, different seeds. The baseline
             every other batch is compared against. A family that cannot beat
             this batch's null band is not a finding.
  batch-002  Favorite band. Buy-and-hold YES where the ask sits in a band.
  batch-003  Longshot band. Buy-and-hold YES at low asks.
  batch-004  Momentum. Follow close-to-close moves, threshold grid.
  batch-005  Contrarian. Same signal, opposite side.
  batch-006  Mean reversion. Entry below the prior mean, exit back at it.
  batch-007  Exits and stops. Take-profit and stop-loss grids on a favorite.
  batch-008  Volume and gates. Volume-confirmed moves and calm/sanity gates.
  batch-009  Breakouts and entry timing. New-high entries and ordinal timing.
  batch-010  Spread tolerance. How much spread an entry band may sit through.

The registry is enumerated one strategy at a time. Tests assert the batch
sizes, id uniqueness, parameter serializability, and that every variant
returns a Decision under a synthetic decision view.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from itertools import product

from simcomp.strategies import (
    Contrarian,
    Decision,
    DiversifiedSlice,
    FavoriteExit,
    FavoriteHold,
    Intent,
    LongshotHold,
    MeanRevert,
    Momentum,
    SeededNull,
    Strategy,
    TightValue,
    _mid,
    _reference_price,
    _spread_ok,
)
from simcomp.money import usable_quote

# The engine only exposes this many immediately prior candles to a strategy.
# Every lookback in the registry must fit inside it. tests/test_program.py asserts.
PROGRAM_PRIOR_WINDOW = 24


class StopLossFavorite(Strategy):
    id = "stop_loss_favorite"
    name = "Favorite with a stop-loss"
    summary = (
        "Enter YES once in the favorite band, then sell everything if the closing "
        "bid falls at least the stop below the entry price. Isolates the stop "
        "from the take-profit leg."
    )
    parameters = {"min_ask": "0.65", "max_ask": "0.92", "max_spread": "0.08", "stop": "0.08"}

    def decide(self, ctx) -> Decision:
        candle = ctx.candle
        if ctx.position.qty and ctx.position.side == "yes":
            bid = candle.yes_bid_close
            if not usable_quote(bid):
                return Decision(note="hold: no usable bid")
            entry = ctx.position.avg_entry_price
            if bid <= entry - self._num("stop", ctx):
                return Decision(
                    intents=[Intent("sell", "yes", ctx.position.qty, reason=(
                        f"bid {bid} is the stop {self.parameters['stop']} or more below entry {entry}"
                    ))],
                    note="stop_loss_exit",
                )
            return Decision(note="hold: stop not reached")
        if ctx.ever_traded:
            return Decision(note="single entry used")
        ask = candle.yes_ask_close
        if not usable_quote(ask):
            return Decision(note="no usable yes ask")
        if not _spread_ok(candle, self._num("max_spread", ctx)):
            return Decision(note="spread outside cap or missing")
        if ask < self._num("min_ask", ctx) or ask > self._num("max_ask", ctx):
            return Decision(note="yes ask outside favorite band")
        return Decision(
            intents=[Intent("buy", "yes", reason=f"yes ask close {ask} inside favorite band")],
            note="enter_favorite_stop",
        )


class TakeProfitFavorite(Strategy):
    id = "take_profit_favorite"
    name = "Favorite with a take-profit"
    summary = (
        "Enter YES once in the favorite band, then sell everything if the closing "
        "bid rises at least the take above the entry price. Isolates the take-profit leg."
    )
    parameters = {"min_ask": "0.65", "max_ask": "0.92", "max_spread": "0.08", "take": "0.10"}

    def decide(self, ctx) -> Decision:
        candle = ctx.candle
        if ctx.position.qty and ctx.position.side == "yes":
            bid = candle.yes_bid_close
            if not usable_quote(bid):
                return Decision(note="hold: no usable bid")
            entry = ctx.position.avg_entry_price
            if bid >= entry + self._num("take", ctx):
                return Decision(
                    intents=[Intent("sell", "yes", ctx.position.qty, reason=(
                        f"bid {bid} is the take {self.parameters['take']} or more above entry {entry}"
                    ))],
                    note="take_profit_exit",
                )
            return Decision(note="hold: take not reached")
        if ctx.ever_traded:
            return Decision(note="single entry used")
        ask = candle.yes_ask_close
        if not usable_quote(ask):
            return Decision(note="no usable yes ask")
        if not _spread_ok(candle, self._num("max_spread", ctx)):
            return Decision(note="spread outside cap or missing")
        if ask < self._num("min_ask", ctx) or ask > self._num("max_ask", ctx):
            return Decision(note="yes ask outside favorite band")
        return Decision(
            intents=[Intent("buy", "yes", reason=f"yes ask close {ask} inside favorite band")],
            note="enter_favorite_take",
        )


class FavoriteExitReentry(FavoriteExit):
    id = "favorite_exit_reentry"
    name = "Favorite exit with re-entry"
    summary = (
        "Take-profit and stop rule of Favorite with an exit, but the participant may "
        "enter again after an exit. Tests whether repeated disciplined entries beat a single ride."
    )
    parameters = {"min_ask": "0.65", "max_ask": "0.92", "max_spread": "0.08", "take": "0.10", "stop": "0.08"}

    def decide(self, ctx) -> Decision:
        decision = super().decide(ctx)
        if decision.note == "already completed the single entry":
            # FavoriteExit blocks re-entry after its one completed entry; this variant re-enters.
            candle = ctx.candle
            ask = candle.yes_ask_close
            if not usable_quote(ask):
                return Decision(note="no usable yes ask")
            if not _spread_ok(candle, self._num("max_spread", ctx)):
                return Decision(note="spread outside cap or missing")
            if ask < self._num("min_ask", ctx) or ask > self._num("max_ask", ctx):
                return Decision(note="yes ask outside favorite band")
            return Decision(
                intents=[Intent("buy", "yes", reason=f"re-entry: yes ask close {ask} inside favorite band")],
                note="reenter_favorite_exit",
            )
        return decision


class VolumeMomentumWindow(Strategy):
    id = "volume_momentum_window"
    name = "Volume momentum, bounded window"
    summary = (
        "Follow the close-to-close move only when this candle's volume is above the "
        "median volume of the last `window` prior candles. The bounded window is the "
        "program form of the unbounded volume_momentum signal so 1000 participants "
        "stay affordable and the claimed lookback is explicit."
    )
    parameters = {"window": 5, "min_move": "0.02", "max_spread": "0.12"}

    def decide(self, ctx) -> Decision:
        window = self._int("window")
        if len(ctx.prior) < window:
            return Decision(note="not enough prior candles for the volume window")
        volumes = [c.volume for c in ctx.prior[-window:]]
        if ctx.candle.volume is None or any(v is None for v in volumes):
            return Decision(note="volume missing")
        ordered = sorted(volumes)
        median = ordered[(len(ordered) - 1) // 2]
        if ctx.candle.volume <= median:
            return Decision(note="volume not above prior window median")
        if not _spread_ok(ctx.candle, self._num("max_spread", ctx)):
            return Decision(note="spread outside cap or missing")
        current, current_src = _reference_price(ctx.candle)
        previous, previous_src = _reference_price(ctx.prior[-1])
        if current is None or previous is None:
            return Decision(note="no reference price")
        move = current - previous
        if abs(move) < self._num("min_move", ctx):
            return Decision(note="move below threshold")
        side = "yes" if move > 0 else "no"
        reason = (
            f"volume {ctx.candle.volume} > window median {median}; "
            f"{previous_src} {previous} -> {current_src} {current}"
        )
        if ctx.position.qty and ctx.position.side == side:
            return Decision(note="already hold the signaled side")
        intents = []
        if ctx.position.qty and ctx.position.side != side:
            intents.append(Intent("sell", ctx.position.side, ctx.position.qty, reason="exit; " + reason))
        intents.append(Intent("buy", side, reason="enter; " + reason))
        return Decision(intents=intents, note="volume_window_signal")


class VolatilityGate(Strategy):
    id = "volatility_gate"
    name = "Volatility-gated band entry"
    summary = (
        "Buy YES once when the ask is in the band and the standard deviation of the "
        "reference prices over the last `window` candles is at or below the cap. Tests "
        "whether calm books are a better entry than any book."
    )
    parameters = {"window": 5, "max_stdev": "0.02", "min_ask": "0.35", "max_ask": "0.60", "max_spread": "0.12"}

    def decide(self, ctx) -> Decision:
        if ctx.position.qty or ctx.ever_traded:
            return Decision(note="single entry used")
        window = self._int("window")
        if len(ctx.prior) < window:
            return Decision(note="not enough prior candles for the stdev window")
        refs = []
        for candle in ctx.prior[-window:]:
            price, _src = _reference_price(candle)
            if price is None:
                return Decision(note="a prior candle has no reference price")
            refs.append(price)
        mean = sum(refs) / len(refs)
        variance = sum((r - mean) * (r - mean) for r in refs) / len(refs)
        stdev = variance.sqrt()
        if stdev > self._num("max_stdev", ctx):
            return Decision(note="reference stdev above the calm cap")
        candle = ctx.candle
        ask = candle.yes_ask_close
        if not usable_quote(ask):
            return Decision(note="no usable yes ask")
        if not _spread_ok(candle, self._num("max_spread", ctx)):
            return Decision(note="spread outside cap or missing")
        if ask < self._num("min_ask", ctx) or ask > self._num("max_ask", ctx):
            return Decision(note="yes ask outside band")
        return Decision(
            intents=[Intent("buy", "yes", reason=(
                f"stdev {stdev} over {window} <= {self.parameters['max_stdev']}; yes ask {ask} in band"
            ))],
            note="enter_calm_band",
        )


class RelativeSpreadValue(Strategy):
    id = "relative_spread_value"
    name = "Relative-spread value"
    summary = (
        "Buy YES once when the closing spread is at most rel_spread times the ask and "
        "the ask is under the cap. A relative test of liquidity instead of an absolute cent cap."
    )
    parameters = {"rel_spread": "0.10", "min_ask": "0.05", "max_ask": "0.45"}

    def decide(self, ctx) -> Decision:
        if ctx.position.qty or ctx.ever_traded:
            return Decision(note="single entry used")
        candle = ctx.candle
        ask = candle.yes_ask_close
        bid = candle.yes_bid_close
        if not usable_quote(ask) or not usable_quote(bid):
            return Decision(note="book is not two-sided")
        if (ask - bid) > self._num("rel_spread", ctx) * ask:
            return Decision(note="relative spread above cap")
        if ask < self._num("min_ask", ctx) or ask > self._num("max_ask", ctx):
            return Decision(note="yes ask outside band")
        return Decision(
            intents=[Intent("buy", "yes", reason=(
                f"spread {ask - bid} <= {self.parameters['rel_spread']} * ask {ask}"
            ))],
            note="enter_relative_spread",
        )


class BreakoutHold(Strategy):
    id = "breakout_hold"
    name = "Breakout, hold"
    summary = (
        "Buy YES once when the reference price exceeds the maximum reference of the "
        "last `window` prior candles by at least min_break, and the ask is under the cap. "
        "Tests trend continuation against the null batch."
    )
    parameters = {"window": 4, "min_break": "0.03", "max_ask": "0.90", "max_spread": "0.12"}

    def decide(self, ctx) -> Decision:
        if ctx.position.qty or ctx.ever_traded:
            return Decision(note="single entry used")
        window = self._int("window")
        if len(ctx.prior) < window:
            return Decision(note="not enough prior candles for the breakout window")
        refs = []
        for candle in ctx.prior[-window:]:
            price, _src = _reference_price(candle)
            if price is None:
                return Decision(note="a prior candle has no reference price")
            refs.append(price)
        current, current_src = _reference_price(ctx.candle)
        if current is None:
            return Decision(note="no reference price")
        ceiling = max(refs)
        if current < ceiling + self._num("min_break", ctx):
            return Decision(note="no breakout over the prior window max")
        candle = ctx.candle
        ask = candle.yes_ask_close
        if not usable_quote(ask):
            return Decision(note="no usable yes ask")
        if not _spread_ok(candle, self._num("max_spread", ctx)):
            return Decision(note="spread outside cap or missing")
        if ask > self._num("max_ask", ctx):
            return Decision(note="yes ask above the breakout cap")
        return Decision(
            intents=[Intent("buy", "yes", reason=(
                f"reference {current_src} {current} breaks window max {ceiling} + {self.parameters['min_break']}"
            ))],
            note="enter_breakout",
        )


class EntryTimingBand(Strategy):
    id = "entry_timing_band"
    name = "Entry timing, band"
    summary = (
        "The favorite/slice band rule, but the entry is allowed only on or after the "
        "entry_index-th decision candle of the market. Earlier candles are observed, not traded. "
        "Isolates timing from band choice."
    )
    parameters = {"entry_index": 3, "min_ask": "0.65", "max_ask": "0.92", "max_spread": "0.08"}

    def decide(self, ctx) -> Decision:
        if ctx.position.qty or ctx.ever_traded:
            return Decision(note="single entry used")
        # 1-based ordinal of this decision candle. candle_index is set by the
        # engines; the prior-length fallback keeps synthetic unit tests simple.
        ordinal = ctx.candle_index + 1 if getattr(ctx, "candle_index", None) is not None else len(ctx.prior) + 1
        if ordinal < self._int("entry_index"):
            return Decision(note="before the entry candle ordinal")
        candle = ctx.candle
        ask = candle.yes_ask_close
        if not usable_quote(ask):
            return Decision(note="no usable yes ask")
        if not _spread_ok(candle, self._num("max_spread", ctx)):
            return Decision(note="spread outside cap or missing")
        if ask < self._num("min_ask", ctx) or ask > self._num("max_ask", ctx):
            return Decision(note="yes ask outside band")
        return Decision(
            intents=[Intent("buy", "yes", reason=(
                f"decision candle ordinal {ordinal} >= {self.parameters['entry_index']}; yes ask {ask} in band"
            ))],
            note="enter_timed_band",
        )


class TightValueRanged(Strategy):
    id = "tight_value_ranged"
    name = "Tight-spread value, ranged"
    summary = (
        "Tight-spread value with an explicit lower band, so the family can separate "
        "'cheap and tight' from 'any ask that is not yet a favorite'."
    )
    parameters = {"min_ask": "0.05", "max_ask": "0.40", "max_spread": "0.04"}

    def decide(self, ctx) -> Decision:
        if ctx.position.qty or ctx.ever_traded:
            return Decision(note="single entry used")
        candle = ctx.candle
        ask = candle.yes_ask_close
        if not usable_quote(ask):
            return Decision(note="no usable yes ask")
        if not _spread_ok(candle, self._num("max_spread", ctx)):
            return Decision(note="spread wider than the tight cap or missing")
        if ask < self._num("min_ask", ctx) or ask > self._num("max_ask", ctx):
            return Decision(note="ask outside the ranged band")
        return Decision(
            intents=[Intent("buy", "yes", reason=(
                f"spread {candle.spread} <= {self.parameters['max_spread']}; ask {ask} in "
                f"{self.parameters['min_ask']}–{self.parameters['max_ask']}"
            ))],
            note="enter_tight_value_ranged",
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


@dataclass
class Variant:
    batch: str
    topic: str
    family: str
    strategy_id: str
    username: str
    display_name: str
    hypothesis: str
    strategy: Strategy

    def public(self) -> dict:
        return {
            "batch": self.batch,
            "topic": self.topic,
            "family": self.family,
            "strategy_id": self.strategy_id,
            "username": self.username,
            "display_name": self.display_name,
            "hypothesis": self.hypothesis,
            "parameters": dict(self.strategy.parameters),
            "class": type(self.strategy).__name__,
            "simulated": True,
        }


TOPICS = {
    "batch-001": (
        "Null models",
        "Random but valid entries, seeds varied, rules fixed. Every other batch is read "
        "against this null band. A family whose median cannot clear the null band is not a finding.",
    ),
    "batch-002": (
        "Favorite band",
        "Test: does buying and holding YES in a declared favorite ask band beat the null, "
        "and how wide may the band and spread go before that stops being true?",
    ),
    "batch-003": (
        "Longshot band",
        "Test: the longshot-bias question on this snapshot. Buy-and-hold YES at low asks "
        "across a grid of band edges and spread caps.",
    ),
    "batch-004": (
        "Momentum",
        "Test: following close-to-close moves at several thresholds, spread caps, and "
        "prior-candle minimums. Is any point on the grid materially different from another?",
    ),
    "batch-005": (
        "Contrarian fade",
        "Test: the identical momentum signal, faded. The two batches together separate "
        "'move signals' from 'side choice' under identical data and size rules.",
    ),
    "batch-006": (
        "Mean reversion",
        "Test: entry when the reference price sits below the prior mean by a declared "
        "deviation, exit at that mean, across lookback and deviation grids.",
    ),
    "batch-007": (
        "Exits and stops",
        "Test: a favorite entry with a take-profit leg, a stop-loss leg, both legs, and "
        "re-entry. Reads exit rules separately from entry rules.",
    ),
    "batch-008": (
        "Volume and gates",
        "Test: price signals conditioned on activity (volume above a bounded window "
        "median), on calm (bounded reference stdev), and on relative spread.",
    ),
    "batch-009": (
        "Breakouts and entry timing",
        "Test: entries on new highs of the recent window, and the same band rule entered "
        "on different decision-candle ordinals.",
    ),
    "batch-010": (
        "Spread tolerance",
        "Test: how much spread each entry style may sit through before results stop "
        "differing from the null band. Wide-spread twins of the band families.",
    ),
}


def _slug(text: str) -> str:
    return text.replace("0.", "").replace(".", "")


def _family_params(family: str, params: dict) -> dict:
    row = {"family": family}
    row.update(params)
    return row


def _variants_for_batch(batch: str) -> list[tuple[str, dict, type, str, str]]:
    """(family, parameters, class, hypothesis template, display template), 100 per batch."""
    rows: list[tuple[str, dict, type, str, str]] = []
    if batch == "batch-001":
        fire_plan = [(i, 30) for i in range(1, 51)] + [(i, 10) for i in range(51, 76)] + [(i, 60) for i in range(76, 101)]
        for index, fire in fire_plan:
            seed = hashlib.sha256(f"simcomp-null-{index:03d}".encode()).hexdigest()[:12]
            rows.append((
                "null_model",
                {"seed": seed, "fire_per_mille": fire, "max_spread": "0.12"},
                SeededNull,
                f"Null draw: fires on about {fire / 10:g}% of candles with seed {seed}. "
                "Holds to settlement. Any family result must clear this band to be a finding.",
                f"Null seed {index:03d} (fire {fire}/1000)",
            ))
    elif batch == "batch-002":
        for min_ask, max_ask, spread in product(
            ("0.55", "0.60", "0.65", "0.70", "0.75"),
            ("0.80", "0.85", "0.90", "0.95"),
            ("0.04", "0.08", "0.12", "0.16", "0.20"),
        ):
            rows.append((
                "favorite_band",
                {"min_ask": min_ask, "max_ask": max_ask, "max_spread": spread},
                FavoriteHold,
                f"Buy-and-hold YES with ask in {min_ask}–{max_ask} and spread <= {spread}. "
                "Held to settlement; read against the null batch.",
                f"Favorite {min_ask}–{max_ask} s{spread[2:]}",
            ))
    elif batch == "batch-003":
        for min_ask, max_ask, spread in product(
            ("0.01", "0.02", "0.04", "0.06", "0.08"),
            ("0.10", "0.15", "0.20", "0.25", "0.30"),
            ("0.04", "0.08", "0.12", "0.20"),
        ):
            rows.append((
                "longshot_band",
                {"min_ask": min_ask, "max_ask": max_ask, "max_spread": spread},
                LongshotHold,
                f"Buy-and-hold YES with ask in {min_ask}–{max_ask} and spread <= {spread}. "
                "Tests the longshot-bias question on this snapshot.",
                f"Longshot {min_ask}–{max_ask} s{spread[2:]}",
            ))
    elif batch == "batch-004":
        for min_move, spread, min_prior in product(
            ("0.01", "0.02", "0.03", "0.04", "0.05"),
            ("0.06", "0.10", "0.14", "0.18"),
            (1, 2, 3, 5, 8),
        ):
            rows.append((
                "momentum",
                {"min_move": min_move, "max_spread": spread, "min_prior_candles": min_prior},
                Momentum,
                f"Follow close-to-close moves of at least {min_move} with spread <= {spread} "
                f"and at least {min_prior} prior candles.",
                f"Momentum m{min_move[2:]} s{spread[2:]} p{min_prior}",
            ))
    elif batch == "batch-005":
        for min_move, spread, min_prior in product(
            ("0.01", "0.02", "0.03", "0.04", "0.05"),
            ("0.06", "0.10", "0.14", "0.18"),
            (1, 2, 3, 5, 8),
        ):
            rows.append((
                "contrarian",
                {"min_move": min_move, "max_spread": spread, "min_prior_candles": min_prior},
                Contrarian,
                f"Fade close-to-close moves of at least {min_move} with spread <= {spread} "
                f"and at least {min_prior} prior candles.",
                f"Fade m{min_move[2:]} s{spread[2:]} p{min_prior}",
            ))
    elif batch == "batch-006":
        for lookback, deviation, spread in product(
            (2, 3, 4, 6, 8),
            ("0.02", "0.04", "0.06", "0.09", "0.12"),
            ("0.06", "0.10", "0.14", "0.18"),
        ):
            rows.append((
                "mean_reversion",
                {"deviation": deviation, "lookback": lookback, "max_spread": spread},
                MeanRevert,
                f"Enter at least {deviation} below the mean of the prior {lookback} references; "
                f"exit at that mean; spread <= {spread}.",
                f"Revert l{lookback} d{deviation[2:]} s{spread[2:]}",
            ))
    elif batch == "batch-007":
        for take, stop in product(("0.05", "0.10", "0.15", "0.20"), ("0.04", "0.08", "0.12", "0.16", "0.20")):
            rows.append((
                "favorite_exit",
                {"min_ask": "0.65", "max_ask": "0.92", "max_spread": "0.08", "take": take, "stop": stop},
                FavoriteExit,
                f"Favorite entry 0.65–0.92; take-profit {take}, stop {stop}. Single entry.",
                f"Exit t{take[2:]} s{stop[2:]}",
            ))
        for stop, min_ask in product(("0.03", "0.06", "0.09", "0.12", "0.15"), ("0.60", "0.65", "0.70", "0.75", "0.80")):
            rows.append((
                "stop_loss_favorite",
                {"min_ask": min_ask, "max_ask": "0.92", "max_spread": "0.08", "stop": stop},
                StopLossFavorite,
                f"Favorite entry {min_ask}–0.92 with a stop {stop} below entry; no take-profit leg.",
                f"Stop {stop[2:]} from {min_ask[2:]}",
            ))
        for take, min_ask in product(("0.04", "0.08", "0.12", "0.16", "0.20"), ("0.60", "0.65", "0.70", "0.75", "0.80")):
            rows.append((
                "take_profit_favorite",
                {"min_ask": min_ask, "max_ask": "0.92", "max_spread": "0.08", "take": take},
                TakeProfitFavorite,
                f"Favorite entry {min_ask}–0.92 with a take-profit {take} above entry; no stop leg.",
                f"Take {take[2:]} from {min_ask[2:]}",
            ))
        for take, stop, min_ask in product(("0.05", "0.10", "0.15"), ("0.05", "0.10"), ("0.60", "0.65", "0.70", "0.75", "0.80")):
            rows.append((
                "favorite_exit_reentry",
                {"min_ask": min_ask, "max_ask": "0.92", "max_spread": "0.08", "take": take, "stop": stop},
                FavoriteExitReentry,
                f"Favorite entry {min_ask}–0.92; take {take}, stop {stop}; re-entry allowed after an exit.",
                f"Reentry t{take[2:]} s{stop[2:]} from {min_ask[2:]}",
            ))
    elif batch == "batch-008":
        for window, min_move, spread in product((3, 5, 8, 13), ("0.01", "0.02", "0.03"), ("0.08", "0.12", "0.16", "0.20")):
            rows.append((
                "volume_momentum_window",
                {"window": window, "min_move": min_move, "max_spread": spread},
                VolumeMomentumWindow,
                f"Follow moves >= {min_move} only when volume is above the median of the prior "
                f"{window} candles; spread <= {spread}.",
                f"VolMom w{window} m{min_move[2:]} s{spread[2:]}",
            ))
        for window, max_stdev, band in product(
            (3, 5, 8),
            ("0.01", "0.02", "0.03"),
            (("0.65", "0.92"), ("0.35", "0.60"), ("0.04", "0.18")),
        ):
            rows.append((
                "volatility_gate",
                {"window": window, "max_stdev": max_stdev, "min_ask": band[0], "max_ask": band[1], "max_spread": "0.12"},
                VolatilityGate,
                f"Enter YES in {band[0]}–{band[1]} only when reference stdev over {window} candles is <= {max_stdev}.",
                f"Calm w{window} sd{max_stdev[2:]} {band[0][2:]}–{band[1][2:]}",
            ))
        for rel_spread, max_ask in product(("0.05", "0.10", "0.15", "0.20", "0.25"), ("0.35", "0.45", "0.60", "0.75", "0.90")):
            rows.append((
                "relative_spread_value",
                {"rel_spread": rel_spread, "min_ask": "0.05", "max_ask": max_ask},
                RelativeSpreadValue,
                f"Enter once when spread <= {rel_spread} * ask and ask <= {max_ask}.",
                f"RelSpread {rel_spread[2:]} cap {max_ask[2:]}",
            ))
    elif batch == "batch-009":
        for window, min_break, max_ask in product((2, 4, 8), ("0.01", "0.03", "0.05", "0.08"), ("0.60", "0.75", "0.90")):
            rows.append((
                "breakout_hold",
                {"window": window, "min_break": min_break, "max_ask": max_ask, "max_spread": "0.12"},
                BreakoutHold,
                f"Enter YES when the reference exceeds the max of the prior {window} references "
                f"by >= {min_break}; ask <= {max_ask}. Hold.",
                f"Breakout w{window} b{min_break[2:]} cap {max_ask[2:]}",
            ))
        for entry_index, min_ask, spread in product((1, 2, 3, 5, 8), ("0.60", "0.65", "0.70", "0.75", "0.80"), ("0.08", "0.12")):
            rows.append((
                "entry_timing_band",
                {"entry_index": entry_index, "min_ask": min_ask, "max_ask": "0.92", "max_spread": spread},
                EntryTimingBand,
                f"Favorite band {min_ask}–0.92, but entry allowed only from decision candle "
                f"#{entry_index} onward; spread <= {spread}.",
                f"Timing #{entry_index} {min_ask[2:]} s{spread[2:]}",
            ))
        for entry_index, spread in product((1, 2, 3, 5, 8, 13, 21), ("0.12", "0.20")):
            rows.append((
                "entry_timing_slice",
                {"entry_index": entry_index, "min_ask": "0.10", "max_ask": "0.90", "max_spread": spread},
                EntryTimingBand,
                f"One-slice band 0.10–0.90, entry allowed only from decision candle #{entry_index}; "
                f"spread <= {spread}.",
                f"Slice timing #{entry_index} s{spread[2:]}",
            ))
    elif batch == "batch-010":
        for min_ask, max_ask, spread in product(
            ("0.02", "0.05", "0.10"),
            ("0.30", "0.40", "0.45", "0.50"),
            ("0.02", "0.04", "0.06", "0.10"),
        ):
            rows.append((
                "tight_value_ranged",
                {"min_ask": min_ask, "max_ask": max_ask, "max_spread": spread},
                TightValueRanged,
                f"Tight-value entry with ask in {min_ask}–{max_ask} and spread <= {spread}.",
                f"Tight {min_ask[2:]}–{max_ask[2:]} s{spread[2:]}",
            ))
        for min_ask, max_ask, spread in product(
            ("0.60", "0.65", "0.70", "0.75"),
            ("0.85", "0.92"),
            ("0.25", "0.35", "0.50"),
        ):
            rows.append((
                "favorite_band_wide",
                {"min_ask": min_ask, "max_ask": max_ask, "max_spread": spread},
                FavoriteHold,
                f"Favorite band {min_ask}–{max_ask} that tolerates spread <= {spread}. "
                "Pairs with batch-002 to price the spread tolerance.",
                f"FavWide {min_ask[2:]}–{max_ask[2:]} s{spread[2:]}",
            ))
        for min_ask, max_ask, spread in product(
            ("0.01", "0.04", "0.08"),
            ("0.15", "0.25"),
            ("0.25", "0.50"),
        ):
            rows.append((
                "longshot_band_wide",
                {"min_ask": min_ask, "max_ask": max_ask, "max_spread": spread},
                LongshotHold,
                f"Longshot band {min_ask}–{max_ask} that tolerates spread <= {spread}. "
                "Pairs with batch-003.",
                f"LongWide {min_ask[2:]}–{max_ask[2:]} s{spread[2:]}",
            ))
        for min_ask, max_ask, spread in product(
            ("0.05", "0.10", "0.20", "0.40"),
            ("0.90",),
            ("0.06", "0.12", "0.20", "0.30"),
        ):
            rows.append((
                "slice_band",
                {"min_ask": min_ask, "max_ask": max_ask, "max_spread": spread},
                DiversifiedSlice,
                f"One-slice entry with ask in {min_ask}–{max_ask} and spread <= {spread}.",
                f"Slice {min_ask[2:]}–{max_ask[2:]} s{spread[2:]}",
            ))
    else:  # pragma: no cover
        raise ValueError(f"unknown batch {batch}")
    return rows


def _class_lookback(cls: type, parameters: dict) -> int:
    if issubclass(cls, (Momentum, Contrarian)):
        return int(parameters.get("min_prior_candles", 1)) + 1
    if cls is MeanRevert:
        return int(parameters.get("lookback", 3)) + 1
    if cls is VolumeMomentumWindow:
        return int(parameters.get("window", 5)) + 1
    if cls is VolatilityGate:
        return int(parameters.get("window", 5)) + 1
    if cls is BreakoutHold:
        return int(parameters.get("window", 4)) + 1
    return 1


def program_variants() -> list[Variant]:
    """Enumerate the program one strategy at a time. 100 per batch, 10 batches."""
    variants: list[Variant] = []
    seen_ids: set[str] = set()
    seen_users: set[str] = set()
    for batch_number in range(1, 11):
        batch = f"batch-{batch_number:03d}"
        topic, _statement = TOPICS[batch]
        rows = _variants_for_batch(batch)
        if len(rows) != 100:  # registry contract; tests also assert
            raise ValueError(f"{batch} has {len(rows)} variants, expected 100")
        for index, (family, parameters, cls, hypothesis, display) in enumerate(rows, start=1):
            lookback = _class_lookback(cls, parameters)
            if lookback + 1 > PROGRAM_PRIOR_WINDOW:
                raise ValueError(
                    f"{family} variant {parameters} needs {lookback + 1} prior candles, "
                    f"window is {PROGRAM_PRIOR_WINDOW}"
                )
            family_slug = family.replace("_", "-")
            strategy_id = f"{family_slug}-b{batch_number:03d}-{index:03d}"
            username = f"sim-b{batch_number:03d}-{index:03d}"
            if strategy_id in seen_ids or username in seen_users:
                raise ValueError(f"duplicate id or username at {strategy_id}")
            seen_ids.add(strategy_id)
            seen_users.add(username)
            strategy = cls()
            strategy.parameters = dict(parameters)
            variants.append(Variant(
                batch=batch,
                topic=topic,
                family=family,
                strategy_id=strategy_id,
                username=username,
                display_name=f"{display} · {batch}",
                hypothesis=hypothesis,
                strategy=strategy,
            ))
    return variants


def topic_statement(batch: str) -> tuple[str, str]:
    return TOPICS[batch]
