"""Pluggable simulated strategies.

Each strategy is a pure function of the decision-time view. It cannot see the
official result, settlement time, later order book, or any later candle.
Parameters are fixed before the run and stored with every trade.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from simcomp.money import usable_quote


@dataclass
class Intent:
    action: str  # buy or sell
    side: str  # yes or no
    quantity: int | None = None  # None means "use the competition size rule"
    reason: str = ""


@dataclass
class Decision:
    intents: list = field(default_factory=list)
    note: str = ""


def _spread_ok(candle, max_spread) -> bool:
    spread = candle.spread
    if spread is None:
        return False
    return spread >= 0 and spread <= max_spread


def _mid(candle):
    if usable_quote(candle.yes_bid_close) and usable_quote(candle.yes_ask_close):
        return (candle.yes_bid_close + candle.yes_ask_close) / 2
    return None


def _reference_price(candle):
    """Price used only as a signal, never as a fill. Trade close if printed, else mid."""
    if usable_quote(candle.trade_close):
        return candle.trade_close, "trade_close"
    mid = _mid(candle)
    if mid is not None and usable_quote(mid):
        return mid, "bid_ask_mid"
    return None, ""


class Strategy:
    id = ""
    name = ""
    summary = ""
    parameters: dict = {}

    def decide(self, ctx) -> Decision:
        raise NotImplementedError

    def public(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "summary": self.summary,
            "parameters": dict(self.parameters),
            "information_used": [
                "candles ending at or before the decision timestamp",
                "this participant's own simulated cash and position",
                "published series fee_type is applied by the engine, not read here",
            ],
            "information_not_used": [
                "official result",
                "settlement timestamp",
                "candles that end after the decision",
                "intra-candle high and low",
                "the order book fetched after the candle close",
                "other participants' orders",
            ],
        }


class HoldCash(Strategy):
    id = "hold_cash"
    name = "Hold cash"
    summary = "Control. Never trades. Same starting cash as every other participant, so the leaderboard has a do-nothing baseline."
    parameters = {}

    def decide(self, ctx) -> Decision:
        return Decision(note="control: no order")


class FavoriteHold(Strategy):
    id = "favorite_hold"
    name = "Favorite, hold"
    summary = (
        "Buy YES once, at the closing ask, when that ask is between the favorite "
        "band and the closing spread is within the cap. Hold to settlement. "
        "Does not sell."
    )
    parameters = {"min_ask": "0.65", "max_ask": "0.92", "max_spread": "0.08"}

    def decide(self, ctx) -> Decision:
        if ctx.position.qty:
            return Decision(note="already in position; hold")
        candle = ctx.candle
        ask = candle.yes_ask_close
        p = self.parameters
        if not usable_quote(ask):
            return Decision(note="no usable yes ask")
        if not _spread_ok(candle, ctx.decimal(p["max_spread"])):
            return Decision(note="spread outside cap or missing")
        if ask < ctx.decimal(p["min_ask"]) or ask > ctx.decimal(p["max_ask"]):
            return Decision(note="yes ask outside favorite band")
        return Decision(
            intents=[Intent("buy", "yes", reason=(
                f"yes ask close {ask} is inside {p['min_ask']}–{p['max_ask']} "
                f"and spread {candle.spread} <= {p['max_spread']}"
            ))],
            note="enter favorite",
        )


class LongshotHold(Strategy):
    id = "longshot_hold"
    name = "Longshot, hold"
    summary = "Buy YES once when the closing ask is in a low band and the spread is capped. Hold to settlement."
    parameters = {"min_ask": "0.04", "max_ask": "0.18", "max_spread": "0.08"}

    def decide(self, ctx) -> Decision:
        if ctx.position.qty:
            return Decision(note="already in position; hold")
        candle = ctx.candle
        ask = candle.yes_ask_close
        p = self.parameters
        if not usable_quote(ask):
            return Decision(note="no usable yes ask")
        if not _spread_ok(candle, ctx.decimal(p["max_spread"])):
            return Decision(note="spread outside cap or missing")
        if ask < ctx.decimal(p["min_ask"]) or ask > ctx.decimal(p["max_ask"]):
            return Decision(note="yes ask outside longshot band")
        return Decision(
            intents=[Intent("buy", "yes", reason=(
                f"yes ask close {ask} is inside {p['min_ask']}–{p['max_ask']} "
                f"and spread {candle.spread} <= {p['max_spread']}"
            ))],
            note="enter longshot",
        )


class _MoveStrategy(Strategy):
    direction = 1  # 1 follows the move, -1 fades it

    def decide(self, ctx) -> Decision:
        p = self.parameters
        if len(ctx.prior) < int(p["min_prior_candles"]):
            return Decision(note="not enough prior candles")
        candle = ctx.candle
        if not _spread_ok(candle, ctx.decimal(p["max_spread"])):
            return Decision(note="spread outside cap or missing")
        current, current_src = _reference_price(candle)
        previous, previous_src = _reference_price(ctx.prior[-1])
        if current is None or previous is None:
            return Decision(note="no reference price on this candle or the prior candle")
        move = current - previous
        threshold = ctx.decimal(p["min_move"])
        if abs(move) < threshold:
            return Decision(note=f"move {move} below {threshold}")
        follow_yes = move > 0
        want_yes = follow_yes if self.direction == 1 else not follow_yes
        side = "yes" if want_yes else "no"
        reason = (
            f"reference {previous_src} {previous} -> {current_src} {current} "
            f"(move {move}); direction={self.direction}; spread {candle.spread}"
        )
        if ctx.position.qty and ctx.position.side == side:
            return Decision(note="already hold the signaled side")
        intents = []
        if ctx.position.qty and ctx.position.side != side:
            intents.append(Intent("sell", ctx.position.side, ctx.position.qty, reason="exit opposite signal; " + reason))
        intents.append(Intent("buy", side, reason="enter; " + reason))
        return Decision(intents=intents, note="signal")


class Momentum(_MoveStrategy):
    id = "momentum"
    name = "Momentum"
    summary = "Follow a close-to-close move of at least the threshold. Signal uses trade close, or the bid/ask mid if no trade printed. Fills still use the closing quote, not the signal price."
    direction = 1
    parameters = {"min_move": "0.02", "max_spread": "0.12", "min_prior_candles": 1}


class Contrarian(_MoveStrategy):
    id = "contrarian"
    name = "Contrarian fade"
    summary = "Same signal as momentum, opposite side. Separates 'follow the move' from 'fade the move' under identical data and size rules."
    direction = -1
    parameters = {"min_move": "0.02", "max_spread": "0.12", "min_prior_candles": 1}


class MeanRevert(Strategy):
    id = "mean_revert"
    name = "Mean reversion"
    summary = "Buy YES when the reference price is at least the deviation below the mean of up to three prior reference prices. Sell YES when it has returned to that mean. Needs three prior candles so the mean is not a single print."
    parameters = {"deviation": "0.06", "lookback": 3, "max_spread": "0.12"}

    def decide(self, ctx) -> Decision:
        lookback = int(self.parameters["lookback"])
        if len(ctx.prior) < lookback:
            return Decision(note="not enough prior candles for the mean")
        if not _spread_ok(ctx.candle, ctx.decimal(self.parameters["max_spread"])):
            return Decision(note="spread outside cap or missing")
        refs = []
        for candle in ctx.prior[-lookback:]:
            price, _src = _reference_price(candle)
            if price is None:
                return Decision(note="a prior candle has no reference price")
            refs.append(price)
        mean = sum(refs) / len(refs)
        current, src = _reference_price(ctx.candle)
        if current is None:
            return Decision(note="no reference price")
        deviation = ctx.decimal(self.parameters["deviation"])
        if ctx.position.qty and ctx.position.side == "yes" and current >= mean:
            return Decision(
                intents=[Intent("sell", "yes", ctx.position.qty, reason=(
                    f"reference {src} {current} returned to prior mean {mean}"
                ))],
                note="exit reversion",
            )
        if ctx.position.qty:
            return Decision(note="holding; reversion exit not met")
        if current <= mean - deviation:
            return Decision(
                intents=[Intent("buy", "yes", reason=(
                    f"reference {src} {current} is at least {deviation} below prior mean {mean}"
                ))],
                note="enter reversion",
            )
        return Decision(note="not far enough below the prior mean")


class TightValue(Strategy):
    id = "tight_value"
    name = "Tight-spread value"
    summary = "Buy YES once only when the closing spread is very tight and the ask is at or below 0.45. Tests a liquidity filter against strategies that tolerate wider books."
    parameters = {"max_spread": "0.04", "max_ask": "0.45"}

    def decide(self, ctx) -> Decision:
        if ctx.position.qty:
            return Decision(note="already in position")
        candle = ctx.candle
        ask = candle.yes_ask_close
        if not usable_quote(ask):
            return Decision(note="no usable yes ask")
        if not _spread_ok(candle, ctx.decimal(self.parameters["max_spread"])):
            return Decision(note="spread wider than the tight cap or missing")
        if ask > ctx.decimal(self.parameters["max_ask"]):
            return Decision(note="ask above value cap")
        return Decision(
            intents=[Intent("buy", "yes", reason=(
                f"spread {candle.spread} <= {self.parameters['max_spread']} and yes ask {ask} <= {self.parameters['max_ask']}"
            ))],
            note="enter tight value",
        )


class DiversifiedSlice(Strategy):
    id = "diversified_slice"
    name = "One slice per market"
    summary = "Buy one YES slice on the first candle with a two-sided book, a capped spread, and an ask between 0.10 and 0.90. Compares broad participation with selective strategies."
    parameters = {"min_ask": "0.10", "max_ask": "0.90", "max_spread": "0.12"}

    def decide(self, ctx) -> Decision:
        if ctx.position.qty or ctx.ever_traded:
            return Decision(note="one entry only")
        candle = ctx.candle
        ask = candle.yes_ask_close
        if not usable_quote(ask) or not usable_quote(candle.yes_bid_close):
            return Decision(note="book is not two-sided")
        if not _spread_ok(candle, ctx.decimal(self.parameters["max_spread"])):
            return Decision(note="spread outside cap")
        if ask < ctx.decimal(self.parameters["min_ask"]) or ask > ctx.decimal(self.parameters["max_ask"]):
            return Decision(note="ask outside slice band")
        return Decision(
            intents=[Intent("buy", "yes", reason=(
                f"first two-sided candle; yes ask {ask}; spread {candle.spread}"
            ))],
            note="enter slice",
        )


class VolumeMomentum(Strategy):
    id = "volume_momentum"
    name = "Volume-confirmed momentum"
    summary = "Same side rule as momentum, but only when this candle's volume is strictly above the median volume of prior candles. Separates a price signal from a price-plus-activity signal."
    parameters = {"min_move": "0.02", "max_spread": "0.12", "min_prior_candles": 3}

    def decide(self, ctx) -> Decision:
        p = self.parameters
        if len(ctx.prior) < int(p["min_prior_candles"]):
            return Decision(note="not enough prior candles for a volume median")
        volumes = [c.volume for c in ctx.prior if c.volume is not None]
        if len(volumes) < int(p["min_prior_candles"]) or ctx.candle.volume is None:
            return Decision(note="volume missing")
        ordered = sorted(volumes)
        median = ordered[(len(ordered) - 1) // 2]
        if ctx.candle.volume <= median:
            return Decision(note=f"volume {ctx.candle.volume} is not above prior median {median}")
        if not _spread_ok(ctx.candle, ctx.decimal(p["max_spread"])):
            return Decision(note="spread outside cap or missing")
        current, current_src = _reference_price(ctx.candle)
        previous, previous_src = _reference_price(ctx.prior[-1])
        if current is None or previous is None:
            return Decision(note="no reference price")
        move = current - previous
        if abs(move) < ctx.decimal(p["min_move"]):
            return Decision(note="move below threshold")
        side = "yes" if move > 0 else "no"
        reason = (
            f"volume {ctx.candle.volume} > prior median {median}; "
            f"{previous_src} {previous} -> {current_src} {current}"
        )
        if ctx.position.qty and ctx.position.side == side:
            return Decision(note="already hold the signaled side")
        intents = []
        if ctx.position.qty and ctx.position.side != side:
            intents.append(Intent("sell", ctx.position.side, ctx.position.qty, reason="exit; " + reason))
        intents.append(Intent("buy", side, reason="enter; " + reason))
        return Decision(intents=intents, note="volume signal")


class FavoriteExit(Strategy):
    id = "favorite_exit"
    name = "Favorite with an exit"
    summary = "Same entry rule as Favorite, hold, but sells YES if the closing bid is 0.10 above the entry price or 0.08 below it. Compares hold-to-settlement with an explicit exit."
    parameters = {"min_ask": "0.65", "max_ask": "0.92", "max_spread": "0.08", "take": "0.10", "stop": "0.08"}

    def decide(self, ctx) -> Decision:
        candle = ctx.candle
        if ctx.position.qty and ctx.position.side == "yes":
            bid = candle.yes_bid_close
            if not usable_quote(bid):
                return Decision(note="cannot exit; no usable bid")
            entry = ctx.position.avg_entry_price
            if bid >= entry + ctx.decimal(self.parameters["take"]):
                return Decision(
                    intents=[Intent("sell", "yes", ctx.position.qty, reason=f"bid {bid} is {self.parameters['take']} above entry {entry}")],
                    note="take profit",
                )
            if bid <= entry - ctx.decimal(self.parameters["stop"]):
                return Decision(
                    intents=[Intent("sell", "yes", ctx.position.qty, reason=f"bid {bid} is {self.parameters['stop']} below entry {entry}")],
                    note="stop",
                )
            return Decision(note="hold; exit band not reached")
        if ctx.ever_traded:
            return Decision(note="already completed the single entry")
        ask = candle.yes_ask_close
        if not usable_quote(ask):
            return Decision(note="no usable yes ask")
        if not _spread_ok(candle, ctx.decimal(self.parameters["max_spread"])):
            return Decision(note="spread outside cap or missing")
        if ask < ctx.decimal(self.parameters["min_ask"]) or ask > ctx.decimal(self.parameters["max_ask"]):
            return Decision(note="yes ask outside favorite band")
        return Decision(
            intents=[Intent("buy", "yes", reason=f"yes ask close {ask} inside favorite band")],
            note="enter favorite-exit",
        )


class SeededNull(Strategy):
    id = "seeded_null"
    name = "Seeded null"
    summary = (
        "Null model. On about 3 percent of candles, buys a small YES or NO slice. "
        "The choice is a SHA-256 of the stored seed, ticker, and candle timestamp. "
        "It does not use later information and it is not a claim of skill."
    )
    parameters = {"seed": "20260924", "fire_per_mille": 30, "max_spread": "0.12"}

    def decide(self, ctx) -> Decision:
        if ctx.position.qty:
            return Decision(note="null model holds until settlement")
        if not _spread_ok(ctx.candle, ctx.decimal(self.parameters["max_spread"])):
            return Decision(note="spread outside cap or missing")
        digest = hashlib.sha256(
            f"{self.parameters['seed']}|{ctx.market.ticker}|{ctx.candle.end_period_ts}".encode()
        ).hexdigest()
        bucket = int(digest[:8], 16) % 1000
        if bucket >= int(self.parameters["fire_per_mille"]):
            return Decision(note="null draw did not fire")
        side = "yes" if int(digest[8:10], 16) % 2 == 0 else "no"
        return Decision(
            intents=[Intent("buy", side, reason=f"seeded null fired; bucket {bucket}; side {side}")],
            note="null entry",
        )


def default_strategies() -> list[Strategy]:
    return [
        HoldCash(),
        FavoriteHold(),
        LongshotHold(),
        Momentum(),
        MeanRevert(),
        Contrarian(),
        TightValue(),
        DiversifiedSlice(),
        VolumeMomentum(),
        FavoriteExit(),
        SeededNull(),
    ]


def clone_strategies(overrides: dict | None = None) -> list[Strategy]:
    strategies = default_strategies()
    overrides = overrides or {}
    for strategy in strategies:
        extra = overrides.get(strategy.id)
        if extra:
            strategy.parameters = {**strategy.parameters, **extra}
    return strategies


PARTICIPANTS = [
    ("sim-ada-hold", "hold_cash", "Ada Hold"),
    ("sim-basil-favorite", "favorite_hold", "Basil Favorite"),
    ("sim-cleo-longshot", "longshot_hold", "Cleo Longshot"),
    ("sim-dmitri-momentum", "momentum", "Dmitri Momentum"),
    ("sim-elena-revert", "mean_revert", "Elena Revert"),
    ("sim-farid-fade", "contrarian", "Farid Fade"),
    ("sim-gina-tight", "tight_value", "Gina Tight"),
    ("sim-hiro-slice", "diversified_slice", "Hiro Slice"),
    ("sim-ines-volume", "volume_momentum", "Ines Volume"),
    ("sim-jonas-exit", "favorite_exit", "Jonas Exit"),
    ("sim-kira-null", "seeded_null", "Kira Null"),
]
