"""Deterministic paper-trading engine.

Participants are simulated independently against stored Kalshi quotes. They do
not trade with each other and they do not send orders to Kalshi.

A decision at candle end T may use only candles of that market with
end_period_ts <= T, and only if T is strictly before settlement_ts when a
settlement timestamp is known. The official result is attached after the
decision loop, in attach_later_results, and is not on the decision view.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from types import SimpleNamespace

from simcomp.kalshi_parse import Candle, Market
from simcomp.money import ZERO, money, taker_fee, unix_to_iso, usable_quote, D
from simcomp.strategies import Decision, Intent, PARTICIPANTS, Strategy, clone_strategies

SETTLED_STATUSES = {"determined", "finalized", "amended"}


@dataclass
class SimConfig:
    competition_id: str
    title: str
    kind: str  # historical_backtest | forward_simulation | assumption_run
    data_tier: str
    starting_cash: Decimal = Decimal("10000")
    target_entry_spend: Decimal = Decimal("100")
    max_contracts: int = 500
    max_cost_per_market: Decimal = Decimal("300")
    max_spend_fraction: Decimal = Decimal("0.05")
    fees_enabled: bool = True
    fill_model: str = "taker_close_quote"
    assumption_note: str = ""
    primary: bool = True

    def public(self) -> dict:
        return {
            "competition_id": self.competition_id,
            "title": self.title,
            "kind": self.kind,
            "data_tier": self.data_tier,
            "starting_cash": money(self.starting_cash),
            "target_entry_spend": money(self.target_entry_spend),
            "max_contracts": self.max_contracts,
            "max_cost_per_market": money(self.max_cost_per_market),
            "max_spend_fraction": str(self.max_spend_fraction),
            "fees_enabled": self.fees_enabled,
            "fill_model": self.fill_model,
            "assumption_note": self.assumption_note,
            "primary": self.primary,
            "simulated": True,
            "participants_trade_with_each_other": False,
        }


@dataclass
class Position:
    side: str = ""
    qty: int = 0
    cost: Decimal = ZERO
    avg_entry_price: Decimal = ZERO

    def copy(self) -> "Position":
        return Position(self.side, self.qty, self.cost, self.avg_entry_price)


@dataclass
class Book:
    cash: Decimal
    position: Position = field(default_factory=Position)
    ever_traded: bool = False
    realized: Decimal = ZERO
    fees: Decimal = ZERO
    trade_count: int = 0
    wins: int = 0
    losses: int = 0
    settled_round_trips: int = 0
    last_reason: str = ""
    peak: Decimal = ZERO
    max_drawdown: Decimal = ZERO


class DecisionView:
    """The only object a strategy receives. No result, no future candles."""

    __slots__ = ("as_of_ts", "market", "candle", "prior", "position", "cash", "ever_traded")

    def __init__(self, as_of_ts, market, candle, prior, position, cash, ever_traded):
        self.as_of_ts = as_of_ts
        self.market = market
        self.candle = candle
        self.prior = prior
        self.position = position
        self.cash = cash
        self.ever_traded = ever_traded

    @staticmethod
    def decimal(value) -> Decimal:
        return D(value)


def decision_candles(market: Market) -> tuple[list[Candle], list[dict]]:
    """Candles a strategy may see. Drops anything at or after settlement."""
    flags = []
    candles = sorted(market.candles, key=lambda c: c.end_period_ts)
    seen = set()
    unique = []
    for candle in candles:
        if candle.end_period_ts in seen:
            flags.append({
                "code": "duplicate_candle",
                "severity": "review",
                "message": f"Duplicate candle end {candle.end_period_ts} on {market.ticker}; kept the first.",
                "market_ticker": market.ticker,
            })
            continue
        seen.add(candle.end_period_ts)
        unique.append(candle)
    if market.settlement_ts is None and market.status in SETTLED_STATUSES:
        flags.append({
            "code": "settled_without_timestamp",
            "severity": "review",
            "message": (
                f"{market.ticker} status is {market.status} but settlement_ts is missing. "
                "No simulated settlement and no simulated trades: a decision clock cannot be proved."
            ),
            "market_ticker": market.ticker,
        })
        return [], flags
    allowed = []
    for candle in unique:
        if market.settlement_ts is not None and candle.end_period_ts >= market.settlement_ts:
            continue
        if market.open_time is not None and candle.end_period_ts < market.open_time:
            continue
        allowed.append(candle)
    if not allowed:
        flags.append({
            "code": "no_pre_settlement_candles",
            "severity": "info",
            "message": f"{market.ticker} has no candlestick ending before settlement (or before a proved decision clock).",
            "market_ticker": market.ticker,
        })
    return allowed, flags


def _quote_fill(candle: Candle, action: str, side: str, fill_model: str):
    """Return (price, source_field) or (None, reason). Never invents a price."""
    if fill_model == "last_trade":
        if usable_quote(candle.trade_close):
            return candle.trade_close, "price.close"
        return None, "no last trade; fill model does not fall back to the quote"
    if action == "buy" and side == "yes":
        if usable_quote(candle.yes_ask_close):
            return candle.yes_ask_close, "yes_ask.close"
        return None, "no usable yes ask"
    if action == "sell" and side == "yes":
        if usable_quote(candle.yes_bid_close):
            return candle.yes_bid_close, "yes_bid.close"
        return None, "no usable yes bid"
    if action == "buy" and side == "no":
        # A YES bid at P is economically a NO ask at 1-P. Use the published bid only.
        if usable_quote(candle.yes_bid_close):
            return (Decimal("1") - candle.yes_bid_close), "derived_no_ask_from_yes_bid.close"
        return None, "no usable yes bid, so NO ask cannot be derived"
    if action == "sell" and side == "no":
        if usable_quote(candle.yes_ask_close):
            return (Decimal("1") - candle.yes_ask_close), "derived_no_bid_from_yes_ask.close"
        return None, "no usable yes ask, so NO bid cannot be derived"
    return None, "unsupported action"


def _size_for(config: SimConfig, book: Book, position: Position, price: Decimal, requested: int | None) -> tuple[int, str]:
    if requested is not None and requested <= 0:
        return 0, "requested quantity was not positive"
    spend_cap = min(config.target_entry_spend, config.starting_cash * config.max_spend_fraction, book.cash)
    room = config.max_cost_per_market - position.cost
    if room <= 0:
        return 0, "per-market cost cap already reached"
    spend_cap = min(spend_cap, room, book.cash)
    if spend_cap <= 0 or price <= 0:
        return 0, "no cash under the size rules"
    by_spend = int(spend_cap / price)
    qty = by_spend if requested is None else min(requested, by_spend)
    qty = min(qty, config.max_contracts)
    if qty < 1:
        return 0, "one contract would exceed the entry budget or remaining cash"
    return qty, ""


def _mark(position: Position, candle: Candle | None) -> tuple[Decimal, str]:
    if position.qty <= 0 or candle is None:
        return ZERO, "flat"
    if position.side == "yes":
        if usable_quote(candle.yes_bid_close):
            return candle.yes_bid_close * position.qty, "yes_bid.close"
        return ZERO, "no usable yes bid; liquidation mark set to 0 and flagged"
    if position.side == "no":
        if usable_quote(candle.yes_ask_close):
            no_bid = Decimal("1") - candle.yes_ask_close
            if usable_quote(no_bid):
                return no_bid * position.qty, "derived_no_bid_from_yes_ask.close"
        return ZERO, "no usable NO bid; liquidation mark set to 0 and flagged"
    return ZERO, "unknown side"


def assign_ranks(rows: list[dict]) -> None:
    """Competition rank. Equal ending equity shares a rank. Alphabetical id is not a win."""
    rows.sort(key=lambda row: (-D(row["ending_equity"]), row["participant_id"]))
    seen = None
    rank = 0
    for index, row in enumerate(rows, start=1):
        equity = row["ending_equity"]
        if equity != seen:
            rank = index
            seen = equity
        row["rank"] = rank
        row["tied"] = sum(1 for other in rows if other["ending_equity"] == equity) > 1


def _drawdown(book: Book, equity: Decimal) -> None:
    if equity > book.peak:
        book.peak = equity
    drop = book.peak - equity
    if drop > book.max_drawdown:
        book.max_drawdown = drop


def run_competition(markets: list[Market], config: SimConfig, strategies: list[Strategy] | None = None) -> dict:
    strategies = strategies or clone_strategies()
    by_id = {s.id: s for s in strategies}
    participants = []
    for username, strategy_id, display in PARTICIPANTS:
        if strategy_id not in by_id:
            continue
        participants.append({
            "id": username,
            "username": username,
            "display_name": display,
            "strategy_id": strategy_id,
            "simulated": True,
            "real_kalshi_account": False,
        })

    flags: list[dict] = []
    prepared = []
    for market in markets:
        if market.market_type and market.market_type != "binary":
            flags.append({
                "code": "not_binary",
                "severity": "info",
                "message": f"{market.ticker} market_type={market.market_type}; not simulated.",
                "market_ticker": market.ticker,
            })
            continue
        candles, market_flags = decision_candles(market)
        flags.extend(market_flags)
        if not candles:
            continue
        prepared.append((market, candles))

    books = {
        p["id"]: Book(cash=config.starting_cash, peak=config.starting_cash)
        for p in participants
    }
    # Per-market position. A book above is the cash book; positions live here.
    positions: dict[tuple[str, str], Position] = {}
    ever: dict[tuple[str, str], bool] = {}
    trades = []
    equity_points = []
    seq = 0
    skip_counts: dict[tuple[str, str], int] = {}

    events = []
    for market, candles in prepared:
        for index, candle in enumerate(candles):
            events.append((candle.end_period_ts, market.ticker, index, market, candles))
    events.sort(key=lambda item: (item[0], item[1]))

    def position_for(pid: str, ticker: str) -> Position:
        return positions.setdefault((pid, ticker), Position())

    for end_ts, _ticker, index, market, candles in events:
        candle = candles[index]
        prior = tuple(candles[:index])
        if any(c.end_period_ts > end_ts for c in prior) or candle.end_period_ts != end_ts:
            raise RuntimeError("lookahead guard failed while building the decision view")
        if market.settlement_ts is not None and end_ts >= market.settlement_ts:
            raise RuntimeError(f"lookahead guard: {market.ticker} candle {end_ts} is not before settlement")
        market_view = SimpleNamespace(
            ticker=market.ticker,
            title=market.title,
            open_time=market.open_time,
            series_ticker=market.series_ticker,
            event_ticker=market.event_ticker,
        )
        for participant in participants:
            strategy = by_id[participant["strategy_id"]]
            pos = position_for(participant["id"], market.ticker)
            book = books[participant["id"]]
            view = DecisionView(
                as_of_ts=end_ts,
                market=market_view,
                candle=candle,
                prior=prior,
                position=pos.copy(),
                cash=book.cash,
                ever_traded=ever.get((participant["id"], market.ticker), False),
            )
            if hasattr(view.market, "result") or hasattr(view, "result"):
                raise RuntimeError("decision view leaked result")
            decision = strategy.decide(view)
            if not isinstance(decision, Decision):
                raise TypeError(f"{strategy.id} did not return Decision")
            # Sells first so a flip in one candle can use the proceeds.
            intents = sorted(decision.intents, key=lambda item: 0 if item.action == "sell" else 1)
            if not intents and decision.note:
                key = (participant["id"], decision.note.split(":")[0][:80])
                skip_counts[key] = skip_counts.get(key, 0) + 1
            for intent in intents:
                seq, row, clip = _apply_intent(
                    seq, config, participant, strategy, market, candle, book, pos, intent, end_ts
                )
                if row:
                    ever[(participant["id"], market.ticker)] = True
                    trades.append(row)
                    book.last_reason = row["reason"]
                    _drawdown(book, _equity(book, positions, participant["id"], market.ticker, candle))
                    equity_points.append(_equity_point(config, participant, book, positions, end_ts, market.ticker, candle))
                elif clip:
                    key = (participant["id"], clip.split(";")[0][:80])
                    skip_counts[key] = skip_counts.get(key, 0) + 1

    # Settlement is a later event. Strategies are not called.
    for market, candles in prepared:
        result = market.settled_result
        if not result:
            continue
        if market.settlement_ts is None:
            continue
        for participant in participants:
            pos = positions.get((participant["id"], market.ticker))
            if not pos or pos.qty <= 0:
                continue
            book = books[participant["id"]]
            won = (result == "yes" and pos.side == "yes") or (result == "no" and pos.side == "no")
            payout = (Decimal(pos.qty) if won else ZERO)
            realized = payout - pos.cost
            book.cash += payout
            book.realized += realized
            book.settled_round_trips += 1
            if realized > 0:
                book.wins += 1
            elif realized < 0:
                book.losses += 1
            seq += 1
            trades.append({
                "trade_id": f"{config.competition_id}:{participant['id']}:{seq:05d}",
                "competition_id": config.competition_id,
                "participant_id": participant["id"],
                "strategy_id": participant["strategy_id"],
                "strategy_parameters": dict(by_id[participant["strategy_id"]].parameters),
                "simulated": True,
                "record_type": "simulated_settlement",
                "real_order": False,
                "market_ticker": market.ticker,
                "event_ticker": market.event_ticker,
                "series_ticker": market.series_ticker,
                "action": "settlement",
                "side": pos.side,
                "price": "1.0000" if won else "0.0000",
                "quantity": pos.qty,
                "quantity_requested": pos.qty,
                "clip_reason": "",
                "fee": "0.0000",
                "fee_model": "no_separate_settlement_fee_in_fetched_payload",
                "notional": money(payout),
                "cash_after": money(book.cash),
                "realized_pnl_this_event": money(realized),
                "timestamp": unix_to_iso(market.settlement_ts),
                "timestamp_unix": market.settlement_ts,
                "decision_candle_end_unix": None,
                "information_available_through_unix": market.settlement_ts,
                "outcome_known_at_decision": False,
                "this_event_is_when_outcome_is_applied": True,
                "reason": f"Official Kalshi result '{result}' applied at settlement_ts. Not available to the strategy.",
                "fill_price_source": "market.result",
                "yes_bid_close": None,
                "yes_ask_close": None,
                "trade_close": None,
                "spread": None,
                "source_market_url": market.source_url,
                "later_official_result": result,
                "later_result_used_in_decision": False,
            })
            pos.qty = 0
            pos.cost = ZERO
            pos.side = ""
            _drawdown(book, book.cash)
            equity_points.append({
                "competition_id": config.competition_id,
                "participant_id": participant["id"],
                "timestamp_unix": market.settlement_ts,
                "timestamp": unix_to_iso(market.settlement_ts),
                "equity": money(book.cash),
                "simulated": True,
                "point_type": "settlement",
            })

    # Final liquidation mark for anything still open, using the last decision candle only.
    last_candle = {market.ticker: candles[-1] for market, candles in prepared}
    position_rows = []
    for participant in participants:
        book = books[participant["id"]]
        mtm_total = ZERO
        for market, candles in prepared:
            pos = positions.get((participant["id"], market.ticker))
            if not pos or pos.qty <= 0:
                continue
            mark, mark_source = _mark(pos, last_candle.get(market.ticker))
            mtm_total += mark
            if mark_source.startswith("no usable"):
                flags.append({
                    "code": "unmarked_position",
                    "severity": "review",
                    "message": f"{participant['id']} {market.ticker}: {mark_source}",
                    "market_ticker": market.ticker,
                    "participant_id": participant["id"],
                })
            position_rows.append({
                "competition_id": config.competition_id,
                "participant_id": participant["id"],
                "strategy_id": participant["strategy_id"],
                "market_ticker": market.ticker,
                "event_ticker": market.event_ticker,
                "series_ticker": market.series_ticker,
                "simulated": True,
                "status": "open",
                "side": pos.side,
                "quantity": pos.qty,
                "avg_entry_price": money(pos.avg_entry_price) if pos.qty else None,
                "cost_basis": money(pos.cost),
                "liquidation_value": money(mark),
                "liquidation_source": mark_source,
                "unrealized_pnl": money(mark - pos.cost),
                "mark_candle_end_unix": last_candle[market.ticker].end_period_ts,
                "official_result_at_fetch": market.result or "",
                "official_result_used_in_mark": False,
            })
        book.mtm = mtm_total  # type: ignore[attr-defined]
        equity = book.cash + mtm_total
        _drawdown(book, equity)
        equity_points.append({
            "competition_id": config.competition_id,
            "participant_id": participant["id"],
            "timestamp_unix": None,
            "timestamp": "",
            "equity": money(equity),
            "simulated": True,
            "point_type": "final_mark",
        })

    leaderboard = []
    for participant in participants:
        book = books[participant["id"]]
        mtm = getattr(book, "mtm", ZERO)
        equity = book.cash + mtm
        unrealized = equity - config.starting_cash - book.realized
        trips = book.settled_round_trips
        leaderboard.append({
            "participant_id": participant["id"],
            "display_name": participant["display_name"],
            "strategy_id": participant["strategy_id"],
            "simulated": True,
            "starting_cash": money(config.starting_cash),
            "ending_equity": money(equity),
            "cash": money(book.cash),
            "liquidation_value": money(mtm),
            "realized_pnl": money(book.realized),
            "unrealized_pnl": money(unrealized),
            "fees": money(book.fees),
            "trade_count": book.trade_count,
            "open_positions": sum(1 for row in position_rows if row["participant_id"] == participant["id"]),
            "roi": money((equity - config.starting_cash) / config.starting_cash),
            "max_drawdown": money(book.max_drawdown),
            "settled_round_trips": trips,
            "wins": book.wins,
            "losses": book.losses,
            "win_rate_settled": None if trips == 0 else money(Decimal(book.wins) / Decimal(trips)),
        })
    assign_ranks(leaderboard)

    market_results = []
    for market, candles in prepared:
        by_participant = {}
        for participant in participants:
            pid = participant["id"]
            related = [t for t in trades if t["participant_id"] == pid and t["market_ticker"] == market.ticker]
            pos = positions.get((pid, market.ticker), Position())
            mark, mark_source = _mark(pos, candles[-1]) if pos.qty else (ZERO, "flat")
            realized = sum(D(t["realized_pnl_this_event"]) for t in related if t["action"] != "buy")
            # Buys realize 0 in realized_pnl_this_event. Sells and settlements carry it.
            by_participant[pid] = {
                "trades": len(related),
                "realized_pnl": money(sum(D(t.get("realized_pnl_this_event") or "0") for t in related)),
                "unrealized_pnl": money((mark - pos.cost) if pos.qty else ZERO),
                "ending_side": pos.side if pos.qty else "",
                "ending_qty": pos.qty,
                "last_reason": books[pid].last_reason if related else "",
                "reasons": [t.get("reason") for t in related],
            }
        market_results.append({
            "competition_id": config.competition_id,
            "ticker": market.ticker,
            "title": market.title,
            "subtitle": market.subtitle,
            "event_ticker": market.event_ticker,
            "series_ticker": market.series_ticker,
            "data_tier": market.tier,
            "status": market.status,
            "official_result": market.settled_result or (market.result or ""),
            "result_is_simulated": False,
            "result_label": "historical_official" if market.settled_result else "unsettled",
            "settlement_ts": market.settlement_ts,
            "source_url": market.source_url,
            "candle_source_url": market.candle_source_url,
            "decision_candles": len(candles),
            "participants": by_participant,
            "simulated_activity": True,
        })

    return {
        "config": config.public(),
        "participants": participants,
        "strategies": [s.public() for s in strategies],
        "trades": trades,
        "positions": position_rows,
        "leaderboard": leaderboard,
        "equity": equity_points,
        "market_results": market_results,
        "flags": flags,
        "skip_counts": [
            {"participant_id": pid, "note": note, "count": count}
            for (pid, note), count in sorted(skip_counts.items())
        ],
        "markets_used": len(prepared),
    }


def _equity(book: Book, positions, pid: str, current_ticker: str, candle: Candle) -> Decimal:
    total = book.cash
    # Mark only the market we just touched; other positions keep their cost out of cash
    # and are marked at the final pass. Intra-run drawdown uses cash plus this market's mark
    # plus other positions at cost (a conservative incomplete mark). Final equity is authoritative.
    for (opid, ticker), pos in positions.items():
        if opid != pid or pos.qty <= 0:
            continue
        if ticker == current_ticker:
            mark, _src = _mark(pos, candle)
            total += mark
        else:
            total += pos.cost
    return total


def _equity_point(config, participant, book, positions, end_ts, ticker, candle) -> dict:
    return {
        "competition_id": config.competition_id,
        "participant_id": participant["id"],
        "timestamp_unix": end_ts,
        "timestamp": unix_to_iso(end_ts),
        "equity": money(_equity(book, positions, participant["id"], ticker, candle)),
        "simulated": True,
        "point_type": "fill",
        "market_ticker": ticker,
    }


def _apply_intent(seq, config, participant, strategy, market, candle, book, pos, intent: Intent, end_ts):
    if intent.action not in ("buy", "sell") or intent.side not in ("yes", "no"):
        return seq, None, "intent was not a buy or sell of yes or no"
    if intent.action == "sell":
        if pos.qty <= 0 or pos.side != intent.side:
            return seq, None, "no position on that side to sell"
        price, source = _quote_fill(candle, "sell", intent.side, config.fill_model)
        if price is None:
            return seq, None, source
        qty = pos.qty if intent.quantity is None else min(intent.quantity, pos.qty)
        if qty < 1:
            return seq, None, "sell quantity clipped to zero"
        fee = taker_fee(market.fee_multiplier, qty, price) if config.fees_enabled and _fee_applies(market) else ZERO
        fee_model = _fee_model(config, market)
        proceeds = price * qty
        if proceeds < fee:
            return seq, None, "exit fee exceeds proceeds; not filled"
        alloc = pos.cost * Decimal(qty) / Decimal(pos.qty)
        realized = proceeds - fee - alloc
        book.cash += proceeds - fee
        book.fees += fee
        book.realized += realized
        book.trade_count += 1
        pos.qty -= qty
        pos.cost -= alloc
        if pos.qty == 0:
            pos.side = ""
            pos.avg_entry_price = ZERO
            pos.cost = ZERO
            book.settled_round_trips += 1
            if realized > 0:
                book.wins += 1
            elif realized < 0:
                book.losses += 1
        seq += 1
        return seq, _trade_row(
            seq, config, participant, strategy, market, candle, intent, qty, qty, "",
            price, source, fee, fee_model, proceeds, book.cash, realized, end_ts,
        ), ""

    if pos.qty and pos.side != intent.side:
        return seq, None, "opposite side blocked; a sell must come first"
    price, source = _quote_fill(candle, "buy", intent.side, config.fill_model)
    if price is None:
        return seq, None, source
    qty, clip = _size_for(config, book, pos, price, intent.quantity)
    if qty < 1:
        return seq, None, clip or "size clipped to zero"
    fee = taker_fee(market.fee_multiplier, qty, price) if config.fees_enabled and _fee_applies(market) else ZERO
    fee_model = _fee_model(config, market)
    cost = price * qty + fee
    if cost > book.cash:
        # Shrink to what cash can pay, including the fee. One retry.
        qty = int(book.cash / (price + (fee / qty if qty else price)))
        if qty < 1:
            return seq, None, "cash cannot cover price plus fee"
        fee = taker_fee(market.fee_multiplier, qty, price) if config.fees_enabled and _fee_applies(market) else ZERO
        cost = price * qty + fee
        if cost > book.cash:
            return seq, None, "cash cannot cover price plus fee"
        clip = (clip + "; " if clip else "") + "shrunk to remaining cash"
    book.cash -= cost
    book.fees += fee
    book.trade_count += 1
    new_qty = pos.qty + qty
    pos.avg_entry_price = ((pos.avg_entry_price * pos.qty) + (price * qty)) / Decimal(new_qty) if new_qty else ZERO
    pos.cost += cost
    pos.qty = new_qty
    pos.side = intent.side
    seq += 1
    return seq, _trade_row(
        seq, config, participant, strategy, market, candle, intent, intent.quantity or qty, qty, clip,
        price, source, fee, fee_model, cost, book.cash, ZERO, end_ts,
    ), ""


def _fee_applies(market: Market) -> bool:
    fee_type = (market.fee_type or "").lower()
    return fee_type.startswith("quadratic")


def _fee_model(config: SimConfig, market: Market) -> str:
    if not config.fees_enabled:
        return "fees_disabled_assumption"
    if not _fee_applies(market):
        return "fee_not_applied_fee_type_not_quadratic"
    if (market.fee_type or "").lower() == "quadratic_with_maker_fees":
        return "quadratic_taker_v1_maker_schedule_not_charged"
    return "quadratic_taker_v1"


def _trade_row(seq, config, participant, strategy, market, candle, intent, requested, qty, clip, price, source, fee, fee_model, notional, cash_after, realized, end_ts):
    spread = candle.spread
    return {
        "trade_id": f"{config.competition_id}:{participant['id']}:{seq:05d}",
        "competition_id": config.competition_id,
        "participant_id": participant["id"],
        "strategy_id": strategy.id,
        "strategy_parameters": dict(strategy.parameters),
        "simulated": True,
        "record_type": "simulated_trade",
        "real_order": False,
        "market_ticker": market.ticker,
        "event_ticker": market.event_ticker,
        "series_ticker": market.series_ticker,
        "action": intent.action,
        "side": intent.side,
        "price": money(price),
        "quantity": qty,
        "quantity_requested": requested,
        "clip_reason": clip,
        "fee": money(fee),
        "fee_model": fee_model,
        "notional": money(notional),
        "cash_after": money(cash_after),
        "realized_pnl_this_event": money(realized),
        "timestamp": unix_to_iso(end_ts),
        "timestamp_unix": end_ts,
        "decision_candle_end_unix": end_ts,
        "information_available_through_unix": end_ts,
        "outcome_known_at_decision": False,
        "this_event_is_when_outcome_is_applied": False,
        "reason": intent.reason,
        "fill_price_source": source,
        "yes_bid_close": money(candle.yes_bid_close) if candle.yes_bid_close is not None else None,
        "yes_ask_close": money(candle.yes_ask_close) if candle.yes_ask_close is not None else None,
        "trade_close": money(candle.trade_close) if candle.trade_close is not None else None,
        "spread": money(spread) if spread is not None else None,
        "source_market_url": market.source_url,
        "later_official_result": None,
        "later_result_used_in_decision": False,
    }


def attach_later_results(result: dict, markets: list[Market]) -> dict:
    """Stamp the official result onto trade rows after decisions are finished.

    The field is for the audit export. later_result_used_in_decision is always false.
    """
    by_ticker = {m.ticker: m for m in markets}
    for trade in result["trades"]:
        market = by_ticker.get(trade["market_ticker"])
        if not market:
            continue
        trade["later_official_result"] = market.settled_result or ""
        trade["later_result_source"] = market.source_url
        trade["later_result_used_in_decision"] = False
        trade["later_result_note"] = (
            "Attached after the decision loop from the stored Kalshi market payload. "
            "Not an input to the strategy."
        )
    return result
