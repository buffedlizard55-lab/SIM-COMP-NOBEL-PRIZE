"""Run the simulated competitions from stored Kalshi files and write the site bundle."""

from __future__ import annotations

import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path

from simcomp import ENGINE_VERSION
from simcomp.engine import SimConfig, attach_later_results, run_competition
from simcomp.kalshi_parse import market_from_payload, parse_candle
from simcomp.money import money
from simcomp.strategies import PARTICIPANTS, clone_strategies, default_strategies

ROOT_DEFAULT = Path(__file__).resolve().parents[1]


def load_records(root: Path) -> list[dict]:
    path = root / "data" / "kalshi" / "markets.jsonl"
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def record_to_market(record: dict):
    series = record.get("series") or {}
    market = market_from_payload(
        record.get("market") or {},
        tier=record.get("tier") or "",
        source_url=record.get("source_url") or "",
        series=series,
    )
    market.candle_source_url = record.get("candle_source_url") or ""
    market.universe = record.get("universe") or ""
    market.candles = []
    for raw in record.get("candles") or []:
        try:
            market.candles.append(parse_candle(raw))
        except Exception:
            continue
    return market


def _configs() -> list[tuple[SimConfig, str, dict | None]]:
    """(config, universe, strategy overrides)."""
    rows = []

    def add(config: SimConfig, universe: str, overrides=None):
        rows.append((config, universe, overrides))

    add(SimConfig(
        competition_id="nobel-forward-primary",
        title="Nobel markets, forward simulation",
        kind="forward_simulation",
        data_tier="live_kalshi",
        assumption_note="Primary forward run. Fills at the closing quote. Taker fee interpretation on. Positions marked to the closing bid. Outcomes are not known.",
        primary=True,
    ), "nobel_forward")
    add(SimConfig(
        competition_id="nobel-settled-primary",
        title="Settled Nobel markets, historical backtest",
        kind="historical_backtest",
        data_tier="historical_kalshi",
        assumption_note="Primary historical run on settled Nobel markets. Official result is applied only at settlement_ts.",
        primary=True,
    ), "nobel_settled")
    add(SimConfig(
        competition_id="panel-settled-primary",
        title="Settled panel, historical backtest",
        kind="historical_backtest",
        data_tier="historical_kalshi",
        assumption_note="Primary run on the capped settled panel (not a complete Kalshi history). Same rules as the Nobel historical run.",
        primary=True,
    ), "panel_settled")
    for universe, prefix, tier, kind in (
        ("nobel_forward", "nobel-forward", "live_kalshi", "assumption_run"),
        ("nobel_settled", "nobel-settled", "historical_kalshi", "assumption_run"),
        ("panel_settled", "panel-settled", "historical_kalshi", "assumption_run"),
    ):
        add(SimConfig(
            competition_id=f"{prefix}-fee-off",
            title=f"{prefix} with fees off",
            kind=kind,
            data_tier=tier,
            fees_enabled=False,
            assumption_note="Same decisions and fills as the primary size rules, but the taker fee is not charged. Not the primary leaderboard.",
            primary=False,
        ), universe)
        add(SimConfig(
            competition_id=f"{prefix}-size-250",
            title=f"{prefix} with $250 entry target",
            kind=kind,
            data_tier=tier,
            target_entry_spend=Decimal("250"),
            max_cost_per_market=Decimal("750"),
            assumption_note="Entry budget raised from $100 to $250 and the per-market cost cap from $300 to $750. Fees stay on. Not the primary leaderboard.",
            primary=False,
        ), universe)
    add(SimConfig(
        competition_id="panel-settled-momentum-5c",
        title="Settled panel, momentum threshold 0.05",
        kind="assumption_run",
        data_tier="historical_kalshi",
        assumption_note="Momentum and volume-momentum require a 0.05 move instead of 0.02. Other strategies are unchanged. Shows threshold sensitivity.",
        primary=False,
    ), "panel_settled", {"momentum": {"min_move": "0.05"}, "volume_momentum": {"min_move": "0.05"}})
    add(SimConfig(
        competition_id="panel-settled-fill-at-trade",
        title="Settled panel, fill at last trade",
        kind="assumption_run",
        data_tier="historical_kalshi",
        fill_model="last_trade",
        assumption_note="Fills use the candle's last trade price when one exists. No fallback to the quote. Candles without a trade are not filled.",
        primary=False,
    ), "panel_settled")
    return rows


def _bucket(market) -> str:
    if market.universe == "nobel" and market.settled_result:
        return "nobel_settled"
    if market.universe == "nobel":
        return "nobel_forward"
    if market.universe == "panel" and market.settled_result:
        return "panel_settled"
    return ""


def input_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            flat = {}
            for key, value in row.items():
                if isinstance(value, (dict, list)):
                    flat[key] = json.dumps(value, ensure_ascii=False)
                else:
                    flat[key] = value
            writer.writerow(flat)


def build(root: Path | None = None) -> dict:
    root = root or ROOT_DEFAULT
    records = load_records(root)
    markets = [record_to_market(record) for record in records]
    grouped = {"nobel_forward": [], "nobel_settled": [], "panel_settled": []}
    for market in markets:
        bucket = _bucket(market)
        if bucket:
            grouped[bucket].append(market)

    competitions = []
    all_trades = []
    all_positions = []
    all_equity = []
    all_market_results = []
    all_flags = []
    comparisons = []
    for config, universe, overrides in _configs():
        result = run_competition(grouped[universe], config, clone_strategies(overrides))
        attach_later_results(result, grouped[universe])
        competitions.append({
            "config": result["config"],
            "leaderboard": result["leaderboard"],
            "markets_used": result["markets_used"],
            "trade_count": len(result["trades"]),
            "flag_count": len(result["flags"]),
        })
        all_trades.extend(result["trades"])
        all_positions.extend(result["positions"])
        all_equity.extend(result["equity"])
        all_market_results.extend(result["market_results"])
        for flag in result["flags"]:
            flag = dict(flag)
            flag["competition_id"] = config.competition_id
            all_flags.append(flag)
        comparisons.append({
            "competition_id": config.competition_id,
            "primary": config.primary,
            "kind": config.kind,
            "assumption_note": config.assumption_note,
            "leaderboard": [
                {
                    "participant_id": row["participant_id"],
                    "strategy_id": row["strategy_id"],
                    "ending_equity": row["ending_equity"],
                    "realized_pnl": row["realized_pnl"],
                    "unrealized_pnl": row["unrealized_pnl"],
                    "fees": row["fees"],
                    "trade_count": row["trade_count"],
                    "rank": row["rank"],
                }
                for row in result["leaderboard"]
            ],
        })

    manifest_path = root / "data" / "kalshi" / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    failures_path = root / "data" / "kalshi" / "failures.json"
    failures = json.loads(failures_path.read_text()) if failures_path.exists() else []
    for failure in failures:
        all_flags.append({
            "code": "collection_failure",
            "severity": "review",
            "message": json.dumps(failure)[:500],
            "market_ticker": failure.get("ticker"),
            "competition_id": "",
        })

    market_index = []
    candle_dir = root / "data" / "sim" / "candles"
    candle_dir.mkdir(parents=True, exist_ok=True)
    traded = {row["market_ticker"] for row in all_trades}
    for record, market in zip(records, markets):
        official = record.get("market") or {}
        market_index.append({
            "ticker": market.ticker,
            "title": market.title,
            "subtitle": market.subtitle,
            "event_ticker": market.event_ticker,
            "series_ticker": market.series_ticker,
            "universe": market.universe,
            "tier": market.tier,
            "status": market.status,
            "result": market.result,
            "result_is_official_kalshi": True,
            "result_is_simulated": False,
            "market_type": market.market_type,
            "open_time": official.get("open_time"),
            "close_time": official.get("close_time"),
            "settlement_ts": official.get("settlement_ts"),
            "volume_fp": official.get("volume_fp"),
            "open_interest_fp": official.get("open_interest_fp"),
            "last_price_dollars": official.get("last_price_dollars"),
            "yes_bid_dollars": official.get("yes_bid_dollars"),
            "yes_ask_dollars": official.get("yes_ask_dollars"),
            "rules_primary": market.rules_primary,
            "fee_type": market.fee_type,
            "fee_multiplier": market.fee_multiplier,
            "settlement_sources": market.settlement_sources,
            "source_url": market.source_url,
            "candle_source_url": market.candle_source_url,
            "contract_url": (record.get("series") or {}).get("contract_url"),
            "contract_terms_url": (record.get("series") or {}).get("contract_terms_url"),
            "kalshi_series_url": f"https://kalshi.com/markets/{market.series_ticker.lower()}" if market.series_ticker else "",
            "candle_count": len(market.candles),
            "period_interval": record.get("period_interval"),
            "simulated": False,
            "data_class": "kalshi_market_data",
        })
        if market.ticker in traded or market.universe == "nobel":
            compact = []
            for candle in market.candles:
                compact.append({
                    "end_period_ts": candle.end_period_ts,
                    "yes_bid_close": money(candle.yes_bid_close) if candle.yes_bid_close is not None else None,
                    "yes_ask_close": money(candle.yes_ask_close) if candle.yes_ask_close is not None else None,
                    "trade_close": money(candle.trade_close) if candle.trade_close is not None else None,
                    "volume": money(candle.volume) if candle.volume is not None else None,
                    "open_interest": money(candle.open_interest) if candle.open_interest is not None else None,
                    "source": "kalshi_candlestick",
                    "used_high_low_for_fills": False,
                })
            (candle_dir / f"{market.ticker}.json").write_text(json.dumps(compact, separators=(",", ":")))

    participants = []
    strategy_by_id = {s.id: s for s in default_strategies()}
    for username, strategy_id, display in PARTICIPANTS:
        strategy = strategy_by_id[strategy_id]
        participants.append({
            "id": username,
            "username": username,
            "display_name": display,
            "strategy_id": strategy_id,
            "simulated": True,
            "real_kalshi_account": False,
            "note": "Simulated username. Not a Kalshi account and not a real person.",
            "strategy": strategy.public(),
        })

    jsonl = root / "data" / "kalshi" / "markets.jsonl"
    summary = {
        "engine_version": ENGINE_VERSION,
        "generated_from": "data/kalshi/markets.jsonl",
        "input_sha256": input_hash(jsonl) if jsonl.exists() else "",
        "fetched_at": manifest.get("fetched_at"),
        "disclaimer": (
            "Every participant, trade, position, and P&L figure in this competition is simulated. "
            "None of it is a Kalshi order, a Kalshi user, or a real fill. "
            "Market prices, results, and volumes are Kalshi data only where a source URL is shown."
        ),
        "participants_trade_with_each_other": False,
        "competitions": competitions,
        "participants": participants,
        "strategies": [s.public() for s in default_strategies()],
        "data_quality": {
            "fetched_at": manifest.get("fetched_at"),
            "exchange_status": manifest.get("exchange_status"),
            "historical_cutoff": manifest.get("historical_cutoff"),
            "markets_stored": manifest.get("markets_stored", 0),
            "markets_with_candle_responses": manifest.get("markets_with_candles", 0),
            "collection_failures": manifest.get("failure_count", 0),
            "nobel_series": manifest.get("nobel_series", []),
            "panel_series": manifest.get("panel_series", []),
            "panel_kept": manifest.get("panel_kept", {}),
            "scope": manifest.get("scope", {}),
            "universes": {key: len(value) for key, value in grouped.items()},
            "status": "ok" if records else "missing_kalshi_snapshot",
        },
        "sources": [
            {"name": "Kalshi Trade API v2", "url": "https://external-api.kalshi.com/trade-api/v2", "role": "market data"},
            {"name": "Kalshi market data quick start", "url": "https://docs.kalshi.com/getting_started/quick_start_market_data", "role": "public endpoints, no API key"},
            {"name": "Kalshi historical data", "url": "https://docs.kalshi.com/getting_started/historical_data", "role": "cutoff and historical routes"},
            {"name": "Kalshi fee schedule", "url": "https://kalshi.com/fee-schedule", "role": "taker fee range used to interpret quadratic fees"},
            {"name": "Nobel Prize API", "url": "https://api.nobelprize.org/2.1/nobelPrizes", "role": "laureates and motivations"},
            {"name": "Nomination archive", "url": "https://www.nobelprize.org/nomination/archive/", "role": "other candidates, where the 50-year seal is open"},
        ],
        "assumptions": [config.assumption_note for config, _u, _o in _configs()],
        "research_questions": [
            {"question": "How do different strategies perform under different market conditions?", "view": "compare"},
            {"question": "How does a strategy perform against other simulated strategies?", "view": "leaderboard"},
            {"question": "How do market price movements affect simulated positions?", "view": "markets"},
            {"question": "What happens when strategies enter or exit at different prices?", "view": "compare"},
            {"question": "How sensitive are results to timing, position sizing, and available information?", "view": "compare"},
            {"question": "Which assumptions materially affect simulation results?", "view": "compare"},
            {"question": "Can the same simulation be reproduced from the stored market data and strategy decisions?", "view": "quality"},
        ],
    }
    sim = root / "data" / "sim"
    sim.mkdir(parents=True, exist_ok=True)
    (sim / "summary.json").write_text(json.dumps(summary, indent=2))
    (sim / "trades.json").write_text(json.dumps(all_trades))
    (sim / "positions.json").write_text(json.dumps(all_positions))
    (sim / "equity.json").write_text(json.dumps(all_equity))
    (sim / "market_results.json").write_text(json.dumps(all_market_results))
    (sim / "market_index.json").write_text(json.dumps(market_index))
    (sim / "comparisons.json").write_text(json.dumps(comparisons, indent=2))
    (sim / "flags.json").write_text(json.dumps(all_flags, indent=2))
    write_csv(sim / "trades.csv", all_trades)
    write_csv(sim / "leaderboard.csv", [row for comp in competitions for row in (
        {**item, "competition_id": comp["config"]["competition_id"]} for item in comp["leaderboard"]
    )])
    _write_leaderboard_md(sim / "LEADERBOARD.md", competitions, summary)
    print(json.dumps({
        "competitions": len(competitions),
        "trades": len(all_trades),
        "markets": len(markets),
        "universes": summary["data_quality"]["universes"],
    }, indent=2))
    return summary


def _write_leaderboard_md(path: Path, competitions, summary) -> None:
    lines = [
        "# Simulated leaderboards",
        "",
        summary["disclaimer"],
        "",
        f"Kalshi snapshot: {summary.get('fetched_at') or 'not collected'}",
        "",
    ]
    for comp in competitions:
        if not comp["config"].get("primary"):
            continue
        lines.append(f"## {comp['config']['title']}")
        lines.append("")
        lines.append(f"Id: `{comp['config']['competition_id']}`. Kind: {comp['config']['kind']}. Markets used: {comp['markets_used']}.")
        lines.append("")
        lines.append("| Rank | Participant | Strategy | Ending equity | Realized | Unrealized | Fees | Trades |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for row in comp["leaderboard"]:
            lines.append(
                f"| {row['rank']} | {row['participant_id']} | {row['strategy_id']} | {row['ending_equity']} | "
                f"{row['realized_pnl']} | {row['unrealized_pnl']} | {row['fees']} | {row['trade_count']} |"
            )
        lines.append("")
    path.write_text("\n".join(lines))
