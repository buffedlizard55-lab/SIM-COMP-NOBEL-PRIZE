"""Normalize official Kalshi market and candlestick payloads.

Field names differ between the live and historical candlestick schemas.
Both are accepted. Missing prices stay missing. Nothing is interpolated.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from simcomp.money import dollars_or_none, parse_unix


def _obj(value) -> dict:
    return value if isinstance(value, dict) else {}


def _first_dollars(obj: dict, *keys):
    for key in keys:
        if key in obj and obj[key] not in (None, ""):
            return dollars_or_none(obj[key])
    return None


def _count(raw: dict, *keys):
    for key in keys:
        if key in raw and raw[key] not in (None, ""):
            return dollars_or_none(raw[key])
    return None


@dataclass
class Candle:
    end_period_ts: int
    yes_bid_close: object = None
    yes_ask_close: object = None
    trade_close: object = None
    volume: object = None
    open_interest: object = None
    # Stored for the market page. Not copied into the decision view.
    yes_bid_low: object = None
    yes_bid_high: object = None
    yes_ask_low: object = None
    yes_ask_high: object = None
    trade_low: object = None
    trade_high: object = None

    @property
    def spread(self):
        if self.yes_bid_close is None or self.yes_ask_close is None:
            return None
        return self.yes_ask_close - self.yes_bid_close


def parse_candle(raw: dict) -> Candle:
    if "end_period_ts" not in raw:
        raise ValueError("candlestick missing end_period_ts")
    bid = _obj(raw.get("yes_bid"))
    ask = _obj(raw.get("yes_ask"))
    price = _obj(raw.get("price"))
    return Candle(
        end_period_ts=int(raw["end_period_ts"]),
        yes_bid_close=_first_dollars(bid, "close_dollars", "close"),
        yes_ask_close=_first_dollars(ask, "close_dollars", "close"),
        trade_close=_first_dollars(price, "close_dollars", "close"),
        volume=_count(raw, "volume_fp", "volume"),
        open_interest=_count(raw, "open_interest_fp", "open_interest"),
        yes_bid_low=_first_dollars(bid, "low_dollars", "low"),
        yes_bid_high=_first_dollars(bid, "high_dollars", "high"),
        yes_ask_low=_first_dollars(ask, "low_dollars", "low"),
        yes_ask_high=_first_dollars(ask, "high_dollars", "high"),
        trade_low=_first_dollars(price, "low_dollars", "low"),
        trade_high=_first_dollars(price, "high_dollars", "high"),
    )


@dataclass
class Market:
    ticker: str
    event_ticker: str
    series_ticker: str
    title: str
    subtitle: str
    rules_primary: str
    status: str
    result: str
    market_type: str
    open_time: int | None
    close_time: int | None
    settlement_ts: int | None
    expected_expiration_time: int | None
    fee_type: str
    fee_multiplier: str
    volume: str
    tier: str
    source_url: str
    candle_source_url: str
    settlement_sources: list
    raw_status_fields: dict = field(default_factory=dict)
    candles: list = field(default_factory=list)
    universe: str = ""

    @property
    def settled_result(self) -> str:
        text = (self.result or "").strip().lower()
        if text in ("yes", "no") and self.status in ("determined", "finalized", "amended"):
            return text
        return ""


def market_from_payload(raw: dict, *, tier: str, source_url: str, series: dict | None = None) -> Market:
    series = series or {}
    title = raw.get("title") or raw.get("yes_sub_title") or raw.get("ticker") or ""
    return Market(
        ticker=raw.get("ticker") or "",
        event_ticker=raw.get("event_ticker") or "",
        series_ticker=raw.get("series_ticker") or series.get("ticker") or "",
        title=title,
        subtitle=raw.get("yes_sub_title") or raw.get("subtitle") or "",
        rules_primary=raw.get("rules_primary") or "",
        status=(raw.get("status") or "").strip().lower(),
        result=(raw.get("result") or "").strip().lower(),
        market_type=(raw.get("market_type") or "").strip().lower(),
        open_time=parse_unix(raw.get("open_time")),
        close_time=parse_unix(raw.get("close_time")),
        settlement_ts=parse_unix(raw.get("settlement_ts")),
        expected_expiration_time=parse_unix(raw.get("expected_expiration_time")),
        fee_type=str(series.get("fee_type") or raw.get("fee_type") or ""),
        fee_multiplier=str(series.get("fee_multiplier") if series.get("fee_multiplier") is not None else "1"),
        volume=str(raw.get("volume_fp") or raw.get("volume") or ""),
        tier=tier,
        source_url=source_url,
        candle_source_url="",
        settlement_sources=list(series.get("settlement_sources") or []),
        raw_status_fields={
            "status": raw.get("status"),
            "result": raw.get("result"),
            "settlement_value_dollars": raw.get("settlement_value_dollars"),
            "expiration_value": raw.get("expiration_value"),
            "notional_value_dollars": raw.get("notional_value_dollars"),
            "last_price_dollars": raw.get("last_price_dollars"),
            "yes_bid_dollars": raw.get("yes_bid_dollars"),
            "yes_ask_dollars": raw.get("yes_ask_dollars"),
            "volume_fp": raw.get("volume_fp"),
            "open_interest_fp": raw.get("open_interest_fp"),
            "close_time": raw.get("close_time"),
            "settlement_ts": raw.get("settlement_ts"),
        },
    )
