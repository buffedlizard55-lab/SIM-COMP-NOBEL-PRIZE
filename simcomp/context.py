"""Decision-time information channels for the research program.

Three channels extend what a program strategy may read. Each one is built only
from stored Kalshi fields whose timestamp proves they were public at the
decision time T (the candle end). The engine re-checks every guard at runtime and
raises instead of silently passing a later record.

1. Event quotes (``ctx.event``)
   For the market being decided, the latest candle of every stored market in the
   same Kalshi event and the same simulation universe with ``end_period_ts <= T``.
   Candles that close at T are public at T, so a sibling's candle closing at T is
   visible regardless of the order the engine happens to visit markets in.
   Source fields: Kalshi candlestick ``yes_bid.close``, ``yes_ask.close``,
   ``price.close``, ``volume``, ``open_interest``; event ``mutually_exclusive``
   from ``GET /events``.

2. Settled pool (``ctx.settled``)
   Every stored market (any universe) whose Kalshi ``settlement_ts`` is strictly
   before T, with its official ``result`` and its own pre-settlement reference
   prices. The result is public at settlement, so a record enters the pool only
   after that timestamp. Records that settle at or after T are not in the pool.

3. Schedule (``ctx.schedule``)
   The event's ``strike_date`` from ``GET /events`` when Kalshi publishes one
   (the Fed meeting time for KXFEDDECISION, the end of the measured day for
   KXHIGHNY). It is scheduled contract metadata, not an outcome. Market
   ``close_time`` is deliberately NOT used: on settled Nobel markets it is the
   actual (early) close written after the announcement, e.g. sub-second values
   such as 2025-10-17T00:29:40.415884Z on KXNOBELECON-25, which would leak when
   the market resolved. Nobel events publish no strike_date, so the schedule
   channel is empty for them and schedule-based rules abstain there.

What the channels cannot fix: the set of stored markets was chosen by the
collector at fetch time (the settled panel keeps the top 25 by lifetime volume).
Event quotes therefore cover only the stored contracts of an event, and the
settled pool is a post-selected sample. Both limits are reported, not hidden.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from simcomp.money import usable_quote


@dataclass(frozen=True)
class QuoteSnap:
    """One market's latest candle close at or before the decision time."""

    ticker: str
    end_ts: int
    yes_bid: Decimal | None
    yes_ask: Decimal | None
    ref: Decimal | None  # trade close if printed, else bid/ask mid, else None
    volume: Decimal | None
    open_interest: Decimal | None

    @property
    def mid(self) -> Decimal | None:
        if usable_quote(self.yes_bid) and usable_quote(self.yes_ask):
            return (self.yes_bid + self.yes_ask) / 2
        return None


@dataclass(frozen=True)
class SettledRecord:
    """A market whose official result was public before the decision time."""

    ticker: str
    series_ticker: str
    category: str
    event_ticker: str
    settlement_ts: int
    result: str  # "yes" or "no", Kalshi market.result
    open_time: int | None
    # (candle end, reference price) for every pre-settlement decision candle of
    # that market. All strictly before settlement_ts, so strictly before T.
    pairs: tuple


def reference_of(candle) -> Decimal | None:
    if usable_quote(candle.trade_close):
        return candle.trade_close
    if usable_quote(candle.yes_bid_close) and usable_quote(candle.yes_ask_close):
        mid = (candle.yes_bid_close + candle.yes_ask_close) / 2
        if usable_quote(mid):
            return mid
    return None


def parse_schedule(event: dict | None) -> tuple[int | None, str]:
    """Scheduled close from event.strike_date, or (None, reason).

    Accepted only when the timestamp is on a whole minute (no seconds and no
    fractional seconds). Kalshi's scheduled times in this snapshot are whole
    minutes (e.g. 2026-01-06T04:59:00Z); anything else looks like a written-after
    timestamp and is refused rather than trusted.
    """
    if not event:
        return None, "event record not stored"
    raw = event.get("strike_date")
    if not raw:
        return None, "Kalshi event has no strike_date"
    try:
        text = str(raw).replace("Z", "+00:00")
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None, f"unparseable strike_date {raw!r}"
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    if moment.second != 0 or moment.microsecond != 0:
        return None, f"strike_date {raw} is not on a whole minute; refused as possibly written after the fact"
    return int(moment.timestamp()), "events.json strike_date (GET /events), scheduled, stored at fetch time"


class EventIndex:
    """Per-universe event membership with bisectable candle timelines."""

    def __init__(self, prepared: list, events_by_ticker: dict | None = None):
        events_by_ticker = events_by_ticker or {}
        self._members: dict[str, list] = {}
        self._timeline: dict[str, tuple[list[int], list]] = {}
        self._meta: dict[str, SimpleNamespace] = {}
        for market, candles in prepared:
            key = market.event_ticker or market.ticker
            self._members.setdefault(key, []).append(market.ticker)
            self._timeline[market.ticker] = ([c.end_period_ts for c in candles], candles)
        for key, tickers in self._members.items():
            tickers.sort()
            record = events_by_ticker.get(key)
            close_ts, source = parse_schedule(record)
            self._meta[key] = SimpleNamespace(
                event_ticker=key,
                mutually_exclusive=(record or {}).get("mutually_exclusive"),
                stored_markets=len(tickers),
                scheduled_close_ts=close_ts,
                schedule_source=source,
            )
        self._cache_key = None
        self._cache_value = None

    def meta(self, event_ticker: str) -> SimpleNamespace | None:
        return self._meta.get(event_ticker)

    def view(self, event_ticker: str, as_of_ts: int) -> SimpleNamespace | None:
        key = (event_ticker, as_of_ts)
        if key == self._cache_key:
            return self._cache_value
        meta = self._meta.get(event_ticker)
        if meta is None:
            return None
        quotes = []
        for ticker in self._members[event_ticker]:
            stamps, candles = self._timeline[ticker]
            position = bisect.bisect_right(stamps, as_of_ts) - 1
            if position < 0:
                continue
            candle = candles[position]
            if candle.end_period_ts > as_of_ts:  # runtime guard; bisect already ensures this
                raise RuntimeError(f"lookahead guard: sibling {ticker} candle {candle.end_period_ts} > {as_of_ts}")
            quotes.append(QuoteSnap(
                ticker=ticker,
                end_ts=candle.end_period_ts,
                yes_bid=candle.yes_bid_close if usable_quote(candle.yes_bid_close) else None,
                yes_ask=candle.yes_ask_close if usable_quote(candle.yes_ask_close) else None,
                ref=reference_of(candle),
                volume=candle.volume,
                open_interest=candle.open_interest,
            ))
        value = SimpleNamespace(
            event_ticker=event_ticker,
            as_of_ts=as_of_ts,
            mutually_exclusive=meta.mutually_exclusive,
            stored_markets=meta.stored_markets,
            quotes=tuple(quotes),
        )
        self._cache_key = key
        self._cache_value = value
        return value

    def schedule(self, event_ticker: str) -> SimpleNamespace:
        meta = self._meta.get(event_ticker)
        if meta is None:
            return SimpleNamespace(close_ts=None, source="event not indexed")
        return SimpleNamespace(close_ts=meta.scheduled_close_ts, source=meta.schedule_source)


class SettledPool:
    """Monotone pool of settled markets, advanced strictly by settlement time."""

    def __init__(self, records: list[SettledRecord]):
        self._records = sorted(records, key=lambda r: (r.settlement_ts, r.ticker))
        self._stamps = [r.settlement_ts for r in self._records]
        self._count = -1
        self._view = None

    def view(self, as_of_ts: int) -> SimpleNamespace:
        count = bisect.bisect_left(self._stamps, as_of_ts)  # strictly before as_of_ts
        if count != self._count:
            records = tuple(self._records[:count])
            if records and records[-1].settlement_ts >= as_of_ts:  # runtime guard
                raise RuntimeError("lookahead guard: settled pool contains a record not yet settled")
            self._count = count
            self._view = SimpleNamespace(records=records, version=count)
        return self._view

    @property
    def size(self) -> int:
        return len(self._records)


def build_settled_records(all_markets: list, decision_candles_fn, categories: dict | None = None) -> list[SettledRecord]:
    """Settled records from every stored market with an official result and settlement_ts."""
    categories = categories or {}
    out = []
    for market in all_markets:
        result = market.settled_result
        if not result or market.settlement_ts is None:
            continue
        if market.market_type and market.market_type != "binary":
            continue
        candles, _flags = decision_candles_fn(market)
        pairs = []
        for candle in candles:
            ref = reference_of(candle)
            if ref is not None and candle.end_period_ts < market.settlement_ts:
                pairs.append((candle.end_period_ts, ref))
        out.append(SettledRecord(
            ticker=market.ticker,
            series_ticker=market.series_ticker,
            category=categories.get(market.series_ticker, ""),
            event_ticker=market.event_ticker,
            settlement_ts=market.settlement_ts,
            result=result,
            open_time=market.open_time,
            pairs=tuple(pairs),
        ))
    return out
