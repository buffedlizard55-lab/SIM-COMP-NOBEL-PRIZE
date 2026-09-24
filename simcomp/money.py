"""Decimal helpers. Kalshi dollar strings are kept exact; no binary floats."""

from __future__ import annotations

from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

CENT = Decimal("0.01")
DOLLAR_QUANT = Decimal("0.0001")
FEE_COEFFICIENT = Decimal("0.07")
ONE = Decimal("1")
ZERO = Decimal("0")


def D(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None or value == "":
        raise ValueError("missing decimal")
    return Decimal(str(value))


def money(value) -> str:
    return str(D(value).quantize(DOLLAR_QUANT, rounding=ROUND_HALF_UP))


def dollars_or_none(value):
    if value is None or value == "":
        return None
    try:
        return D(value)
    except Exception:
        return None


def usable_quote(value) -> bool:
    """A tradable quote is strictly inside (0, 1). Zero is an empty book, not a price."""
    return value is not None and ZERO < value < ONE


def taker_fee(multiplier, quantity: int, price: Decimal) -> Decimal:
    """Quadratic taker fee, rounded up to the next cent.

    Official schedule page https://kalshi.com/fee-schedule (retrieved 2026-09-24)
    lists most markets at fee multiplier 1 with a taker fee range of $0.07–$1.75
    per 100 contracts. fee = round_up_cent(multiplier × 0.07 × C × P × (1−P))
    reproduces that range at a 1-cent price and at 50 cents. The market payload
    itself only carries fee_type and fee_multiplier, not the 0.07 coefficient.
    Callers must record that this is an interpretation of the schedule page.
    """
    mult = D(multiplier)
    if quantity <= 0 or mult <= 0 or not usable_quote(price):
        return ZERO
    raw = mult * FEE_COEFFICIENT * Decimal(quantity) * price * (ONE - price)
    return raw.quantize(CENT, rounding=ROUND_CEILING)


def parse_unix(value):
    """Parse a Kalshi timestamp into unix seconds. None if absent. No guessing."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = int(value)
        if number > 10_000_000_000:  # milliseconds
            return number // 1000
        return number
    text = str(value).strip()
    if text.isdigit():
        number = int(text)
        return number // 1000 if number > 10_000_000_000 else number
    from datetime import datetime, timezone

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def unix_to_iso(ts) -> str:
    if ts is None:
        return ""
    from datetime import datetime, timezone

    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
