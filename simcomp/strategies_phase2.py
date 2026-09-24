"""Phase-2 research strategies (batches 011-020).

Rules of this module
--------------------
* A strategy reads only the DecisionView: this market's candle and bounded prior
  window, its own simulated position and cash, and the optional decision-time
  channels in simcomp/context.py (event quotes, settled pool, schedule). No
  result, no settlement time of the market being decided, no later candle.
* All arithmetic that can change a decision is Decimal (ln, exp, sqrt are
  correctly rounded by the decimal module), so a replay on another machine
  makes the same decisions. No binary floats in a decision path.
* Memory (``self._state``) is built only from views already shown in the
  current run and is cleared by ``reset()`` before every universe and replay.
* Unless a family is about exits or sizing, a phase-2 strategy enters at most
  once per market and holds to settlement. That keeps "what triggered the entry"
  separate from "how the position was managed", which is batch 018's topic.
* Every buy/sell carries a short note code (ledger) and a reason string (the
  numbers the decision used), so a row can be re-derived from stored candles.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal, localcontext

from simcomp.context import reference_of
from simcomp.money import FEE_COEFFICIENT, ONE, ZERO, usable_quote
from simcomp.strategies import Decision, Intent, Strategy, _spread_ok

HALF = Decimal("0.5")
HOUR = 3600
DAY = 86400

# ---------------------------------------------------------------------------
# Deterministic Decimal math with caches
# ---------------------------------------------------------------------------

_LOGIT: dict = {}
_EXP: dict = {}


def dlogit(p: Decimal) -> Decimal:
    cached = _LOGIT.get(p)
    if cached is None:
        with localcontext() as ctx:
            ctx.prec = 28
            cached = (p / (ONE - p)).ln()
        _LOGIT[p] = cached
    return cached


def dexp(x: Decimal) -> Decimal:
    cached = _EXP.get(x)
    if cached is None:
        with localcontext() as ctx:
            ctx.prec = 28
            cached = x.exp()
        _EXP[x] = cached
    return cached


def dsigmoid(x: Decimal) -> Decimal:
    x = x.quantize(Decimal("0.000001"))  # bounded cache, deterministic rounding
    return ONE / (ONE + dexp(-x))


def logit_model(p: Decimal, k: Decimal) -> Decimal:
    """q = sigmoid(k * logit(p)). k > 1 pushes prices toward 0/1 (favorite-longshot reading)."""
    return dsigmoid(k * dlogit(p))


def prelec_inverse(p: Decimal, alpha: Decimal) -> Decimal:
    """Invert Prelec (1998) w(t) = exp(-(-ln t)^alpha): t = exp(-(-ln p)^(1/alpha))."""
    with localcontext() as ctx:
        ctx.prec = 28
        inner = -(p.ln())
        power = (inner.ln() / alpha).exp()  # inner ** (1/alpha)
        return (-power).exp()


def dsqrt(x: Decimal) -> Decimal:
    if x <= 0:
        return ZERO
    with localcontext() as ctx:
        ctx.prec = 28
        return x.sqrt()


def fee_per_contract(price: Decimal) -> Decimal:
    """Same quadratic reading as money.taker_fee, per contract and unrounded."""
    return FEE_COEFFICIENT * price * (ONE - price)


def hash_unit(*parts) -> Decimal:
    """Deterministic uniform in [0, 1) from SHA-256 of the parts. Not a skill signal."""
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return Decimal(int(digest[:12], 16)) / Decimal(16 ** 12)


def ref(candle):
    return reference_of(candle)


def mid(candle):
    if usable_quote(candle.yes_bid_close) and usable_quote(candle.yes_ask_close):
        return (candle.yes_bid_close + candle.yes_ask_close) / 2
    return None


def refs_window(prior, n):
    """Last n prior reference prices, or None if the window is short or any is missing."""
    if len(prior) < n:
        return None
    out = []
    for candle in prior[-n:]:
        value = reference_of(candle)
        if value is None:
            return None
        out.append(value)
    return out


def median(values):
    ordered = sorted(values)
    return ordered[(len(ordered) - 1) // 2]


def mean(values):
    return sum(values) / Decimal(len(values))


def stdev(values):
    m = mean(values)
    return dsqrt(sum((v - m) * (v - m) for v in values) / Decimal(len(values)))


# ---------------------------------------------------------------------------
# Base classes
# ---------------------------------------------------------------------------


class Phase2(Strategy):
    """Shared helpers. ``required_prior`` lets the registry refuse a window overrun."""

    entry_note = "enter"

    def required_prior(self) -> int:
        return 1

    def p(self, key, default=None):
        return self.parameters.get(key, default)

    def num(self, key, ctx, default=None):
        if key not in self.parameters:
            return None if default is None else ctx.decimal(default)
        return self._num(key, ctx)

    def spread_ok(self, ctx) -> bool:
        if "max_spread" not in self.parameters:
            return True
        return _spread_ok(ctx.candle, self._num("max_spread", ctx))

    def quantity(self, ctx, side):
        return None  # engine size rule

    def buy(self, ctx, side, reason, note=None):
        return Decision(intents=[Intent("buy", side, self.quantity(ctx, side), reason=reason)],
                        note=note or self.entry_note)


class SingleEntry(Phase2):
    """Enter at most once per market, hold to settlement."""

    def signal(self, ctx):  # -> str note | (side, reason)
        raise NotImplementedError

    def decide(self, ctx) -> Decision:
        if ctx.position.qty or ctx.ever_traded:
            return Decision(note="single entry used")
        out = self.signal(ctx)
        if isinstance(out, str):
            return Decision(note=out)
        side, reason = out
        if not self.spread_ok(ctx):
            return Decision(note="spread outside cap or missing")
        return self.buy(ctx, side, reason)


# ---------------------------------------------------------------------------
# Reusable entry rules (used by gates, sizing, exits, ablations)
# ---------------------------------------------------------------------------


def entry_rule(name, ctx, params, num):
    """Named entry rules shared by several families. Returns note | (side, reason)."""
    candle = ctx.candle
    if name == "fav":
        ask = candle.yes_ask_close
        lo = num("fav_lo", ctx, "0.65")
        hi = num("fav_hi", ctx, "0.92")
        if not usable_quote(ask):
            return "no usable yes ask"
        if ask < lo or ask > hi:
            return "yes ask outside favorite band"
        return "yes", f"yes ask {ask} in favorite band {lo}-{hi}"
    if name == "longshot_yes":
        ask = candle.yes_ask_close
        if not usable_quote(ask):
            return "no usable yes ask"
        if ask < Decimal("0.04") or ask > Decimal("0.18"):
            return "yes ask outside longshot band"
        return "yes", f"yes ask {ask} in longshot band 0.04-0.18"
    if name == "longshot_no":
        ask = candle.yes_ask_close
        cap = num("ls_cap", ctx, "0.15")
        if not usable_quote(ask):
            return "no usable yes ask"
        if ask > cap:
            return "yes ask above longshot cap"
        return "no", f"yes ask {ask} <= longshot cap {cap}; buy NO"
    if name == "momentum":
        if not ctx.prior:
            return "no prior candle"
        now, before = ref(candle), ref(ctx.prior[-1])
        if now is None or before is None:
            return "no reference price"
        move = now - before
        threshold = num("mom", ctx, "0.03")
        if abs(move) < threshold:
            return "move below threshold"
        return ("yes" if move > 0 else "no"), f"reference {before} -> {now} (move {move}) >= {threshold}"
    if name == "logit":
        m = mid(candle)
        if m is None:
            return "no two-sided book"
        k = num("k", ctx, "1.25")
        edge = num("edge", ctx, "0.02")
        q = logit_model(m, k)
        if q - candle.yes_ask_close >= edge:
            return "yes", f"logit model q={q:.4f} (k={k}, mid {m}) - ask {candle.yes_ask_close} >= {edge}"
        if candle.yes_bid_close - q >= edge:
            return "no", f"yes bid {candle.yes_bid_close} - logit model q={q:.4f} (k={k}) >= {edge}; buy NO"
        return "model edge below threshold"
    raise ValueError(f"unknown entry rule {name}")


# ---------------------------------------------------------------------------
# Batch 011: event structure
# ---------------------------------------------------------------------------


class EventStructure(SingleEntry):
    """Rules that read the other stored contracts of the same Kalshi event."""

    id = "event_structure"
    name = "Event structure"
    summary = "Reads sibling contracts' closes at or before the decision time (ctx.event)."
    parameters = {"mode": "normalized"}
    entry_note = "event_entry"

    def _quotes(self, ctx):
        event = ctx.event
        if event is None:
            return None, "no event channel"
        stale = int(self.p("max_stale_h", 48)) * HOUR
        quotes = [q for q in event.quotes if ctx.as_of_ts - q.end_ts <= stale]
        if len(quotes) < int(self.p("min_n", 3)):
            return None, "too few fresh sibling quotes"
        return quotes, ""

    def _ranked(self, quotes):
        with_mid = [(q.mid, q.ticker, q) for q in quotes if q.mid is not None]
        with_mid.sort(key=lambda item: (-item[0], item[1]))
        return with_mid

    def _event_state(self, ctx, key_value):
        """(previous value, current value) for this event, independent of visit order."""
        event = ctx.event.event_ticker
        state = self._state.setdefault(("event", event), {"prev": None, "cur_ts": None, "cur": None})
        if state["cur_ts"] != ctx.as_of_ts:
            state["prev"] = state["cur"]
            state["cur_ts"] = ctx.as_of_ts
            state["cur"] = key_value
        return state["prev"], state["cur"]

    def signal(self, ctx):
        quotes, note = self._quotes(ctx)
        if quotes is None:
            return note
        mode = self.p("mode")
        me = ctx.market.ticker
        own = next((q for q in quotes if q.ticker == me), None)
        if own is None:
            return "own quote not in event view"
        candle = ctx.candle
        ranked = self._ranked(quotes)
        mids = [item[0] for item in ranked]
        mass = sum(mids) if mids else ZERO
        if mode == "normalized":
            lo, hi = self._num("mass_lo", ctx), self._num("mass_hi", ctx)
            if not mids or mass < lo or mass > hi:
                return "event mass outside sanity gate"
            if own.mid is None:
                return "no own mid"
            fair = own.mid / mass
            edge = self._num("edge", ctx)
            if usable_quote(candle.yes_ask_close) and fair - candle.yes_ask_close >= edge:
                return "yes", f"normalized {own.mid}/{mass}={fair:.4f} - ask {candle.yes_ask_close} >= {edge}"
            if self.p("sides") == "both" and usable_quote(candle.yes_bid_close) and candle.yes_bid_close - fair >= edge:
                return "no", f"bid {candle.yes_bid_close} - normalized {fair:.4f} >= {edge}; buy NO"
            return "no normalized edge"
        if mode == "overround_no":
            bids = [q.yes_bid for q in quotes if q.yes_bid is not None]
            total = sum(bids) if bids else ZERO
            margin = self._num("margin", ctx)
            if total < ONE + margin:
                return "sum of yes bids below 1 + margin"
            if not usable_quote(candle.yes_ask_close) or candle.yes_ask_close > self._num("max_leg_ask", ctx):
                return "leg yes ask above cap"
            return "no", f"sum of {len(bids)} yes bids {total} >= 1 + {margin}; leg ask {candle.yes_ask_close}; buy NO"
        if mode == "underround_yes":
            if ctx.event.mutually_exclusive is not True:
                return "event not mutually exclusive"
            asks = [q.yes_ask for q in quotes]
            if any(a is None for a in asks):
                return "a leg has no ask"
            if mass < self._num("mass_lo", ctx):
                return "event mass below gate; stored field looks partial"
            total = sum(asks)
            if total > ONE - self._num("margin", ctx):
                return "sum of yes asks above 1 - margin"
            return "yes", f"mutually exclusive event; sum of {len(asks)} asks {total} <= 1 - {self.parameters['margin']}"
        if not ranked:
            return "no sibling mids"
        rank = next((i + 1 for i, item in enumerate(ranked) if item[1] == me), None)
        if rank is None:
            return "own contract has no mid"
        if mode == "leader":
            if rank != 1:
                return f"rank {rank} is not the event leader"
            lead = ranked[0][0] - (ranked[1][0] if len(ranked) > 1 else ZERO)
            if ranked[0][0] < self._num("min_mid", ctx) or ranked[0][0] > Decimal("0.95"):
                return "leader mid outside band"
            if lead < self._num("gap", ctx):
                return "leader margin below gap"
            return "yes", f"event leader mid {ranked[0][0]} leads #2 by {lead} >= {self.parameters['gap']}"
        if mode == "rank_k":
            if rank != int(self.p("k")):
                return f"rank {rank} is not {self.p('k')}"
            if not usable_quote(candle.yes_ask_close) or candle.yes_ask_close > self._num("cap", ctx):
                return "ask above cap"
            return "yes", f"event rank {rank} with ask {candle.yes_ask_close} <= {self.parameters['cap']}"
        if mode == "field_no":
            if rank < int(self.p("k")):
                return f"rank {rank} is inside the top {int(self.p('k')) - 1}"
            if not usable_quote(candle.yes_ask_close) or candle.yes_ask_close > self._num("cap", ctx):
                return "leg ask above cap"
            return "no", f"event rank {rank} >= {self.p('k')}; yes ask {candle.yes_ask_close} <= {self.parameters['cap']}; buy NO"
        if mode == "concentration":
            if rank != 1 or mass <= 0:
                return "not the leader"
            hhi = sum((m / mass) * (m / mass) for m in mids)
            h = self._num("h", ctx)
            ok = hhi >= h if self.p("dir") == "high" else hhi <= h
            if not ok:
                return "concentration gate not met"
            return "yes", f"leader with HHI {hhi:.4f} {'>=' if self.p('dir') == 'high' else '<='} {h}"
        if mode == "leader_change":
            prev, cur = self._event_state(ctx, ranked[0][1])
            if prev is None or prev == cur:
                return "no leader change"
            if rank != 1:
                return "not the new leader"
            lead = ranked[0][0] - (ranked[1][0] if len(ranked) > 1 else ZERO)
            if ranked[0][0] < self._num("min_mid", ctx) or lead < self._num("gap", ctx):
                return "new leader too weak"
            return "yes", f"leader changed {prev} -> {cur}; mid {ranked[0][0]}, lead {lead}"
        if mode == "rotation":
            prev_mass, _cur = self._event_state(ctx, mass)
            if prev_mass is None or not ctx.prior:
                return "no previous event mass"
            before = ref(ctx.prior[-1])
            now = ref(candle)
            if before is None or now is None:
                return "no reference price"
            move = now - before
            if abs(move) < self._num("m", ctx):
                return "own move below threshold"
            if abs(mass - prev_mass) > self._num("x", ctx):
                return "whole event repriced; not a rotation"
            return ("yes" if move > 0 else "no"), f"own move {move} with event mass {prev_mass} -> {mass} (rotation)"
        raise ValueError(f"unknown event mode {mode}")


# ---------------------------------------------------------------------------
# Batch 012: calibration priors from the literature (no fitting)
# ---------------------------------------------------------------------------


class CalibrationPrior(SingleEntry):
    id = "calibration_prior"
    name = "Literature calibration prior"
    summary = "Maps the closing mid to a model probability with a fixed, predeclared curve."
    parameters = {"mode": "logit", "k": "1.25", "edge": "0.02", "sides": "both"}
    entry_note = "calibration_entry"

    def signal(self, ctx):
        candle = ctx.candle
        mode = self.p("mode")
        if mode == "longshot_no":
            ask = candle.yes_ask_close
            if not usable_quote(ask) or ask > self._num("cap", ctx):
                return "yes ask above longshot cap"
            return "no", f"yes ask {ask} <= {self.parameters['cap']}; buy NO against the longshot"
        if mode == "high_favorite":
            ask = candle.yes_ask_close
            if not usable_quote(ask) or ask < self._num("lo", ctx) or ask > Decimal("0.99"):
                return "yes ask outside high-favorite band"
            return "yes", f"yes ask {ask} in {self.parameters['lo']}-0.99"
        m = mid(candle)
        if m is None:
            return "no two-sided book"
        if mode in ("logit", "fee_aware"):
            q = logit_model(m, self._num("k", ctx))
        elif mode == "prelec":
            q = prelec_inverse(m, self._num("alpha", ctx))
        else:
            raise ValueError(mode)
        edge = self._num("edge", ctx)
        ask, bid = candle.yes_ask_close, candle.yes_bid_close
        yes_hurdle = edge + (fee_per_contract(ask) if mode == "fee_aware" else ZERO)
        no_hurdle = edge + (fee_per_contract(ONE - bid) if mode == "fee_aware" else ZERO)
        sides = self.p("sides", "both")
        if sides in ("both", "yes") and q - ask >= yes_hurdle:
            return "yes", f"{mode} q={q:.4f} from mid {m} - ask {ask} >= {yes_hurdle:.4f}"
        if sides in ("both", "no") and bid - q >= no_hurdle:
            return "no", f"bid {bid} - {mode} q={q:.4f} >= {no_hurdle:.4f}; buy NO"
        return "model edge below hurdle"


# ---------------------------------------------------------------------------
# Batch 013: walk-forward learning from settled results
# ---------------------------------------------------------------------------


def pool_records(ctx, scope):
    settled = ctx.settled
    if settled is None:
        return None
    if scope == "series":
        key = ctx.market.series_ticker
        return tuple(r for r in settled.records if r.series_ticker == key)
    if scope == "category":
        key = getattr(ctx.market, "category", "")
        return tuple(r for r in settled.records if key and r.category == key)
    return settled.records


_LEARN_CACHE: dict = {}
_LOGLIK: dict = {}


def _loglik_terms(p: Decimal, k: Decimal):
    key = (p, k)
    cached = _LOGLIK.get(key)
    if cached is None:
        q = logit_model(p, k)
        q = min(max(q, Decimal("0.000001")), Decimal("0.999999"))
        with localcontext() as c:
            c.prec = 28
            cached = (q.ln(), (ONE - q).ln())
        _LOGLIK[key] = cached
    return cached


class PoolLearner(SingleEntry):
    """Learns only from markets whose official result settled strictly before T."""

    id = "pool_learner"
    name = "Walk-forward learner"
    summary = "Calibration or base rates estimated from the settled pool available at T."
    parameters = {"mode": "bucket", "scope": "series"}
    entry_note = "learned_entry"

    def _cached(self, ctx, label, builder):
        """Tables are pure functions of (pool contents, scope, label), so they are
        shared across instances. The key fingerprints the pool by its size and its
        latest record, which identifies the prefix of the settlement-ordered pool."""
        scope = self.p("scope", "all")
        if scope == "series":
            scope_key = ctx.market.series_ticker
        elif scope == "category":
            scope_key = getattr(ctx.market, "category", "")
        else:
            scope_key = ""
        records_all = ctx.settled.records if ctx.settled is not None else ()
        last = records_all[-1] if records_all else None
        fingerprint = (len(records_all), last.ticker if last else "", last.settlement_ts if last else 0)
        key = (fingerprint, scope, scope_key, label)
        cached = _LEARN_CACHE.get(key)
        if cached is None:
            if len(_LEARN_CACHE) > 20000:
                _LEARN_CACHE.clear()
            cached = builder(pool_records(ctx, scope) or ())
            _LEARN_CACHE[key] = cached
        return cached

    def _bucket_table(self, records, width, age_split=None):
        table: dict = {}
        for record in records:
            if not record.pairs:
                continue
            weight = ONE / Decimal(len(record.pairs))
            y = ONE if record.result == "yes" else ZERO
            seen = set()
            for end_ts, price in record.pairs:
                bucket = int(price / width)
                if age_split is not None and record.open_time is not None:
                    bucket = (bucket, 1 if (end_ts - record.open_time) >= age_split else 0)
                cell = table.setdefault(bucket, [ZERO, ZERO, 0])
                cell[0] += weight * y
                cell[1] += weight
                if bucket not in seen:
                    cell[2] += 1
                    seen.add(bucket)
        return table

    def _decide_against(self, ctx, q, label):
        candle = ctx.candle
        edge = self._num("edge", ctx)
        sides = self.p("sides", "both")
        if sides in ("both", "yes") and usable_quote(candle.yes_ask_close) and q - candle.yes_ask_close >= edge:
            return "yes", f"{label} q={q:.4f} - ask {candle.yes_ask_close} >= {edge}"
        if sides in ("both", "no") and usable_quote(candle.yes_bid_close) and candle.yes_bid_close - q >= edge:
            return "no", f"bid {candle.yes_bid_close} - {label} q={q:.4f} >= {edge}; buy NO"
        return "learned edge below threshold"

    def signal(self, ctx):
        if ctx.settled is None:
            return "no settled-pool channel"
        mode = self.p("mode")
        candle = ctx.candle
        if mode == "uniform_prior":
            if ctx.event is None or ctx.event.stored_markets < 2:
                return "no event field"
            m = mid(candle)
            if m is None:
                return "no two-sided book"
            w = self._num("w", ctx)
            q = w / Decimal(ctx.event.stored_markets) + (ONE - w) * m
            return self._decide_against(ctx, q, f"uniform prior 1/{ctx.event.stored_markets} blend")
        if mode in ("bucket", "age_bucket"):
            width = self._num("width", ctx)
            split = int(self.p("age_split_d", 0)) * DAY if mode == "age_bucket" else None
            table = self._cached(ctx, f"{mode}:{width}:{split}", lambda recs: self._bucket_table(recs, width, split))
            m = mid(candle)
            if m is None:
                return "no two-sided book"
            bucket = int(m / width)
            if split is not None:
                if ctx.market.open_time is None:
                    return "no open time"
                bucket = (bucket, 1 if (ctx.as_of_ts - ctx.market.open_time) >= split else 0)
            cell = table.get(bucket)
            if not cell or cell[2] < int(self.p("min_n", 5)):
                return "too few settled markets in this price bucket"
            strength = self.num("prior", ctx, "2")
            q = (cell[0] + strength * m) / (cell[1] + strength)
            return self._decide_against(ctx, q, f"bucket {bucket} ({cell[2]} markets)")
        if mode in ("base_rate", "recency_rate"):
            def build(records):
                return tuple(1 if r.result == "yes" else 0 for r in records)  # already settlement-ordered
            outcomes = self._cached(ctx, "outcomes", build)
            if len(outcomes) < int(self.p("min_n", 5)):
                return "too few settled markets for a base rate"
            if mode == "base_rate":
                q = Decimal(sum(outcomes)) / Decimal(len(outcomes))
                label = f"base rate {sum(outcomes)}/{len(outcomes)}"
            else:
                half = Decimal(str(self.p("half_life")))
                num_, den = ZERO, ZERO
                for age, y in enumerate(reversed(outcomes)):
                    weight = dexp(-(Decimal(age) / half) * Decimal("0.6931471805599453094172321215"))
                    num_ += weight * y
                    den += weight
                q = num_ / den
                label = f"recency-weighted rate (half-life {half})"
            return self._decide_against(ctx, q, label)
        if mode == "fitted_slope":
            k = self._cached(ctx, "slope", self._fit_slope)
            if k is None:
                return "too few settled price observations to fit"
            if abs(k - ONE) < Decimal("0.1"):
                return f"fitted slope {k} ~ 1; no calibration edge claimed"
            m = mid(candle)
            if m is None:
                return "no two-sided book"
            return self._decide_against(ctx, logit_model(m, k), f"fitted slope k={k}")
        raise ValueError(mode)

    def _fit_slope(self, records):
        """Grid MLE of k in q = sigmoid(k logit p) on settled pairs (market-weighted)."""
        cells: dict = {}
        count = 0
        for record in records:
            if not record.pairs:
                continue
            weight = ONE / Decimal(len(record.pairs))
            y = record.result == "yes"
            for _ts, price in record.pairs:
                p = price.quantize(Decimal("0.005"))
                if p <= 0 or p >= 1:
                    continue
                cell = cells.setdefault(p, [ZERO, ZERO])
                cell[0 if y else 1] += weight
                count += 1
        if count < int(self.p("min_pairs", 30)):
            return None
        best_k, best_ll = None, None
        for step in range(5, 31):  # k = 0.5 .. 3.0 in 0.1 steps
            k = Decimal(step) / Decimal(10)
            ll = ZERO
            for p, (w_yes, w_no) in cells.items():
                ln_q, ln_not_q = _loglik_terms(p, k)
                ll += w_yes * ln_q + w_no * ln_not_q
            if best_ll is None or ll > best_ll:
                best_k, best_ll = k, ll
        return best_k


# ---------------------------------------------------------------------------
# Batch 014: time, age, and schedule gates
# ---------------------------------------------------------------------------


class GatedEntry(SingleEntry):
    """A named entry rule behind a decision-time gate (age, horizon, clock)."""

    id = "gated_entry"
    name = "Gated entry"
    summary = "Entry rule applies only when a time gate holds at the decision candle."
    parameters = {"gate": "age_ge", "entry": "fav"}
    entry_note = "gated_entry"

    def gate(self, ctx):
        gate = self.p("gate")
        t = ctx.as_of_ts
        if gate in ("age_ge", "age_le"):
            if ctx.market.open_time is None:
                return "no open time"
            age_h = Decimal(t - ctx.market.open_time) / Decimal(HOUR)
            limit = self._num("hours", ctx)
            ok = age_h >= limit if gate == "age_ge" else age_h <= limit
            return "" if ok else f"market age {age_h:.1f}h fails {gate} {limit}h"
        if gate in ("horizon_le", "horizon_ge"):
            schedule = ctx.schedule
            if schedule is None or schedule.close_ts is None:
                return "no scheduled close published for this event"
            left_h = Decimal(schedule.close_ts - t) / Decimal(HOUR)
            if left_h <= 0:
                return "scheduled close already passed"
            limit = self._num("hours", ctx)
            ok = left_h <= limit if gate == "horizon_le" else left_h >= limit
            return "" if ok else f"{left_h:.1f}h to scheduled close fails {gate} {limit}h"
        if gate == "utc_hour":
            hour = (t % DAY) // HOUR
            lo, hi = int(self.p("h_lo")), int(self.p("h_hi"))
            return "" if lo <= hour < hi else f"UTC hour {hour} outside {lo}-{hi}"
        if gate == "weekday":
            weekday = ((t // DAY) + 3) % 7  # 1970-01-01 was a Thursday; Monday = 0
            weekend = weekday >= 5
            want = self.p("days") == "weekend"
            return "" if weekend == want else "day-of-week gate not met"
        raise ValueError(gate)

    def signal(self, ctx):
        blocked = self.gate(ctx)
        if blocked:
            return blocked
        out = entry_rule(self.p("entry"), ctx, self.parameters, self.num)
        if isinstance(out, str):
            return out
        side, reason = out
        return side, f"{self.p('gate')} gate passed; {reason}"


class PreCloseExit(Phase2):
    """Favorite entry, then sell before the scheduled close."""

    id = "pre_close_exit"
    name = "Exit before the scheduled close"
    summary = "Enter a favorite; sell when the scheduled close is within the horizon."
    parameters = {"hours": "24", "fav_lo": "0.65", "max_spread": "0.08"}

    def decide(self, ctx):
        schedule = ctx.schedule
        if ctx.position.qty and ctx.position.side == "yes":
            if schedule is None or schedule.close_ts is None:
                return Decision(note="hold: no schedule")
            left = schedule.close_ts - ctx.as_of_ts
            if left <= int(Decimal(self.p("hours")) * HOUR):
                return Decision(intents=[Intent("sell", "yes", ctx.position.qty, reason=(
                    f"{left / HOUR:.1f}h to scheduled close <= {self.p('hours')}h"))], note="pre_close_exit")
            return Decision(note="hold: before exit horizon")
        if ctx.ever_traded:
            return Decision(note="single entry used")
        if schedule is None or schedule.close_ts is None:
            return Decision(note="no scheduled close published for this event")
        if schedule.close_ts - ctx.as_of_ts <= int(Decimal(self.p("hours")) * HOUR):
            return Decision(note="already inside the exit horizon")
        out = entry_rule("fav", ctx, self.parameters, self.num)
        if isinstance(out, str):
            return Decision(note=out)
        if not self.spread_ok(ctx):
            return Decision(note="spread outside cap or missing")
        return self.buy(ctx, out[0], out[1], note="enter_pre_close")


# ---------------------------------------------------------------------------
# Batch 015: liquidity, volume, open interest
# ---------------------------------------------------------------------------


class ActivitySignal(SingleEntry):
    id = "activity_signal"
    name = "Volume / open-interest signal"
    summary = "Entries conditioned on candle volume, open interest, trade prints, and spread changes."
    parameters = {"mode": "oi_follow"}
    entry_note = "activity_entry"

    def required_prior(self) -> int:
        return int(self.p("w", self.p("n", 1)))

    def signal(self, ctx):
        mode = self.p("mode")
        candle, prior = ctx.candle, ctx.prior
        if mode in ("oi_follow", "oi_fade"):
            w = int(self.p("w"))
            if len(prior) < w:
                return "not enough prior candles"
            then = prior[-w]
            if candle.open_interest is None or then.open_interest is None:
                return "open interest missing"
            base = then.open_interest if then.open_interest > 0 else ONE
            growth = (candle.open_interest - then.open_interest) / base
            now_ref, then_ref = ref(candle), ref(then)
            if now_ref is None or then_ref is None:
                return "no reference price"
            move = now_ref - then_ref
            if abs(move) < self._num("m", ctx):
                return "price move below threshold"
            g = self._num("g", ctx)
            if mode == "oi_follow":
                if growth < g:
                    return "open interest growth below threshold"
                return ("yes" if move > 0 else "no"), f"OI growth {growth:.3f} >= {g} with move {move}; follow"
            if growth > -g:
                return "open interest did not fall enough"
            return ("no" if move > 0 else "yes"), f"OI change {growth:.3f} <= -{g} with move {move}; fade"
        if mode in ("spike_follow", "spike_fade"):
            w = int(self.p("w"))
            if len(prior) < w:
                return "not enough prior candles"
            vols = [c.volume for c in prior[-w:]]
            if candle.volume is None or any(v is None for v in vols):
                return "volume missing"
            threshold = self._num("k", ctx) * max(median(vols), ONE)
            if candle.volume < threshold:
                return "no volume spike"
            now_ref, before = ref(candle), ref(prior[-1])
            if now_ref is None or before is None:
                return "no reference price"
            move = now_ref - before
            if abs(move) < self._num("m", ctx):
                return "spike without a price move"
            follow = mode == "spike_follow"
            side = ("yes" if move > 0 else "no") if follow else ("no" if move > 0 else "yes")
            return side, f"volume {candle.volume} >= {threshold} with move {move}; {'follow' if follow else 'fade'}"
        if mode == "dormant":
            n = int(self.p("n"))
            if len(prior) < n:
                return "not enough prior candles"
            if any(c.volume is None or c.volume != 0 for c in prior[-n:]):
                return "not dormant"
            if candle.volume is None or candle.volume <= 0:
                return "still no volume"
            now_ref, before = ref(candle), ref(prior[-1])
            if now_ref is None or before is None:
                return "no reference price"
            move = now_ref - before
            if move == 0 or abs(move) < self._num("m", ctx):
                return "awakening without a direction"
            return ("yes" if move > 0 else "no"), f"first volume after {n} dormant candles; move {move}"
        if mode in ("liquid", "illiquid"):
            vols = [c.volume for c in prior if c.volume is not None]
            recent = sum(vols) if vols else ZERO
            limit = self._num("v", ctx)
            if mode == "liquid":
                oi = candle.open_interest or ZERO
                if recent < limit or oi < self.num("oi", ctx, "0"):
                    return "recent volume or open interest below liquidity gate"
            elif recent > limit:
                return "recent volume above illiquidity gate"
            out = entry_rule(self.p("entry", "fav"), ctx, self.parameters, self.num)
            if isinstance(out, str):
                return out
            return out[0], f"recent volume {recent} passes {mode} gate {limit}; {out[1]}"
        if mode == "spread_compression":
            w = int(self.p("w"))
            if len(prior) < w:
                return "not enough prior candles"
            spreads = [c.spread for c in prior[-w:]]
            if candle.spread is None or any(s is None for s in spreads):
                return "spread missing"
            drop = mean(spreads) - candle.spread
            if drop < self._num("x", ctx):
                return "spread did not compress"
            now_ref, before = ref(candle), ref(prior[-1])
            if now_ref is None or before is None or now_ref == before:
                return "no direction"
            return ("yes" if now_ref > before else "no"), f"spread compressed by {drop} vs {w}-candle mean; follow move"
        if mode == "stale_quote":
            n = int(self.p("n"))
            if len(prior) < n:
                return "not enough prior candles"
            window = list(prior[-n:]) + [candle]
            if any(usable_quote(c.trade_close) for c in window):
                return "trades printed; quote not stale"
            first, last = mid(prior[-n]), mid(candle)
            if first is None or last is None:
                return "no mid"
            move = last - first
            if abs(move) < self._num("m", ctx):
                return "quote move below threshold"
            return ("yes" if move > 0 else "no"), f"no trade print for {n + 1} candles; mid moved {move}"
        if mode == "turnover_fade":
            if candle.volume is None or candle.open_interest is None or not prior:
                return "volume or open interest missing"
            ratio = candle.volume / max(candle.open_interest, ONE)
            if ratio < self._num("r", ctx):
                return "turnover below threshold"
            now_ref, before = ref(candle), ref(prior[-1])
            if now_ref is None or before is None:
                return "no reference price"
            move = now_ref - before
            if abs(move) < self._num("m", ctx):
                return "move below threshold"
            return ("no" if move > 0 else "yes"), f"turnover {ratio:.3f} >= {self.p('r')} with move {move}; fade"
        raise ValueError(mode)


# ---------------------------------------------------------------------------
# Batch 016: trend and reversal constructions (single entry)
# ---------------------------------------------------------------------------


class TrendSignal(SingleEntry):
    id = "trend_signal"
    name = "Trend / reversal construction"
    summary = "Moving-average, time-series momentum, big-move, RSI, band, run, range and dip rules."
    parameters = {"mode": "tsmom"}
    entry_note = "trend_entry"

    def required_prior(self) -> int:
        mode = self.p("mode")
        if mode == "ma_cross":
            return int(self.p("long")) + 1
        if mode in ("run_follow", "run_fade"):
            return int(self.p("n"))
        if mode == "big_move":
            return 1
        return int(self.p("w", 1))

    def signal(self, ctx):
        mode = self.p("mode")
        candle, prior = ctx.candle, ctx.prior
        now = ref(candle)
        if now is None:
            return "no reference price"
        if mode == "ma_cross":
            short, long_ = int(self.p("short")), int(self.p("long"))
            window = refs_window(prior, long_ + 1)
            if window is None:
                return "not enough reference prices"
            series = window + [now]
            s_now, l_now = mean(series[-short:]), mean(series[-long_:])
            s_prev, l_prev = mean(series[-short - 1:-1]), mean(series[-long_ - 1:-1])
            gap = self._num("gap", ctx)
            if s_prev <= l_prev and s_now - l_now >= gap:
                return "yes", f"MA{short} {s_now:.4f} crossed above MA{long_} {l_now:.4f} by >= {gap}"
            if s_prev >= l_prev and l_now - s_now >= gap:
                return "no", f"MA{short} {s_now:.4f} crossed below MA{long_} {l_now:.4f} by >= {gap}"
            return "no crossover"
        if mode == "tsmom":
            w = int(self.p("w"))
            window = refs_window(prior, w)
            if window is None:
                return "not enough reference prices"
            move = now - window[0]
            if abs(move) < self._num("m", ctx):
                return "window move below threshold"
            return ("yes" if move > 0 else "no"), f"{w}-candle move {window[0]} -> {now} ({move}); follow"
        if mode == "big_move":
            before = ref(prior[-1]) if prior else None
            if before is None:
                return "no prior reference"
            move = now - before
            if abs(move) < self._num("m", ctx):
                return "no big move"
            follow = self.p("dir") == "follow"
            side = ("yes" if move > 0 else "no") if follow else ("no" if move > 0 else "yes")
            return side, f"one-candle move {move} >= {self.p('m')}; {self.p('dir')}"
        if mode == "rsi":
            w = int(self.p("w"))
            window = refs_window(prior, w)
            if window is None:
                return "not enough reference prices"
            series = window + [now]
            gains = sum(max(b - a, ZERO) for a, b in zip(series, series[1:]))
            losses = sum(max(a - b, ZERO) for a, b in zip(series, series[1:]))
            if gains + losses == 0:
                return "flat window"
            rsi = Decimal(100) * gains / (gains + losses)
            hi = self._num("hi", ctx)
            if rsi >= hi:
                return "no", f"RSI {rsi:.1f} >= {hi}; fade"
            if rsi <= Decimal(100) - hi:
                return "yes", f"RSI {rsi:.1f} <= {Decimal(100) - hi}; fade"
            return "RSI inside band"
        if mode == "bollinger":
            w = int(self.p("w"))
            window = refs_window(prior, w)
            if window is None:
                return "not enough reference prices"
            m, sd = mean(window), stdev(window)
            if sd == 0:
                return "flat window"
            z = self._num("z", ctx)
            if now <= m - z * sd:
                return "yes", f"reference {now} <= mean {m:.4f} - {z}*sd {sd:.4f}; revert"
            if now >= m + z * sd:
                return "no", f"reference {now} >= mean {m:.4f} + {z}*sd {sd:.4f}; revert"
            return "inside band"
        if mode in ("run_follow", "run_fade"):
            n = int(self.p("n"))
            window = refs_window(prior, n)
            if window is None:
                return "not enough reference prices"
            series = window + [now]
            moves = [b - a for a, b in zip(series, series[1:])]
            if all(mv > 0 for mv in moves):
                up = True
            elif all(mv < 0 for mv in moves):
                up = False
            else:
                return f"no run of {n} moves"
            follow = mode == "run_follow"
            side = ("yes" if up else "no") if follow else ("no" if up else "yes")
            return side, f"{n} consecutive {'up' if up else 'down'} moves; {'follow' if follow else 'fade'}"
        if mode == "range_pos":
            w = int(self.p("w"))
            window = refs_window(prior, w)
            if window is None:
                return "not enough reference prices"
            hi, lo = max(window), min(window)
            if hi == lo:
                return "flat window"
            pos = (now - lo) / (hi - lo)
            revert = self.p("dir") == "revert"
            if pos <= Decimal("0.1"):
                return ("yes" if revert else "no"), f"range position {pos:.3f} <= 0.1 ({self.p('dir')})"
            if pos >= Decimal("0.9"):
                return ("no" if revert else "yes"), f"range position {pos:.3f} >= 0.9 ({self.p('dir')})"
            return "range position in the middle"
        if mode in ("dip", "rally_fade"):
            w = int(self.p("w"))
            window = refs_window(prior, w)
            if window is None:
                return "not enough reference prices"
            d = self._num("d", ctx)
            if mode == "dip":
                drop = max(window) - now
                return ("yes", f"reference {now} is {drop} below window max; buy the dip") if drop >= d else "no dip"
            rise = now - min(window)
            return ("no", f"reference {now} is {rise} above window min; fade the rally") if rise >= d else "no rally"
        raise ValueError(mode)


# ---------------------------------------------------------------------------
# Batch 017: position sizing
# ---------------------------------------------------------------------------


class SizedEntry(SingleEntry):
    """A fixed entry rule with a sizing rule. The engine's caps still bind (and clip)."""

    id = "sized_entry"
    name = "Sizing rule"
    summary = "Same entry, different quantity rule. Engine caps: $100 per fill, $300 per market, 500 contracts."
    parameters = {"entry": "logit", "sizing": "kelly"}
    entry_note = "sized_entry"

    def _price(self, ctx, side):
        candle = ctx.candle
        if side == "yes":
            return candle.yes_ask_close if usable_quote(candle.yes_ask_close) else None
        return (ONE - candle.yes_bid_close) if usable_quote(candle.yes_bid_close) else None

    def signal(self, ctx):
        sizing = self.p("sizing")
        if sizing == "reserve":
            floor = self._num("r", ctx) * Decimal(10000)
            if ctx.cash < floor:
                return f"cash {ctx.cash} below reserve {floor}"
        return entry_rule(self.p("entry"), ctx, self.parameters, self.num)

    def quantity(self, ctx, side):
        sizing = self.p("sizing")
        price = self._price(ctx, side)
        if price is None or price <= 0:
            return None
        if sizing == "fixed":
            return int(self.p("qty"))
        if sizing == "cash_fraction":
            return max(int(self._num("f", ctx) * ctx.cash / price), 1)
        if sizing == "payout":
            return max(int(self._num("x", ctx)), 1)
        if sizing in ("kelly", "edge_scaled"):
            m = mid(ctx.candle)
            if m is None:
                return None
            q = logit_model(m, self.num("k", ctx, "1.25"))
            prob = q if side == "yes" else ONE - q
            edge = prob - price
            if edge <= 0:
                return 1
            if sizing == "kelly":
                fraction = edge / (ONE - price)
                stake = self._num("frac", ctx) * fraction * ctx.cash
                return max(int(stake / price), 1)
            return max(int(self._num("scale", ctx) * edge * Decimal(100)), 1)
        return None  # reserve and anything else: engine default


class LadderEntry(Phase2):
    """Favorite entry plus up to n additional slices (average down or pyramid)."""

    id = "ladder_entry"
    name = "Ladder"
    summary = "Adds slices after entry when the price moves by a step; per-market cap $300 binds."
    parameters = {"dir": "down", "step": "0.05", "adds": 2, "max_spread": "0.08"}

    def decide(self, ctx):
        ticker = ctx.market.ticker
        state = self._state.setdefault(ticker, {"fills": 0, "last_qty": 0})
        if ctx.position.qty > state["last_qty"]:
            state["fills"] += 1
        state["last_qty"] = ctx.position.qty
        candle = ctx.candle
        if ctx.position.qty and ctx.position.side == "yes":
            if state["fills"] - 1 >= int(self.p("adds")):
                return Decision(note="ladder complete; hold")
            step = self._num("step", ctx)
            avg = ctx.position.avg_entry_price
            if self.p("dir") == "down":
                ask = candle.yes_ask_close
                if usable_quote(ask) and ask <= avg - step and self.spread_ok(ctx):
                    return Decision(intents=[Intent("buy", "yes", reason=f"ask {ask} <= avg {avg} - {step}; average down")], note="ladder_add_down")
            else:
                bid, ask = candle.yes_bid_close, candle.yes_ask_close
                if usable_quote(bid) and usable_quote(ask) and bid >= avg + step and self.spread_ok(ctx):
                    return Decision(intents=[Intent("buy", "yes", reason=f"bid {bid} >= avg {avg} + {step}; pyramid")], note="ladder_add_up")
            return Decision(note="hold: no ladder step")
        if ctx.ever_traded:
            return Decision(note="single ladder used")
        out = entry_rule("fav", ctx, self.parameters, self.num)
        if isinstance(out, str):
            return Decision(note=out)
        if not self.spread_ok(ctx):
            return Decision(note="spread outside cap or missing")
        return self.buy(ctx, out[0], out[1], note="ladder_first")


class SplitEntry(Phase2):
    """Time-diversified entry: n equal slices spaced s candles apart while the band holds."""

    id = "split_entry"
    name = "Split entry"
    summary = "Splits the $100 entry into n slices spaced s decision candles apart."
    parameters = {"n": 2, "s": 1, "max_spread": "0.08"}

    def decide(self, ctx):
        ticker = ctx.market.ticker
        state = self._state.setdefault(ticker, {"slices": 0, "last_ordinal": None, "last_qty": 0})
        if ctx.position.qty > state["last_qty"]:
            state["slices"] += 1
            state["last_ordinal"] = state.get("pending")
        state["last_qty"] = ctx.position.qty
        ordinal = ctx.candle_index if ctx.candle_index is not None else len(ctx.prior)
        n, s = int(self.p("n")), int(self.p("s"))
        if state["slices"] >= n:
            return Decision(note="all slices entered; hold")
        if state["slices"] and state["last_ordinal"] is not None and ordinal - state["last_ordinal"] < s:
            return Decision(note="waiting for the next slice")
        if ctx.position.qty and ctx.position.side != "yes":
            return Decision(note="hold")
        out = entry_rule("fav", ctx, self.parameters, self.num)
        if isinstance(out, str):
            return Decision(note=out)
        if not self.spread_ok(ctx):
            return Decision(note="spread outside cap or missing")
        ask = ctx.candle.yes_ask_close
        qty = max(int(Decimal(100) / Decimal(n) / ask), 1)
        state["pending"] = ordinal
        return Decision(intents=[Intent("buy", "yes", qty, reason=f"slice {state['slices'] + 1}/{n}; {out[1]}")], note="split_slice")


# ---------------------------------------------------------------------------
# Batch 018: exits and holding period
# ---------------------------------------------------------------------------


class ManagedExit(Phase2):
    """One entry rule (fav or logit), one exit rule. No re-entry after an exit."""

    id = "managed_exit"
    name = "Managed exit"
    summary = "Exit rules read separately from a fixed entry rule."
    parameters = {"entry": "fav", "exit": "hold"}

    def required_prior(self) -> int:
        return int(self.p("w", 1))

    def _track(self, ctx):
        state = self._state.setdefault(ctx.market.ticker, {"peak": None, "held": 0, "armed": False, "rung": 0,
                                                            "entry_ts": None, "pending": None, "partial": False})
        if ctx.position.qty:
            state["held"] += 1
            bid = ctx.candle.yes_bid_close
            if usable_quote(bid) and (state["peak"] is None or bid > state["peak"]):
                state["peak"] = bid
            if state["entry_ts"] is None:
                state["entry_ts"] = state["pending"]
        return state

    def decide(self, ctx):
        state = self._track(ctx)
        pos = ctx.position
        if pos.qty and pos.side == "yes":
            return self.exit_rule(ctx, state)
        if pos.qty:
            return Decision(note="hold reversed position to settlement")
        if ctx.ever_traded:
            return Decision(note="exited; no re-entry")
        out = entry_rule(self.p("entry"), ctx, self.parameters, self.num)
        if isinstance(out, str):
            return Decision(note=out)
        if out[0] != "yes":
            return Decision(note="entry signal is NO; exit families trade YES entries only")
        if not self.spread_ok(ctx):
            return Decision(note="spread outside cap or missing")
        state["pending"] = ctx.as_of_ts
        return self.buy(ctx, "yes", out[1], note="exit_family_entry")

    def _sell(self, qty, reason, note):
        return Decision(intents=[Intent("sell", "yes", qty, reason=reason)], note=note)

    def exit_rule(self, ctx, state):
        rule = self.p("exit")
        pos = ctx.position
        candle = ctx.candle
        bid = candle.yes_bid_close
        if rule == "hold":
            return Decision(note="control: hold to settlement")
        if rule == "random":
            u = hash_unit(self.p("seed"), ctx.market.ticker, ctx.as_of_ts)
            if u < self._num("p_exit", ctx) and usable_quote(bid):
                return self._sell(pos.qty, f"random exit draw {u:.4f} < {self.p('p_exit')}", "random_exit")
            return Decision(note="random exit did not fire")
        if not usable_quote(bid):
            return Decision(note="hold: no usable bid")
        avg = pos.avg_entry_price
        if rule == "time":
            if state["held"] >= int(self.p("n")):
                return self._sell(pos.qty, f"held {state['held']} candles >= {self.p('n')}", "time_stop")
            return Decision(note="hold: time stop not reached")
        if rule == "clock":
            if state["entry_ts"] is not None and ctx.as_of_ts - state["entry_ts"] >= int(Decimal(self.p("hours")) * HOUR):
                return self._sell(pos.qty, f"{(ctx.as_of_ts - state['entry_ts']) / HOUR:.1f}h since entry >= {self.p('hours')}h", "clock_stop")
            return Decision(note="hold: clock stop not reached")
        if rule == "trailing":
            x = self._num("x", ctx)
            if state["peak"] is not None and bid <= state["peak"] - x:
                return self._sell(pos.qty, f"bid {bid} <= peak {state['peak']} - {x}", "trailing_stop")
            return Decision(note="hold: trailing stop not hit")
        if rule == "breakeven":
            if bid >= avg + self._num("g", ctx):
                state["armed"] = True
            if state["armed"] and bid <= avg:
                return self._sell(pos.qty, f"armed breakeven; bid {bid} <= entry {avg}", "breakeven_stop")
            return Decision(note="hold: breakeven not triggered")
        if rule == "target":
            if bid >= self._num("level", ctx):
                return self._sell(pos.qty, f"bid {bid} >= target {self.p('level')}", "target_exit")
            return Decision(note="hold: target not reached")
        if rule == "edge_gone":
            m = mid(candle)
            if m is None:
                return Decision(note="hold: no mid")
            q = logit_model(m, self.num("k", ctx, "1.25"))
            if q - bid <= self._num("thr", ctx):
                return self._sell(pos.qty, f"model q={q:.4f} - bid {bid} <= {self.p('thr')}; edge gone", "edge_gone_exit")
            return Decision(note="hold: model edge remains")
        if rule == "stop_reverse":
            if bid <= avg - self._num("x", ctx):
                return Decision(intents=[
                    Intent("sell", "yes", pos.qty, reason=f"bid {bid} <= entry {avg} - {self.p('x')}; stop"),
                    Intent("buy", "no", reason="reverse into NO after the stop"),
                ], note="stop_and_reverse")
            return Decision(note="hold: stop not hit")
        if rule == "vol_stop":
            window = refs_window(ctx.prior, int(self.p("w")))
            if window is None:
                return Decision(note="hold: no volatility window")
            sd = stdev(window)
            if sd > 0 and bid <= avg - self._num("z", ctx) * sd:
                return self._sell(pos.qty, f"bid {bid} <= entry {avg} - {self.p('z')}*sd {sd:.4f}", "vol_stop")
            return Decision(note="hold: volatility stop not hit")
        if rule == "partial":
            if not state["partial"] and bid >= avg + self._num("g", ctx) and pos.qty >= 2:
                state["partial"] = True
                return self._sell(pos.qty // 2, f"bid {bid} >= entry {avg} + {self.p('g')}; take half", "partial_take")
            return Decision(note="hold: partial taken or not reached")
        if rule == "ladder_take":
            g = self._num("g", ctx)
            rung = state["rung"]
            if rung < 3 and bid >= avg + g * Decimal(rung + 1):
                state["rung"] = rung + 1
                qty = pos.qty if rung == 2 else max(pos.qty // (3 - rung), 1)
                return self._sell(qty, f"bid {bid} >= entry {avg} + {rung + 1}x{g}; rung {rung + 1}", "ladder_take")
            return Decision(note="hold: next rung not reached")
        if rule == "max_loss":
            loss = (avg - bid) * Decimal(pos.qty)
            if loss >= self._num("dollars", ctx):
                return self._sell(pos.qty, f"mark loss {loss} >= {self.p('dollars')}", "max_loss_exit")
            return Decision(note="hold: loss limit not hit")
        raise ValueError(rule)


# ---------------------------------------------------------------------------
# Batch 019: information and timing ablations
# ---------------------------------------------------------------------------


class Ablation(SingleEntry):
    id = "ablation"
    name = "Information / timing ablation"
    summary = "The same simple rules with information removed, delayed, degraded, or thinned."
    parameters = {"mode": "lagged_momentum"}
    entry_note = "ablation_entry"

    def required_prior(self) -> int:
        mode = self.p("mode")
        if mode == "lagged_momentum":
            return int(self.p("d")) + 2
        if mode == "window_trunc":
            return int(self.p("L"))
        return 1

    def _ref_by_source(self, candle):
        source = self.p("source")
        if source == "trade":
            return candle.trade_close if usable_quote(candle.trade_close) else None
        if source == "mid":
            return mid(candle)
        if source == "bid":
            return candle.yes_bid_close if usable_quote(candle.yes_bid_close) else None
        if source == "ask":
            return candle.yes_ask_close if usable_quote(candle.yes_ask_close) else None
        raise ValueError(source)

    def _noisy(self, value, ctx, tag):
        sigma = self._num("sigma", ctx)
        if value is None or sigma == 0:
            return value
        u = hash_unit(self.p("seed"), ctx.market.ticker, tag)
        return value + sigma * (Decimal(2) * u - ONE)

    def _rounded(self, value, ctx):
        if value is None:
            return None
        grid = self._num("grid", ctx)
        return (value / grid).quantize(ONE) * grid

    def signal(self, ctx):
        mode = self.p("mode")
        candle, prior = ctx.candle, ctx.prior
        if mode == "lagged_momentum":
            d = int(self.p("d"))
            series = list(prior) + [candle]
            if len(series) < d + 2:
                return "not enough candles for the lag"
            now, before = ref(series[-1 - d]), ref(series[-2 - d])
            if now is None or before is None:
                return "no reference price at the lag"
            move = now - before
            if abs(move) < self._num("m", ctx):
                return "lagged move below threshold"
            return ("yes" if move > 0 else "no"), f"move {move} observed {d} candles ago; follow at today's quote"
        if mode == "delayed":
            ticker = ctx.market.ticker
            ordinal = ctx.candle_index if ctx.candle_index is not None else len(prior)
            state = self._state.setdefault(ticker, {"first": None})
            if state["first"] is None:
                out = entry_rule(self.p("entry"), ctx, self.parameters, self.num)
                if isinstance(out, str):
                    return out
                state["first"] = (ordinal, out[0])
            first, side = state["first"]
            if ordinal < first + int(self.p("d")):
                return f"signal at candle {first}; waiting {self.p('d')} candles"
            price = candle.yes_ask_close if side == "yes" else (ONE - candle.yes_bid_close if usable_quote(candle.yes_bid_close) else None)
            if price is None or not usable_quote(price) or price > Decimal("0.97"):
                return "no fillable price after the delay"
            return side, f"signal first seen at candle {first}; entered {ordinal - first} candles later at {price}"
        if mode == "source":
            now = self._ref_by_source(candle)
            before = self._ref_by_source(prior[-1]) if prior else None
            if now is None or before is None:
                return f"no {self.p('source')} price"
            move = now - before
            if abs(move) < self._num("m", ctx):
                return "move below threshold"
            return ("yes" if move > 0 else "no"), f"{self.p('source')} {before} -> {now} (move {move}); follow"
        if mode == "frequency":
            index = ctx.candle_index if ctx.candle_index is not None else len(prior)
            if index % int(self.p("k")) != 0:
                return f"not a decision candle at frequency 1/{self.p('k')}"
            return entry_rule(self.p("entry"), ctx, self.parameters, self.num)
        if mode == "spread_cap":
            return entry_rule(self.p("entry"), ctx, self.parameters, self.num)
        if mode == "noisy":
            entry = self.p("entry")
            if entry == "fav":
                m = self._noisy(mid(candle), ctx, ctx.as_of_ts)
                if m is None:
                    return "no mid"
                if m < Decimal("0.65") or m > Decimal("0.92"):
                    return "noisy mid outside favorite band"
                return "yes", f"noisy mid {m:.4f} (sigma {self.p('sigma')}) in 0.65-0.92"
            now = self._noisy(ref(candle), ctx, ctx.as_of_ts)
            before = self._noisy(ref(prior[-1]), ctx, prior[-1].end_period_ts) if prior else None
            if now is None or before is None:
                return "no reference price"
            move = now - before
            if abs(move) < Decimal("0.03"):
                return "noisy move below threshold"
            return ("yes" if move > 0 else "no"), f"noisy move {move:.4f} (sigma {self.p('sigma')})"
        if mode == "grid":
            entry = self.p("entry")
            if entry == "fav":
                m = self._rounded(mid(candle), ctx)
                if m is None:
                    return "no mid"
                if m < Decimal("0.65") or m > Decimal("0.92"):
                    return "rounded mid outside favorite band"
                return "yes", f"mid rounded to {self.p('grid')} grid = {m} in band"
            now = self._rounded(ref(candle), ctx)
            before = self._rounded(ref(prior[-1]), ctx) if prior else None
            if now is None or before is None:
                return "no reference price"
            move = now - before
            if abs(move) < Decimal("0.03"):
                return "rounded move below threshold"
            return ("yes" if move > 0 else "no"), f"rounded move {move} on {self.p('grid')} grid"
        if mode == "first_quote":
            side = self.p("side")
            ok = usable_quote(candle.yes_ask_close) if side == "yes" else usable_quote(candle.yes_bid_close)
            if not ok:
                return "no fillable quote yet"
            return side, "first decision candle with a fillable quote; no price rule"
        if mode == "window_trunc":
            L = int(self.p("L"))
            window = refs_window(prior, L)
            now = ref(candle)
            if window is None or now is None:
                return "not enough reference prices"
            m = mean(window)
            if now <= m - self._num("dev", ctx):
                return "yes", f"reference {now} <= mean of {L} = {m:.4f} - {self.p('dev')}"
            return "not below the truncated mean"
        if mode == "trade_gate":
            printed = usable_quote(candle.trade_close)
            want = self.p("prints")
            if want == "require" and not printed:
                return "no trade printed on this candle"
            if want == "absent" and printed:
                return "a trade printed on this candle"
            return entry_rule(self.p("entry"), ctx, self.parameters, self.num)
        raise ValueError(mode)


# ---------------------------------------------------------------------------
# Batch 020: ensembles, regimes, composite ideas, and a second null
# ---------------------------------------------------------------------------


def _vote_signals(ctx):
    """Directional votes from five simple signals. +1 up, -1 down, 0 none."""
    candle, prior = ctx.candle, ctx.prior
    votes = {}
    now = ref(candle)
    before = ref(prior[-1]) if prior else None
    move = (now - before) if (now is not None and before is not None) else None
    votes["momentum"] = 0 if move is None or abs(move) < Decimal("0.03") else (1 if move > 0 else -1)
    window = refs_window(prior, 4)
    if window is None or now is None:
        votes["breakout"] = 0
    elif now >= max(window) + Decimal("0.03"):
        votes["breakout"] = 1
    elif now <= min(window) - Decimal("0.03"):
        votes["breakout"] = -1
    else:
        votes["breakout"] = 0
    vols = [c.volume for c in prior[-6:]] if len(prior) >= 6 else None
    if not vols or candle.volume is None or any(v is None for v in vols) or move is None or move == 0:
        votes["volume"] = 0
    else:
        votes["volume"] = (1 if move > 0 else -1) if candle.volume > median(vols) else 0
    m = mid(candle)
    if m is None:
        votes["logit"] = 0
    else:
        q = logit_model(m, Decimal("1.25"))
        votes["logit"] = 1 if q - candle.yes_ask_close >= Decimal("0.02") else (-1 if candle.yes_bid_close - q >= Decimal("0.02") else 0)
    if len(prior) >= 3 and candle.open_interest is not None and prior[-3].open_interest is not None:
        then = prior[-3]
        base = then.open_interest if then.open_interest > 0 else ONE
        growth = (candle.open_interest - then.open_interest) / base
        r_then = ref(then)
        if growth >= Decimal("0.1") and now is not None and r_then is not None and now != r_then:
            votes["oi"] = 1 if now > r_then else -1
        else:
            votes["oi"] = 0
    else:
        votes["oi"] = 0
    return votes


class Composite(SingleEntry):
    id = "composite"
    name = "Composite / ensemble"
    summary = "Combines simpler signals; includes a matched-rate random null."
    parameters = {"mode": "vote"}
    entry_note = "composite_entry"

    def required_prior(self) -> int:
        return int(self.p("w", 6))

    def _leader(self, ctx):
        event = ctx.event
        if event is None:
            return None
        ranked = sorted(((q.mid, q.ticker) for q in event.quotes if q.mid is not None), key=lambda x: (-x[0], x[1]))
        if not ranked:
            return None
        lead = ranked[0][0] - (ranked[1][0] if len(ranked) > 1 else ZERO)
        return ranked[0][1], lead

    def signal(self, ctx):
        mode = self.p("mode")
        candle, prior = ctx.candle, ctx.prior
        if mode == "vote":
            votes = _vote_signals(ctx)
            up = sum(1 for v in votes.values() if v > 0)
            down = sum(1 for v in votes.values() if v < 0)
            k = int(self.p("k"))
            detail = ",".join(f"{name}={value}" for name, value in sorted(votes.items()))
            if up >= k and down == 0:
                return "yes", f"{up} bullish votes >= {k} ({detail})"
            if self.p("sides") == "both" and down >= k and up == 0:
                return "no", f"{down} bearish votes >= {k} ({detail})"
            return f"votes up={up} down={down} below {k}"
        if mode == "crowd_fade":
            votes = _vote_signals(ctx)
            trend = [votes["momentum"], votes["breakout"]]
            window = refs_window(prior, 6)
            now = ref(candle)
            if window is not None and now is not None and abs(now - window[0]) >= self._num("m", ctx):
                trend.append(1 if now > window[0] else -1)
            up = sum(1 for v in trend if v > 0)
            down = sum(1 for v in trend if v < 0)
            k = int(self.p("k"))
            if up >= k:
                return "no", f"{up} trend signals agree up; fade the crowd"
            if down >= k:
                return "yes", f"{down} trend signals agree down; fade the crowd"
            return "no crowded trend"
        if mode == "regime":
            w = int(self.p("w"))
            window = refs_window(prior, w)
            now = ref(candle)
            if window is None or now is None:
                return "not enough reference prices"
            series = window + [now]
            moves = [b - a for a, b in zip(series, series[1:])]
            vol = stdev(moves)
            if vol >= self._num("s", ctx):
                m, sd = mean(window), stdev(window)
                if sd > 0 and now <= m - Decimal("1.5") * sd:
                    return "yes", f"high-vol regime {vol:.4f}; revert from {now} below band"
                if sd > 0 and now >= m + Decimal("1.5") * sd:
                    return "no", f"high-vol regime {vol:.4f}; revert from {now} above band"
                return "high-vol regime; no band break"
            move = now - window[0]
            if abs(move) >= self._num("m", ctx):
                return ("yes" if move > 0 else "no"), f"calm regime {vol:.4f}; follow {w}-candle move {move}"
            return "calm regime; no trend"
        if mode in ("logit_mom", "conflict"):
            out = entry_rule("logit", ctx, self.parameters, self.num)
            if isinstance(out, str):
                return out
            if not prior:
                return "no prior candle"
            now, before = ref(candle), ref(prior[-1])
            if now is None or before is None:
                return "no reference price"
            move = now - before
            agrees = (out[0] == "yes" and move > 0) or (out[0] == "no" and move < 0)
            if mode == "logit_mom":
                if not agrees or abs(move) < self._num("m", ctx):
                    return "model and momentum do not agree"
                return out[0], f"{out[1]}; momentum {move} agrees"
            conflict = (out[0] == "yes" and move <= -self._num("m", ctx)) or (out[0] == "no" and move >= self._num("m", ctx))
            if self.p("policy") == "skip_conflict":
                return "model conflicts with momentum; skip" if conflict else (out[0], f"{out[1]}; no conflict")
            return (out[0], f"{out[1]}; conflicting momentum {move}") if conflict else "no conflict to trade"
        if mode == "leader_oi":
            lead = self._leader(ctx)
            if lead is None or lead[0] != ctx.market.ticker:
                return "not the event leader"
            if lead[1] < self._num("gap", ctx):
                return "leader margin below gap"
            if len(prior) < 3 or candle.open_interest is None or prior[-3].open_interest is None:
                return "open interest missing"
            base = prior[-3].open_interest if prior[-3].open_interest > 0 else ONE
            growth = (candle.open_interest - prior[-3].open_interest) / base
            if growth < self._num("g", ctx):
                return "open interest growth below threshold"
            if not usable_quote(candle.yes_ask_close) or candle.yes_ask_close > Decimal("0.95"):
                return "leader ask too high"
            return "yes", f"event leader (lead {lead[1]}) with OI growth {growth:.3f}"
        if mode == "consensus_fav":
            out = entry_rule("fav", ctx, self.parameters, self.num)
            if isinstance(out, str):
                return out
            checks = 0
            window = refs_window(prior, 6)
            if window is not None and stdev(window) <= Decimal("0.02"):
                checks += 1
            votes = _vote_signals(ctx)
            checks += 1 if votes["oi"] > 0 else 0
            checks += 1 if votes["volume"] > 0 else 0
            lead = self._leader(ctx)
            checks += 1 if lead is not None and lead[0] == ctx.market.ticker else 0
            if checks < int(self.p("k")):
                return f"{checks} confirmations below {self.p('k')}"
            return "yes", f"{out[1]}; {checks} confirmations"
        if mode == "fav_calm_leader":
            out = entry_rule("fav", ctx, self.parameters, self.num)
            if isinstance(out, str):
                return out
            window = refs_window(prior, 6)
            if window is None or stdev(window) > self._num("vol_cap", ctx):
                return "not calm"
            gap = self._num("gap", ctx)
            if gap > 0:
                lead = self._leader(ctx)
                if lead is None or lead[0] != ctx.market.ticker or lead[1] < gap:
                    return "not a clear event leader"
            return "yes", f"{out[1]}; calm (sd <= {self.p('vol_cap')}) leader gap >= {gap}"
        if mode == "mom_liquidity":
            vols = [c.volume for c in prior if c.volume is not None]
            if (sum(vols) if vols else ZERO) < self._num("v", ctx):
                return "recent volume below gate"
            return entry_rule("momentum", ctx, self.parameters, self.num)
        if mode == "mixture":
            rules = ("fav", "longshot_no", "momentum")
            choice = rules[int(hash_unit(self.p("seed"), ctx.market.ticker) * 3)]
            out = entry_rule(choice, ctx, self.parameters, self.num)
            if isinstance(out, str):
                return f"{choice}: {out}"
            return out[0], f"market assigned to {choice} by seed; {out[1]}"
        if mode == "null_rate":
            m = mid(candle)
            if m is None or m < Decimal("0.10") or m > Decimal("0.90"):
                return "mid outside 0.10-0.90"
            u = hash_unit(self.p("seed"), ctx.market.ticker, ctx.as_of_ts)
            if u * Decimal(1000) >= Decimal(int(self.p("per_mille"))):
                return "null draw did not fire"
            side = self.p("side")
            if side == "coin":
                side = "yes" if hash_unit(self.p("seed"), "side", ctx.market.ticker, ctx.as_of_ts) < HALF else "no"
            return side, f"matched-rate null fired (u={u:.4f}); side {side}"
        if mode in ("learned_structure", "horizon_learned"):
            learner = self._state.get("learner")
            if learner is None:
                learner = PoolLearner()
                learner.parameters = {"mode": "bucket", "scope": self.p("scope"), "width": "0.10",
                                      "min_n": 5, "prior": "2", "edge": self.p("edge"), "sides": "yes"}
                self._state["learner"] = learner
            if mode == "horizon_learned":
                schedule = ctx.schedule
                if schedule is None or schedule.close_ts is None:
                    return "no scheduled close published for this event"
                left_h = Decimal(schedule.close_ts - ctx.as_of_ts) / Decimal(HOUR)
                if left_h <= 0 or left_h > self._num("hours", ctx):
                    return "outside the horizon window"
            out = learner.signal(ctx)
            if isinstance(out, str):
                return out
            if mode == "learned_structure":
                event = ctx.event
                quotes = [q for q in (event.quotes if event else ()) if q.mid is not None]
                mass = sum(q.mid for q in quotes) if quotes else ZERO
                own = next((q for q in quotes if q.ticker == ctx.market.ticker), None)
                if own is None or mass <= 0 or len(quotes) < 3:
                    return "no event structure"
                fair = own.mid / mass
                if fair - candle.yes_ask_close < self._num("edge", ctx):
                    return "normalized event price does not agree"
                return "yes", f"{out[1]}; normalized {fair:.4f} agrees"
            return out
        raise ValueError(mode)


# ---------------------------------------------------------------------------
# Matched placebo: same trigger, seeded coin for the side
# ---------------------------------------------------------------------------


class MatchedPlacebo(Phase2):
    """Runs an entry-only family and replaces its chosen side with a seeded coin.

    Same markets, same timestamps, same size rule as the inner rule, so the
    difference between a family and its placebo isolates the value of the side
    choice from the value of the trigger's timing and market selection.
    """

    id = "matched_placebo"
    name = "Matched placebo"
    summary = "Inner rule's trigger and size, seeded random side."

    def __init__(self, inner: Strategy | None = None, seed: str = "0"):
        super().__init__()
        self.inner = inner
        self.seed = seed
        self.parameters = {}

    def reset(self) -> None:
        super().reset()
        if self.inner is not None:
            self.inner.reset()

    def required_prior(self) -> int:
        return self.inner.required_prior() if hasattr(self.inner, "required_prior") else 1

    def decide(self, ctx):
        decision = self.inner.decide(ctx)
        if not decision.intents:
            return decision
        out = []
        for intent in decision.intents:
            if intent.action != "buy":
                out.append(intent)
                continue
            u = hash_unit(self.seed, ctx.market.ticker, ctx.as_of_ts)
            side = "yes" if u < HALF else "no"
            out.append(Intent("buy", side, intent.quantity,
                              reason=f"placebo side {side} (seed {self.seed}, u={u:.4f}); inner rule said {intent.side}: {intent.reason}"))
        return Decision(intents=out, note="placebo_entry")
