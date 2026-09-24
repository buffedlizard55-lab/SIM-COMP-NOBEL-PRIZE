"""High-throughput program engine for the 2,000-strategy research program (20 batches of 100).

Same economics as engine.run_competition (shared compute_fill), different output
shape: compact gzip CSV ledgers per batch and universe, aggregate JSON for the
site. Participants never trade with each other. Every row streams from a stored
candle close; the decision clock rule is identical to the primary engine.

Ledger layout (one gzipped CSV per batch x universe):

    participant_id,ts_unix,ticker,action,side,price,qty,fee,cash_after,
    realized_pnl,fill_src,note

    action     buy | sell | settlement
    fill_src   YA yes_ask.close | YB yes_bid.close | NA derived NO ask from
               yes_bid.close | NB derived NO bid from yes_ask.close |
               MR official market.result at settlement
    note       the strategy's decision note, or settlement_result_yes/no

A row is reproducible from data/sim/candles/{ticker}.json plus the variant's
parameters in data/sim/program/strategies.json. Readers who need the rich
per-field audit format can rerun any batch: the per-participant ledger hash in
manifest.json is the check.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import time
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from simcomp import ENGINE_VERSION
from simcomp.engine import (
    Book,
    DecisionView,
    Position,
    SimConfig,
    assign_ranks,
    compute_fill,
    decision_candles,
    _mark,
)
from simcomp.analysis import analyse, data_quality_flags, render_markdown
from simcomp.context import EventIndex, SettledPool, build_settled_records
from simcomp.kalshi_parse import Candle, Market
from simcomp.money import ZERO, money, unix_to_iso, D
from simcomp.research_program import PROGRAM_PRIOR_WINDOW, Variant, program_variants, topic_statement
from simcomp.strategies import Decision, Intent

PROGRAM_VERSION = "3.0.0"

UNIVERSES = {
    "nobel_forward": {
        "competition_id": "program-nobel-forward",
        "title": "Program, Nobel markets, forward simulation",
        "kind": "forward_simulation",
        "data_tier": "live_kalshi",
    },
    "nobel_settled": {
        "competition_id": "program-nobel-settled",
        "title": "Program, settled Nobel markets, historical backtest",
        "kind": "historical_backtest",
        "data_tier": "historical_kalshi",
    },
    "panel_settled": {
        "competition_id": "program-panel-settled",
        "title": "Program, settled panel, historical backtest",
        "kind": "historical_backtest",
        "data_tier": "historical_kalshi",
    },
}

FILL_SRC = {
    "yes_ask.close": "YA",
    "yes_bid.close": "YB",
    "derived_no_ask_from_yes_bid.close": "NA",
    "derived_no_bid_from_yes_ask.close": "NB",
    "price.close": "LT",
    "market.result": "MR",
}

CSV_COLUMNS = [
    "participant_id", "ts_unix", "ticker", "action", "side", "price", "qty",
    "fee", "cash_after", "realized_pnl", "fill_src", "note",
]


def _ledger_note(text: str) -> str:
    """Note codes never carry a comma, so the compact CSV parses field-by-field."""
    return (text or "intent").split(";")[0].replace(",", " ")[:64]

# Rerun after the full pass and compared ledger by ledger: the null band, the
# event channel (011), the settled-pool learners (013), and stateful exits (018).
REPLAY_BATCHES = ("batch-001", "batch-011", "batch-013", "batch-018")
REPLAY_BATCH = ", ".join(REPLAY_BATCHES)


@dataclass
class ParticipantAgg:
    book: Book
    open_cost: Decimal = ZERO
    first_ts: int | None = None
    last_ts: int | None = None
    markets: set = field(default_factory=set)
    settlement_rows: int = 0
    ledger_hash: object = None  # hashlib accumulator
    open_positions: int = 0
    liquidation: Decimal = ZERO

    def ledger_row(self, *fields) -> None:
        self.ledger_hash.update("|".join(str(f) for f in fields).encode())
        self.ledger_hash.update(b"\n")


def _gzip_text(path: Path):
    """Text writer for a gzip file with a fixed header (mtime=0), so identical
    ledgers produce byte-identical files and stable sha256 values in the manifest."""
    return io.TextIOWrapper(gzip.GzipFile(str(path), "wb", compresslevel=6, mtime=0), encoding="utf-8", newline="")


class _CsvSinks:
    """One gzipped CSV writer per (batch, universe), opened lazily."""

    def __init__(self, directory: Path, universe: str):
        self.directory = directory
        self.universe = universe
        self.handles: dict[str, tuple] = {}
        self.rows_by_batch: dict[str, int] = {}

    def write(self, batch: str, row: list) -> None:
        entry = self.handles.get(batch)
        if entry is None:
            path = self.directory / batch / f"{self.universe}.csv.gz"
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = _gzip_text(path)
            writer = csv.writer(raw)
            writer.writerow(CSV_COLUMNS)
            entry = (raw, writer, path)
            self.handles[batch] = entry
        entry[1].writerow(row)
        self.rows_by_batch[batch] = self.rows_by_batch.get(batch, 0) + 1

    def close(self) -> dict[str, str]:
        files = {}
        for batch, (raw, _writer, path) in self.handles.items():
            raw.close()
            files[batch] = str(path)
        return files


def _percentile(ordered: list[float], p: float) -> float:
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * p
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    frac = rank - low
    return ordered[low] + (ordered[high] - ordered[low]) * frac


def _band(values: list[float]) -> dict:
    ordered = sorted(values)
    if not ordered:
        return {"n": 0}
    mean = sum(ordered) / len(ordered)
    return {
        "n": len(ordered),
        "min": ordered[0],
        "p05": _percentile(ordered, 0.05),
        "q1": _percentile(ordered, 0.25),
        "median": _percentile(ordered, 0.5),
        "q3": _percentile(ordered, 0.75),
        "p95": _percentile(ordered, 0.95),
        "max": ordered[-1],
        "mean": mean,
    }


def run_universe(
    markets: list[Market],
    universe: str,
    variants: list[Variant],
    sink: _CsvSinks | None,
    collect_note_counts: dict | None = None,
    prior_window: int | None = None,
    events_by_ticker: dict | None = None,
    settled_pool: SettledPool | None = None,
    categories: dict | None = None,
) -> dict:
    """One pass over every participant in the universe. Mirrors run_competition economics.

    prior_window defaults to PROGRAM_PRIOR_WINDOW. The parity tests pass a huge
    window so the views equal the primary engine's full-history views; a
    divergence with the default window must then come only from a strategy whose
    documented lookback exceeds the window (the unbounded volume_momentum).
    """
    window_cap = prior_window if prior_window is not None else PROGRAM_PRIOR_WINDOW
    meta = UNIVERSES[universe]
    config = SimConfig(
        competition_id=meta["competition_id"],
        title=meta["title"],
        kind=meta["kind"],
        data_tier=meta["data_tier"],
        assumption_note=(
            "Program run. Same size rules, fee interpretation, and mark rule as the "
            "primary competition with the same universe."
        ),
        primary=False,
    )

    flags: list[dict] = []
    prepared = []
    for market in markets:
        if market.market_type and market.market_type != "binary":
            flags.append({"code": "not_binary", "severity": "info",
                          "message": f"{market.ticker} market_type={market.market_type}; not simulated.",
                          "market_ticker": market.ticker})
            continue
        candles, market_flags = decision_candles(market)
        flags.extend(market_flags)
        if not candles:
            continue
        prepared.append((market, candles))

    # Decision-time channels (simcomp/context.py). The event index sees only this
    # universe's stored markets; the settled pool is global but strictly < T.
    event_index = EventIndex(prepared, events_by_ticker or {})
    categories = categories or {}

    participants = []
    for variant in variants:
        # Replays and later universes reuse the same instances; memory must not carry over.
        variant.strategy.reset()
        participants.append({
            "id": variant.username,
            "batch": variant.batch,
            "family": variant.family,
            "strategy_id": variant.strategy_id,
            "strategy": variant.strategy,
        })
    strats = {p["id"]: p["strategy"] for p in participants}
    aggs = {p["id"]: ParticipantAgg(book=Book(cash=config.starting_cash, peak=config.starting_cash),
                                    ledger_hash=hashlib.sha256()) for p in participants}
    positions: dict[tuple[str, str], Position] = {}
    ever: dict[tuple[str, str], bool] = {}
    per_market: dict[tuple[str, str], list] = {}  # (pid, ticker) -> [trade_rows, realized Decimal]
    clips: dict[str, int] = {}  # pid -> fills whose size the engine clipped
    activity: dict[str, int] = {}  # ISO day -> ledger rows

    events = []
    for market, candles in prepared:
        for index, candle in enumerate(candles):
            events.append((candle.end_period_ts, market.ticker, index, market, candles))
    events.sort(key=lambda item: (item[0], item[1]))

    def position_for(pid: str, ticker: str) -> Position:
        return positions.setdefault((pid, ticker), Position())

    for end_ts, _ticker, index, market, candles in events:
        candle = candles[index]
        low = index - window_cap
        if low < 0:
            low = 0
        prior = tuple(candles[low:index])
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
            category=categories.get(market.series_ticker, ""),
        )
        event_key = market.event_ticker or market.ticker
        event_view = event_index.view(event_key, end_ts)
        if event_view is not None and any(q.end_ts > end_ts for q in event_view.quotes):
            raise RuntimeError("lookahead guard: event view contains a later candle")
        schedule_view = event_index.schedule(event_key)
        settled_view = settled_pool.view(end_ts) if settled_pool is not None else None
        if settled_view is not None and settled_view.records and settled_view.records[-1].settlement_ts >= end_ts:
            raise RuntimeError("lookahead guard: settled pool not strictly before the decision")
        for participant in participants:
            pid = participant["id"]
            strategy = strats[pid]
            pos = position_for(pid, market.ticker)
            agg = aggs[pid]
            book = agg.book
            view = DecisionView(
                as_of_ts=end_ts,
                market=market_view,
                candle=candle,
                prior=prior,
                position=pos.copy(),
                cash=book.cash,
                ever_traded=ever.get((pid, market.ticker), False),
                candle_index=index,
                event=event_view,
                settled=settled_view,
                schedule=schedule_view,
            )
            if hasattr(view.market, "result") or hasattr(view, "result"):
                raise RuntimeError("decision view leaked result")
            decision = strategy.decide(view)
            if not isinstance(decision, Decision):
                raise TypeError(f"{strategy.id} did not return Decision")
            intents = sorted(decision.intents, key=lambda item: 0 if item.action == "sell" else 1)
            if collect_note_counts is not None:
                note_key = (participant["family"], _ledger_note(decision.note) or "no_note")
                collect_note_counts[note_key] = collect_note_counts.get(note_key, 0) + 1
            for intent in intents:
                fill, clip = compute_fill(config, market, candle, book, pos, intent)
                if fill is None:
                    continue
                ever[(pid, market.ticker)] = True
                agg.open_cost += fill.cost_delta
                note = _ledger_note(decision.note)
                if clip:
                    note = _ledger_note(note + " | clip " + clip)
                    clips[pid] = clips.get(pid, 0) + 1
                canonical = (
                    end_ts, market.ticker, fill.action, fill.side, money(fill.price),
                    fill.qty, money(fill.fee), money(book.cash), money(fill.realized),
                )
                agg.ledger_row(*canonical)
                if sink is not None:
                    sink.write(participant["batch"], [
                        pid, end_ts, market.ticker, fill.action, fill.side,
                        money(fill.price), fill.qty, money(fill.fee), money(book.cash),
                        money(fill.realized), FILL_SRC.get(fill.source, fill.source), note,
                    ])
                day = unix_to_iso(end_ts)[:10]
                activity[day] = activity.get(day, 0) + 1
                agg.markets.add(market.ticker)
                pm = per_market.setdefault((pid, market.ticker), [0, ZERO])
                pm[0] += 1
                pm[1] += fill.realized
                agg.first_ts = end_ts if agg.first_ts is None else min(agg.first_ts, end_ts)
                agg.last_ts = end_ts if agg.last_ts is None else max(agg.last_ts, end_ts)
                mark_now, _src = _mark(pos, candle)
                _drawdown(book, book.cash + (agg.open_cost - pos.cost) + mark_now)

    # Settlement pass: uses official result only after the decision loop.
    for market, candles in prepared:
        result = market.settled_result
        if not result or market.settlement_ts is None:
            continue
        for participant in participants:
            pid = participant["id"]
            pos = positions.get((pid, market.ticker))
            if not pos or pos.qty <= 0:
                continue
            agg = aggs[pid]
            book = agg.book
            won = (result == "yes" and pos.side == "yes") or (result == "no" and pos.side == "no")
            payout = Decimal(pos.qty) if won else ZERO
            realized = payout - pos.cost
            book.cash += payout
            book.realized += realized
            book.settled_round_trips += 1
            if realized > 0:
                book.wins += 1
            elif realized < 0:
                book.losses += 1
            note = f"settlement_result_{result}"
            canonical = (
                market.settlement_ts, market.ticker, "settlement", pos.side,
                "1.0000" if won else "0.0000", pos.qty, "0.0000", money(book.cash), money(realized),
            )
            agg.ledger_row(*canonical)
            if sink is not None:
                sink.write(participant["batch"], [
                    pid, market.settlement_ts, market.ticker, "settlement", pos.side,
                    "1.0000" if won else "0.0000", pos.qty, "0.0000", money(book.cash),
                    money(realized), "MR", note,
                ])
            day = unix_to_iso(market.settlement_ts)[:10]
            activity[day] = activity.get(day, 0) + 1
            agg.open_cost -= pos.cost
            agg.settlement_rows += 1
            pm = per_market.setdefault((pid, market.ticker), [0, ZERO])
            pm[0] += 1
            pm[1] += realized
            agg.markets.add(market.ticker)
            _drawdown(book, book.cash)
            pos.qty = 0
            pos.cost = ZERO
            pos.side = ""

    # Final liquidation marks on the last decision candle only.
    last_candle = {market.ticker: candles[-1] for market, candles in prepared}
    open_position_rows = []
    for market, candles in prepared:
        ticker = market.ticker
        for participant in participants:
            pid = participant["id"]
            pos = positions.get((pid, ticker))
            if not pos or pos.qty <= 0:
                continue
            agg = aggs[pid]
            mark, mark_source = _mark(pos, last_candle[ticker])
            agg.liquidation += mark
            agg.open_positions += 1
            open_position_rows.append([
                pid, ticker, pos.side, pos.qty,
                money(pos.avg_entry_price), money(pos.cost), money(mark),
                money(mark - pos.cost), FILL_SRC.get(mark_source, mark_source),
                last_candle[ticker].end_period_ts,
            ])
            pm = per_market.setdefault((pid, ticker), [0, ZERO])
            pm[1] += mark - pos.cost
    for participant in participants:
        agg = aggs[participant["id"]]
        _drawdown(agg.book, agg.book.cash + agg.liquidation)

    leaderboard = []
    for participant in participants:
        pid = participant["id"]
        agg = aggs[pid]
        book = agg.book
        equity = book.cash + agg.liquidation
        unrealized = equity - config.starting_cash - book.realized
        trips = book.settled_round_trips
        leaderboard.append({
            "p": pid,
            "b": participant["batch"],
            "f": participant["family"],
            "s": participant["strategy_id"],
            "u": universe,
            "eq": money(equity),
            "cash": money(book.cash),
            "mtm": money(agg.liquidation),
            "real": money(book.realized),
            "unreal": money(unrealized),
            "fees": money(book.fees),
            "n": book.trade_count,
            "sett": agg.settlement_rows,
            "w": book.wins,
            "l": book.losses,
            "trips": trips,
            "wr": None if trips == 0 else money(Decimal(book.wins) / Decimal(trips)),
            "dd": money(book.max_drawdown),
            "roi": money((equity - config.starting_cash) / config.starting_cash),
            "mkts": len(agg.markets),
            "open": agg.open_positions,
            "t0": agg.first_ts,
            "t1": agg.last_ts,
            "participant_id": pid,
            "ending_equity": money(equity),
        })
    assign_ranks(leaderboard)
    for row in leaderboard:
        row["r"] = row.pop("rank")
        row["tied_flag"] = row.pop("tied")
        row.pop("participant_id")
        row.pop("ending_equity")

    # Per-market rollups for market-by-market program results.
    market_rollups = []
    pm_by_market: dict[str, list] = {}
    for (pid, ticker), value in per_market.items():
        pm_by_market.setdefault(ticker, []).append((pid, value))
    family_of = {p["id"]: p["family"] for p in participants}
    for market, candles in prepared:
        rows = pm_by_market.get(market.ticker, [])
        families: dict[str, list[float]] = {}
        traded_participants = set()
        for pid, (trade_rows, pnl) in rows:
            if trade_rows <= 0:
                continue
            traded_participants.add(pid)
            families.setdefault(family_of[pid], []).append(float(pnl))
        family_stats = {
            family: {
                "n": len(values),
                "median_pnl": round(_percentile(sorted(values), 0.5), 4),
                "mean_pnl": round(sum(values) / len(values), 4),
                "min_pnl": round(min(values), 4),
                "max_pnl": round(max(values), 4),
            }
            for family, values in sorted(families.items())
            if values
        }
        market_rollups.append({
            "ticker": market.ticker,
            "title": market.title,
            "subtitle": market.subtitle,
            "event_ticker": market.event_ticker,
            "series_ticker": market.series_ticker,
            "universe": universe,
            "status": market.status,
            "official_result": market.settled_result or (market.result or ""),
            "result_label": "historical_official" if market.settled_result else "unsettled",
            "settlement_ts": market.settlement_ts,
            "source_url": market.source_url,
            "decision_candles": len(candles),
            "participants_traded": len(traded_participants),
            "families": family_stats,
        })

    ledger_hashes = {pid: agg.ledger_hash.hexdigest() for pid, agg in aggs.items()}
    combined = hashlib.sha256()
    for pid in sorted(ledger_hashes):
        combined.update(pid.encode())
        combined.update(ledger_hashes[pid].encode())
    return {
        "universe": universe,
        "config": config.public(),
        "markets_used": len(prepared),
        "events": len(events),
        "leaderboard": leaderboard,
        "market_rollups": market_rollups,
        "open_position_rows": open_position_rows,
        "flags": flags,
        "activity": activity,
        "ledger_hashes": ledger_hashes,
        "combined_ledger_sha256": combined.hexdigest(),
        # In-memory only (not written as-is): inputs for simcomp/analysis.py.
        "event_pnl": _event_pnl(per_market, {m.ticker: (m.event_ticker or m.ticker) for m, _c in prepared}),
        "clips": clips,
        "event_outcomes": _event_outcomes(prepared),
    }


def _event_pnl(per_market: dict, event_of: dict) -> dict:
    """pid -> {event_ticker: P&L} (realized + settlement + final mark, fees included)."""
    out: dict[str, dict] = {}
    for (pid, ticker), (_rows, pnl) in per_market.items():
        bucket = out.setdefault(pid, {})
        event = event_of.get(ticker, ticker)
        bucket[event] = bucket.get(event, ZERO) + pnl
    return out


def _event_outcomes(prepared: list) -> dict:
    """event -> {markets, yes, settled}: the power available to test anything on this universe."""
    out: dict[str, dict] = {}
    for market, _candles in prepared:
        entry = out.setdefault(market.event_ticker or market.ticker, {"markets": 0, "yes": 0, "settled": 0})
        entry["markets"] += 1
        result = market.settled_result
        if result:
            entry["settled"] += 1
            entry["yes"] += 1 if result == "yes" else 0
    return out


def _drawdown(book: Book, equity: Decimal) -> None:
    if equity > book.peak:
        book.peak = equity
    drop = book.peak - equity
    if drop > book.max_drawdown:
        book.max_drawdown = drop


def _family_report(universe_results: dict[str, dict]) -> dict:
    """family -> universe -> aggregate stats and top/bottom variants."""
    null_band: dict[str, dict] = {}
    for universe, result in universe_results.items():
        null_equities = [float(row["eq"]) for row in result["leaderboard"] if row["f"] == "null_model"]
        null_band[universe] = _band(null_equities)
    families: dict[str, dict] = {}
    for universe, result in universe_results.items():
        grouped: dict[str, list] = {}
        for row in result["leaderboard"]:
            grouped.setdefault(row["f"], []).append(row)
        p95 = null_band[universe].get("p95", 0.0)
        p05 = null_band[universe].get("p05", 0.0)
        for family, rows in grouped.items():
            equities = [float(row["eq"]) for row in rows]
            ordered = sorted(rows, key=lambda row: float(row["eq"]))
            entry = families.setdefault(family, {})
            band = _band(equities)
            entry[universe] = {
                **{key: (round(value, 4) if isinstance(value, float) else value) for key, value in band.items()},
                "share_above_null_p95": round(sum(1 for e in equities if e > p95) / len(equities), 4) if equities else 0,
                "share_below_null_p05": round(sum(1 for e in equities if e < p05) / len(equities), 4) if equities else 0,
                "top": [{"s": row["s"], "eq": row["eq"]} for row in ordered[-3:]],
                "bottom": [{"s": row["s"], "eq": row["eq"]} for row in ordered[:3]],
            }
    return {"families": families, "null_band": null_band}


def _param_sensitivity(rows: list[dict], variants_by_sid: dict[str, Variant]) -> dict:
    """For each parameter key, median ending equity per parameter value.

    High-cardinality keys (a value held by fewer than two variants, e.g. a null
    seed) are not sensitivity axes and are skipped.
    """
    by_key: dict[str, dict[str, list]] = {}
    for row in rows:
        variant = variants_by_sid.get(row["s"])
        if variant is None:
            continue
        for key, value in variant.strategy.parameters.items():
            bucket = by_key.setdefault(key, {}).setdefault(str(value), [])
            bucket.append(float(row["eq"]))
    out = {}
    for key, values in sorted(by_key.items()):
        points = [
            (value, equities) for value, equities in values.items() if len(equities) >= 2
        ]
        if not points:
            continue

        def _sort_key(item):
            text = item[0]
            try:
                return (0, float(text))
            except ValueError:
                return (1, 0.0)

        out[key] = [
            {"value": value, "n": len(equities), "median_equity": round(_percentile(sorted(equities), 0.5), 4)}
            for value, equities in sorted(points, key=_sort_key)
        ]
    return out


def load_events(root: Path) -> dict:
    path = root / "data" / "kalshi" / "events.json"
    if not path.exists():
        return {}
    records = json.loads(path.read_text())
    return {r["event_ticker"]: r for r in records if r.get("event_ticker")}


def program_channels(root: Path, grouped: dict[str, list]) -> dict:
    """Keyword arguments for run_universe: event records, category map, settled pool.

    The settled pool is built from every stored market in every universe; each
    record becomes visible only strictly after its own Kalshi settlement_ts.
    """
    events = load_events(root)
    categories: dict[str, str] = {}
    for record in events.values():
        series, category = record.get("series_ticker"), record.get("category")
        if series and category and series not in categories:
            categories[series] = category
    all_markets = [m for markets in grouped.values() for m in markets]
    records = build_settled_records(all_markets, decision_candles, categories)
    return {"events_by_ticker": events, "settled_pool": SettledPool(records), "categories": categories}


def run_program(root: Path, grouped: dict[str, list], variants: list[Variant] | None = None,
                replay: bool = True, log=print) -> dict:
    """Run every batch over every universe and write the program bundle."""
    started = time.time()
    variants = variants or program_variants()
    if not variants:
        raise ValueError("empty program")
    variants_by_sid = {v.strategy_id: v for v in variants}
    batches = sorted({v.batch for v in variants})

    program_dir = root / "data" / "sim" / "program"
    trades_dir = program_dir / "trades"
    program_dir.mkdir(parents=True, exist_ok=True)

    channels = program_channels(root, grouped)

    note_counts: dict = {}
    universe_results: dict[str, dict] = {}
    trade_files: dict[str, dict] = {}
    for universe in ("nobel_forward", "nobel_settled", "panel_settled"):
        markets = grouped.get(universe) or []
        sink = _CsvSinks(trades_dir, universe)
        t0 = time.time()
        result = run_universe(markets, universe, variants, sink, note_counts, **channels)
        files = sink.close()
        result["runtime_seconds"] = round(time.time() - t0, 3)
        result["trade_rows_by_batch"] = sink.rows_by_batch
        universe_results[universe] = result
        trade_files[universe] = files
        log(f"program {universe}: {len(variants)} participants, {result['markets_used']} markets, "
            f"{result['events']} candle events in {result['runtime_seconds']}s")

    replay_proof = {"status": "skipped", "batch": REPLAY_BATCH, "batches": list(REPLAY_BATCHES)}
    if replay:
        replay_variants = [v for v in variants if v.batch in REPLAY_BATCHES]
        matched = True
        checked = 0
        details = {}
        for universe in ("nobel_forward", "nobel_settled", "panel_settled"):
            second = run_universe(grouped.get(universe) or [], universe, replay_variants, None, **channels)
            first_hashes = universe_results[universe]["ledger_hashes"]
            for pid, digest in second["ledger_hashes"].items():
                checked += 1
                if first_hashes.get(pid) != digest:
                    matched = False
                    details.setdefault("mismatch", []).append(pid)
            details[universe] = second["combined_ledger_sha256"]
        replay_proof = {
            "status": "matched" if matched else "mismatch",
            "batch": REPLAY_BATCH,
            "batches": list(REPLAY_BATCHES),
            "participants_checked": checked,
            "universes": {u: universe_results[u]["combined_ledger_sha256"] for u in universe_results},
            "note": (
                f"{REPLAY_BATCH} were rerun (fresh strategy memory via reset()) against the stored "
                "candles after the full pass. Per-participant ledger hashes matched. This is not a Kalshi fill."
            ) if matched else "Ledger mismatch. Do not trust the bundle.",
            "replay_universe_hashes": details,
        }
        if not matched:
            raise SystemExit("program replay mismatch")

    # Aggregate files -------------------------------------------------------
    family_report = _family_report(universe_results)

    leaderboard_rows = [row for result in universe_results.values() for row in result["leaderboard"]]
    (program_dir / "leaderboard.json").write_text(json.dumps(leaderboard_rows, separators=(",", ":")))
    csv_fields = ["p", "b", "f", "s", "u", "r", "eq", "cash", "mtm", "real", "unreal", "fees",
                  "n", "sett", "w", "l", "trips", "wr", "dd", "roi", "mkts", "open", "t0", "t1"]
    with (program_dir / "leaderboard.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(csv_fields)
        for row in leaderboard_rows:
            writer.writerow([row.get(key) for key in csv_fields])

    # Open positions, gzipped (audit for unrealized P&L decomposition).
    positions_path = program_dir / "positions.csv.gz"
    with _gzip_text(positions_path) as raw:
        writer = csv.writer(raw)
        writer.writerow(["universe", "participant_id", "ticker", "side", "qty", "avg_entry", "cost",
                         "liquidation", "unrealized_pnl", "mark_src", "mark_ts_unix"])
        for universe in ("nobel_forward", "nobel_settled", "panel_settled"):
            for row in universe_results[universe]["open_position_rows"]:
                writer.writerow([universe] + row)

    families_payload = {
        "generated_at_unix": int(started),
        "null_band": {u: {k: (round(v, 4) if isinstance(v, float) else v) for k, v in band.items()}
                      for u, band in family_report["null_band"].items()},
        "families": family_report["families"],
        "wording": (
            "A family shares its entry rule; variants change parameters. The null band is the "
            "distribution of batch-001 random-entry variants in the same universe. A median inside "
            "that band is not evidence of an edge."
        ),
    }
    (program_dir / "families.json").write_text(json.dumps(families_payload, separators=(",", ":")))

    markets_payload = [row for result in universe_results.values() for row in result["market_rollups"]]
    (program_dir / "markets.json").write_text(json.dumps(markets_payload, separators=(",", ":")))

    ledger_hashes_payload = {
        universe: result["ledger_hashes"] for universe, result in universe_results.items()
    }
    (program_dir / "ledger_hashes.json").write_text(json.dumps(ledger_hashes_payload, separators=(",", ":")))

    strategies_payload = [variant.public() for variant in variants]
    (program_dir / "strategies.json").write_text(json.dumps(strategies_payload, separators=(",", ":")))
    participants_payload = [
        {
            "id": v.username,
            "username": v.username,
            "display_name": v.display_name,
            "strategy_id": v.strategy_id,
            "batch": v.batch,
            "family": v.family,
            "topic": v.topic,
            "hypothesis": v.hypothesis,
            "parameters": dict(v.strategy.parameters),
            "simulated": True,
            "real_kalshi_account": False,
        }
        for v in variants
    ]
    (program_dir / "participants.json").write_text(json.dumps(participants_payload, separators=(",", ":")))

    notes_payload = [
        {"family": family, "note": note, "count": count}
        for (family, note), count in sorted(note_counts.items())
    ]
    (program_dir / "notes.json").write_text(json.dumps(notes_payload, separators=(",", ":")))

    activity_payload = {
        universe: [{"day": day, "ledger_rows": count} for day, count in sorted(result["activity"].items())]
        for universe, result in universe_results.items()
    }
    (program_dir / "activity.json").write_text(json.dumps(activity_payload, separators=(",", ":")))

    # Per-batch reports.
    batch_dir = program_dir / "batches"
    batch_dir.mkdir(parents=True, exist_ok=True)
    for batch in batches:
        topic, statement = topic_statement(batch)
        batch_variants = [v for v in variants if v.batch == batch]
        report = {
            "batch": batch,
            "topic": topic,
            "statement": statement,
            "variant_count": len(batch_variants),
            "families": sorted({v.family for v in batch_variants}),
            "universes": {},
        }
        for universe, result in universe_results.items():
            rows = [row for row in result["leaderboard"] if row["b"] == batch]
            rows.sort(key=lambda row: row["r"])
            equities = [float(row["eq"]) for row in rows]
            entered = [row for row in rows if row["n"] > 0]
            null_band = family_report["null_band"][universe]
            families_in_batch = sorted({row["f"] for row in rows})
            sensitivity = {}
            for family in families_in_batch:
                family_rows = [row for row in rows if row["f"] == family]
                if len(family_rows) < 4:
                    continue
                sensitivity[family] = _param_sensitivity(family_rows, variants_by_sid)
            report["universes"][universe] = {
                "leaderboard": rows,
                "trade_rows": result["trade_rows_by_batch"].get(batch, 0),
                "entered": len(entered),
                "equity": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in _band(equities).items()},
                "best": rows[0] if rows else None,
                "worst": rows[-1] if rows else None,
                "null_band": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in null_band.items()},
                "share_above_null_p95": round(sum(1 for e in equities if e > null_band.get("p95", 0)) / len(equities), 4) if equities else 0,
                "share_below_null_p05": round(sum(1 for e in equities if e < null_band.get("p05", 0)) / len(equities), 4) if equities else 0,
                "param_sensitivity": sensitivity,
                "trades_csv": f"data/sim/program/trades/{batch}/{universe}.csv.gz",
                "caution": (
                    "One snapshot, no market-impact model, fee interpretation, closing-quote fills. "
                    "Rank spread inside this batch is evidence about parameters on this data, not about skill."
                ),
            }
        (batch_dir / f"{batch}.json").write_text(json.dumps(report, separators=(",", ":")))

    # Research analysis: predeclared verdict rules per family (simcomp/analysis.py).
    research = analyse(universe_results, variants)
    research["data_quality"] = data_quality_flags(grouped, universe_results)
    research["replay"] = {"status": replay_proof["status"], "batches": list(REPLAY_BATCHES)}
    (program_dir / "research.json").write_text(json.dumps(research, separators=(",", ":"), default=str))

    # Manifest with a verifiable file inventory.
    def file_entry(path: Path) -> dict:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": digest}

    inventory = []
    # manifest.json cannot hash itself; SCHEMA.md is hand-maintained
    # documentation and edits to it must not invalidate a good build.
    for path in sorted(program_dir.rglob("*")):
        if path.is_file() and path.name not in ("manifest.json", "SCHEMA.md"):
            inventory.append(file_entry(path))
    total_trade_rows = sum(sum(result["trade_rows_by_batch"].values()) for result in universe_results.values())
    flag_rows = [flag for result in universe_results.values() for flag in result["flags"]]
    flag_counts: dict[str, int] = {}
    for flag in flag_rows:
        flag_counts[flag["code"]] = flag_counts.get(flag["code"], 0) + 1
    open_flags = [
        {"universe": universe, **flag}
        for universe, result in universe_results.items()
        for flag in result["flags"][:10]
    ]
    manifest = {
        "program_version": PROGRAM_VERSION,
        "engine_version": ENGINE_VERSION,
        "generated_at_unix": int(started),
        "generated_at": unix_to_iso(int(started)),
        "generated_from": "data/kalshi/markets.jsonl",
        "participants": len(variants),
        "batches": batches,
        "variant_count": len(variants),
        "trade_rows_total": total_trade_rows,
        "universes": {
            universe: {
                "competition_id": UNIVERSES[universe]["competition_id"],
                "kind": UNIVERSES[universe]["kind"],
                "data_tier": UNIVERSES[universe]["data_tier"],
                "markets_used": result["markets_used"],
                "candle_events": result["events"],
                "runtime_seconds": result["runtime_seconds"],
                "trade_rows": sum(result["trade_rows_by_batch"].values()),
                "combined_ledger_sha256": result["combined_ledger_sha256"],
                "open_positions": len(result["open_position_rows"]),
            }
            for universe, result in universe_results.items()
        },
        "replay": replay_proof,
        "decision_clock": {
            "rule": (
                "A decision at candle end T uses only that market's candles with "
                "end_period_ts <= T, and only when T is strictly before settlement_ts. "
                "Same rule as the primary competitions."
            ),
            "prior_window": PROGRAM_PRIOR_WINDOW,
            "settlement_rule": "Official result applied only at settlement_ts, after the decision loop.",
            "channels": {
                "event_quotes": "Sibling contracts of the same event in the same universe: latest candle with end_period_ts <= T.",
                "settled_pool": "Markets (any universe) whose settlement_ts < T, with their official result.",
                "schedule": "Event strike_date when Kalshi publishes one on a whole minute; close_time is never used.",
                "guards": "The engine raises if any channel contains a record stamped after T (or a pool record at/after T).",
            },
        },
        "research": {
            "file": "data/sim/program/research.json",
            "overall_counts": research["overall_counts"],
            "multiple_testing": research["multiple_testing"],
            "families": len(research["families"]),
        },
        "flag_counts": flag_counts,
        "flag_samples": open_flags[:40],
        "disclaimer": (
            "Every participant, trade, position, and P&L figure in the program is simulated. "
            "None of it is a Kalshi order, a Kalshi user, or a real fill. Market prices and "
            "results are Kalshi data only where a source URL is shown."
        ),
        "files": inventory,
    }
    manifest_path = program_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    docs_dir = root / "docs"
    if docs_dir.is_dir():
        (docs_dir / "RESEARCH.md").write_text(render_markdown(research, manifest))
    log(f"program done in {round(time.time() - started, 1)}s: {len(variants)} participants, "
        f"{total_trade_rows} ledger rows, replay {replay_proof['status']}")
    return manifest
