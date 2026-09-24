"""Collect public Kalshi market data. No API key. No paid endpoint.

Raw responses are stored. Missing responses are recorded and left missing.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from simcomp.kalshi_parse import market_from_payload, parse_candle
from simcomp.money import dollars_or_none, parse_unix

BASE = "https://external-api.kalshi.com/trade-api/v2"
USER_AGENT = (
    "SIM-COMP-NOBEL-PRIZE/1.0 "
    "(research; +https://github.com/buffedlizard55-lab/SIM-COMP-NOBEL-PRIZE)"
)
# Explicit union in case series pagination is truncated. Discovery still scans titles.
KNOWN_NOBEL_SERIES = [
    "KXNOBELECON",
    "KXNOBELPEACE",
    "KXNOBELMED",
    "KXNOBELCHEM",
    "KXNOBELLIT",
    "KXNOBELPHYSICS",
]
# Settled-panel series. Each is requested directly. A 404 is recorded, not filled.
PANEL_SERIES = ["KXHIGHNY", "KXFEDDECISION"]
PANEL_CAP_PER_SERIES = 25
REQUEST_PAUSE = 0.2


class KalshiClient:
    def __init__(self):
        self.calls = 0
        self.fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.fetched_at_unix = int(datetime.now(timezone.utc).timestamp())

    def get(self, path: str, params: dict | None = None, retries: int = 4):
        query = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None and v != ""})
        url = BASE + path + (("?" + query) if query else "")
        last_error = None
        for attempt in range(retries):
            request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    self.calls += 1
                    body = response.read()
                    time.sleep(REQUEST_PAUSE)
                    return response.status, json.loads(body.decode("utf-8")), url
            except urllib.error.HTTPError as exc:
                self.calls += 1
                raw = exc.read().decode("utf-8", errors="replace")
                time.sleep(REQUEST_PAUSE)
                if exc.code in (429, 500, 502, 503, 504) and attempt + 1 < retries:
                    time.sleep(1.5 * (attempt + 1))
                    last_error = f"HTTP {exc.code}"
                    continue
                try:
                    parsed = json.loads(raw) if raw else {"error": f"HTTP {exc.code}"}
                except json.JSONDecodeError:
                    parsed = {"error": f"HTTP {exc.code}", "body": raw[:500]}
                return exc.code, parsed, url
            except Exception as exc:  # noqa: BLE001 — recorded, not hidden
                last_error = f"{type(exc).__name__}: {exc}"
                time.sleep(1.5 * (attempt + 1))
        return 0, {"error": last_error or "request failed"}, url

    def paginate(self, path: str, params: dict, key: str, cap: int = 5000):
        rows = []
        cursor = ""
        pages = 0
        failures = []
        while pages < 40 and len(rows) < cap:
            page_params = dict(params)
            page_params["limit"] = params.get("limit", 200)
            if cursor:
                page_params["cursor"] = cursor
            status, body, url = self.get(path, page_params)
            pages += 1
            if status != 200 or not isinstance(body, dict):
                failures.append({"url": url, "status": status, "body": body})
                break
            batch = body.get(key) or []
            if not isinstance(batch, list):
                failures.append({"url": url, "status": status, "body": "unexpected shape"})
                break
            rows.extend(batch)
            cursor = body.get("cursor") or ""
            if not cursor or not batch:
                break
        if len(rows) >= cap:
            failures.append({
                "url": path,
                "status": 200,
                "body": f"stopped at cap {cap}",
                "params": {
                    key: params.get(key)
                    for key in ("series_ticker", "event_ticker", "status", "mve_filter")
                    if params.get(key)
                },
            })
        return rows, failures


def _is_nobel(series: dict) -> bool:
    ticker = str(series.get("ticker") or "").upper()
    title = str(series.get("title") or "").upper()
    return "NOBEL" in ticker or "NOBEL" in title


def _volume(raw: dict):
    return dollars_or_none(raw.get("volume_fp") if raw.get("volume_fp") not in (None, "") else raw.get("volume"))


def _lifespan_seconds(raw: dict) -> int | None:
    open_ts = parse_unix(raw.get("open_time"))
    end_ts = parse_unix(raw.get("settlement_ts")) or parse_unix(raw.get("close_time"))
    if open_ts is None or end_ts is None:
        return None
    return end_ts - open_ts


def choose_interval(raw: dict, now: int | None = None) -> int:
    """Hourly candles for short lives and for markets that opened in the last two days.

    A daily candle has not closed yet for a market listed today, so a daily
    request returns an empty list. That empty list is not a price of zero.
    """
    open_ts = parse_unix(raw.get("open_time"))
    settlement = parse_unix(raw.get("settlement_ts"))
    end = settlement if settlement is not None else now
    if end is None:
        end = parse_unix(raw.get("close_time"))
    span = (end - open_ts) if open_ts is not None and end is not None else None
    if span is None or span <= 10 * 86400:
        return 60
    if settlement is None and open_ts is not None and now is not None and (now - open_ts) <= 2 * 86400:
        return 60
    return 1440


def collect(root: Path) -> dict:
    client = KalshiClient()
    kalshi = root / "data" / "kalshi"
    raw_dir = kalshi / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    failures = []

    status_code, exchange, exchange_url = client.get("/exchange/status")
    cutoff_code, cutoff, cutoff_url = client.get("/historical/cutoff")
    (raw_dir / "exchange_status.json").write_text(json.dumps({"status": status_code, "url": exchange_url, "body": exchange}, indent=2))
    (raw_dir / "cutoff.json").write_text(json.dumps({"status": cutoff_code, "url": cutoff_url, "body": cutoff}, indent=2))
    if status_code != 200:
        failures.append({"url": exchange_url, "status": status_code, "body": exchange})
    if cutoff_code != 200:
        failures.append({"url": cutoff_url, "status": cutoff_code, "body": cutoff})

    series_rows, series_failures = client.paginate("/series", {"limit": 200}, "series", cap=5000)
    failures.extend(series_failures)
    by_ticker = {}
    for row in series_rows:
        ticker = row.get("ticker")
        if ticker and _is_nobel(row):
            row = dict(row)
            row["_role"] = "nobel"
            by_ticker[ticker] = row
    for ticker in KNOWN_NOBEL_SERIES:
        if ticker not in by_ticker:
            code, body, url = client.get(f"/series/{ticker}")
            if code == 200 and isinstance(body, dict) and body.get("series"):
                row = dict(body["series"])
                row["_role"] = "nobel"
                by_ticker[ticker] = row
            else:
                failures.append({"url": url, "status": code, "body": body, "note": "known Nobel series was not returned"})
    for ticker in PANEL_SERIES:
        if ticker in by_ticker:
            continue
        code, body, url = client.get(f"/series/{ticker}")
        if code == 200 and isinstance(body, dict) and body.get("series"):
            row = dict(body["series"])
            row["_role"] = "panel"
            by_ticker[ticker] = row
        else:
            failures.append({"url": url, "status": code, "body": body, "note": "panel series not available"})

    events = []
    market_raw = {}
    for ticker, series in sorted(by_ticker.items()):
        event_rows, event_failures = client.paginate(
            "/events", {"series_ticker": ticker, "limit": 200}, "events", cap=500
        )
        failures.extend(event_failures)
        for event in event_rows:
            event = dict(event)
            event["_role"] = series["_role"]
            events.append(event)
        live_rows, live_failures = client.paginate(
            "/markets", {"series_ticker": ticker, "limit": 200, "mve_filter": "exclude"}, "markets", cap=2000
        )
        failures.extend(live_failures)
        # Historical filters are mutually exclusive. mve_filter with series_ticker
        # returns HTTP 400. Multivariate rows are dropped later, not by this query.
        hist_rows, hist_failures = client.paginate(
            "/historical/markets",
            {"series_ticker": ticker, "limit": 200},
            "markets",
            cap=2000,
        )
        failures.extend(hist_failures)
        for raw in hist_rows:
            raw = dict(raw)
            raw["_tier"] = "historical"
            raw["_role"] = series["_role"]
            if raw.get("ticker"):
                market_raw[raw["ticker"]] = raw
        for raw in live_rows:
            raw = dict(raw)
            raw["_tier"] = "live"
            raw["_role"] = series["_role"]
            if raw.get("ticker"):
                # Live payload wins if both exist. The historical copy is not silently merged.
                market_raw[raw["ticker"]] = raw
        # Event fallback is for Nobel series only. Panel series can have hundreds of
        # events; the panel is a capped sample from the series query, not every event.
        if series.get("_role") == "nobel":
            covered_events = {row.get("event_ticker") for row in market_raw.values()}
            for event in event_rows:
                event_ticker = event.get("event_ticker")
                if not event_ticker or event_ticker in covered_events:
                    continue
                extra, extra_failures = client.paginate(
                    "/historical/markets",
                    {"event_ticker": event_ticker, "limit": 200},
                    "markets",
                    cap=1000,
                )
                failures.extend(extra_failures)
                for raw in extra:
                    raw = dict(raw)
                    raw["_tier"] = "historical"
                    raw["_role"] = series["_role"]
                    if raw.get("ticker") and raw["ticker"] not in market_raw:
                        market_raw[raw["ticker"]] = raw

    selected = []
    panel_kept = {ticker: 0 for ticker in PANEL_SERIES}
    panel_candidates = []
    for raw in market_raw.values():
        if raw.get("mve_collection_ticker") or raw.get("mve_selected_legs"):
            failures.append({
                "url": "",
                "status": 200,
                "body": f"excluded multivariate market {raw.get('ticker')}",
            })
            continue
        if raw.get("_role") == "nobel":
            selected.append(raw)
            continue
        status = str(raw.get("status") or "").lower()
        result = str(raw.get("result") or "").lower()
        if status not in ("determined", "finalized", "amended") or result not in ("yes", "no"):
            continue
        span = _lifespan_seconds(raw)
        volume = _volume(raw) or 0
        if span is None or span < 6 * 3600 or volume <= 0:
            continue
        if parse_unix(raw.get("settlement_ts")) is None:
            continue
        panel_candidates.append(raw)
    panel_candidates.sort(key=lambda raw: (-float(_volume(raw) or 0), raw.get("ticker") or ""))
    for raw in panel_candidates:
        series_ticker = raw.get("series_ticker") or ""
        # series_ticker may be absent on historical rows; fall back to event prefix.
        if series_ticker not in panel_kept:
            for known in PANEL_SERIES:
                if str(raw.get("ticker") or "").startswith(known) or str(raw.get("event_ticker") or "").startswith(known):
                    series_ticker = known
                    break
        if series_ticker not in panel_kept:
            continue
        if panel_kept[series_ticker] >= PANEL_CAP_PER_SERIES:
            continue
        panel_kept[series_ticker] += 1
        raw["_role"] = "panel"
        raw["_panel_rank_rule"] = (
            f"top {PANEL_CAP_PER_SERIES} by volume_fp among settled binary markets returned for {series_ticker} "
            "(historical query capped at 2000 rows), with settlement_ts, lifespan >= 6h, and volume > 0"
        )
        selected.append(raw)

    lines = []
    candle_ok = 0
    for raw in sorted(selected, key=lambda item: item.get("ticker") or ""):
        ticker = raw["ticker"]
        series_ticker = raw.get("series_ticker") or ""
        if not series_ticker:
            for known in list(by_ticker):
                if ticker.startswith(known) or str(raw.get("event_ticker") or "").startswith(known):
                    series_ticker = known
                    raw["series_ticker"] = known
                    break
        series = by_ticker.get(series_ticker, {})
        interval = choose_interval(raw, client.fetched_at_unix)
        open_ts = parse_unix(raw.get("open_time")) or (client.fetched_at_unix - 120 * 86400)
        end_ts = client.fetched_at_unix
        settlement_ts = parse_unix(raw.get("settlement_ts"))
        if settlement_ts:
            end_ts = min(end_ts, settlement_ts + 3600)
        params = {
            "start_ts": max(0, open_ts - 3600),
            "end_ts": end_ts,
            "period_interval": interval,
        }
        tier = raw.get("_tier") or "live"
        candle_body = None
        candle_url = ""
        candle_status = 0
        if tier == "historical":
            candle_status, candle_body, candle_url = client.get(f"/historical/markets/{ticker}/candlesticks", params)
        else:
            if series_ticker:
                candle_status, candle_body, candle_url = client.get(
                    f"/series/{series_ticker}/markets/{ticker}/candlesticks", params
                )
            if candle_status == 404 or not series_ticker:
                candle_status, candle_body, candle_url = client.get(
                    f"/historical/markets/{ticker}/candlesticks", params
                )
                if candle_status == 200:
                    tier = "historical"
        candle_note = ""
        if (
            candle_status == 200
            and isinstance(candle_body, dict)
            and not candle_body.get("candlesticks")
            and interval == 1440
        ):
            # A daily window can be empty when the market opened today. Retry hourly
            # only if the request stays inside Kalshi's 5000-candle cap. An empty
            # daily list is not a price, and an oversized hourly request is not one either.
            span = params["end_ts"] - params["start_ts"]
            if span / 60 <= 5000:
                params["period_interval"] = 60
                interval = 60
            else:
                candle_note = (
                    "Daily candlesticks were empty. Hourly retry skipped because the window "
                    f"would be {span / 60:.0f} candles, above the 5000 cap. No price was invented."
                )
            if tier == "historical":
                candle_status, candle_body, candle_url = client.get(
                    f"/historical/markets/{ticker}/candlesticks", params
                )
            elif series_ticker:
                candle_status, candle_body, candle_url = client.get(
                    f"/series/{series_ticker}/markets/{ticker}/candlesticks", params
                )
        candles = []
        if candle_status == 200 and isinstance(candle_body, dict):
            for item in candle_body.get("candlesticks") or []:
                try:
                    candles.append(parse_candle(item))
                except Exception as exc:  # noqa: BLE001
                    failures.append({"url": candle_url, "status": 200, "body": f"candle parse {ticker}: {exc}"})
            candle_ok += 1
        else:
            failures.append({"url": candle_url, "status": candle_status, "body": candle_body, "ticker": ticker})
        market = market_from_payload(
            raw,
            tier=tier,
            source_url=f"{BASE}/markets/{ticker}" if tier == "live" else f"{BASE}/historical/markets/{ticker}",
            series=series,
        )
        market.candle_source_url = candle_url
        market.universe = "nobel" if raw.get("_role") == "nobel" else "panel"
        record = {
            "ticker": ticker,
            "universe": market.universe,
            "tier": tier,
            "role": raw.get("_role"),
            "panel_rank_rule": raw.get("_panel_rank_rule"),
            "source_url": market.source_url,
            "candle_source_url": candle_url,
            "candle_status": candle_status,
            "candle_note": candle_note,
            "period_interval": interval,
            "series": {
                "ticker": series.get("ticker"),
                "title": series.get("title"),
                "category": series.get("category"),
                "fee_type": series.get("fee_type"),
                "fee_multiplier": series.get("fee_multiplier"),
                "frequency": series.get("frequency"),
                "settlement_sources": series.get("settlement_sources"),
                "contract_url": series.get("contract_url"),
                "contract_terms_url": series.get("contract_terms_url"),
            },
            "market": raw,
            "candles": candle_body.get("candlesticks") if isinstance(candle_body, dict) else [],
        }
        # Drop collection bookkeeping keys from the stored official payload copy.
        official = {k: v for k, v in raw.items() if not str(k).startswith("_")}
        record["market"] = official
        lines.append(record)
        _ = candles  # parsed once here so a bad candle fails collection, not a later silent skip

    orderbooks = []
    open_nobel = [
        row for row in lines
        if row["universe"] == "nobel" and str(row["market"].get("status") or "").lower() in ("active", "open")
    ]
    open_nobel.sort(key=lambda row: -float(_volume(row["market"]) or 0))
    for row in open_nobel[:15]:
        ticker = row["ticker"]
        code, body, url = client.get(f"/markets/{ticker}/orderbook")
        orderbooks.append({
            "ticker": ticker,
            "fetched_at": client.fetched_at,
            "status": code,
            "url": url,
            "body": body if code == 200 else {"error": body},
            "used_for_simulated_decisions": False,
            "note": "Fetch-time order book. Later than the candle closes used for decisions.",
        })
        if code != 200:
            failures.append({"url": url, "status": code, "body": body, "ticker": ticker})

    kalshi.mkdir(parents=True, exist_ok=True)
    jsonl_path = kalshi / "markets.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for record in lines:
            handle.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n")
    (kalshi / "series.json").write_text(json.dumps(list(by_ticker.values()), indent=2))
    (kalshi / "events.json").write_text(json.dumps(events, indent=2))
    (kalshi / "orderbooks.json").write_text(json.dumps(orderbooks, indent=2))
    manifest = {
        "fetched_at": client.fetched_at,
        "fetched_at_unix": client.fetched_at_unix,
        "base_url": BASE,
        "calls": client.calls,
        "exchange_status_url": exchange_url,
        "exchange_status": exchange if status_code == 200 else None,
        "cutoff_url": cutoff_url,
        "historical_cutoff": cutoff if cutoff_code == 200 else None,
        "nobel_series": sorted(t for t, row in by_ticker.items() if row.get("_role") == "nobel"),
        "panel_series": sorted(t for t, row in by_ticker.items() if row.get("_role") == "panel"),
        "panel_kept": panel_kept,
        "panel_cap_per_series": PANEL_CAP_PER_SERIES,
        "markets_stored": len(lines),
        "markets_with_candles": candle_ok,
        "events_stored": len(events),
        "orderbooks_stored": len(orderbooks),
        "failure_count": len(failures),
        "scope": {
            "nobel": "Every non-multivariate market returned by GET /markets and GET /historical/markets for series whose ticker or title contains NOBEL, plus the known Nobel series list. Historical requests do not send mve_filter; that parameter is mutually exclusive with series_ticker and event_ticker and returns HTTP 400.",
            "panel": (
                "Not a complete Kalshi history. For each panel series, the collector keeps at most "
                f"{PANEL_CAP_PER_SERIES} settled binary markets with a settlement timestamp, lifespan of at least 6 hours, "
                "and volume greater than zero, highest volume first, among the first 2000 historical rows returned for that series. This is not a global volume ranking."
            ),
            "not_invented": "Failed requests are listed in failures.json. No price, volume, or result is filled in.",
        },
        "field_sources": {
            "market": "Kalshi Trade API v2 market object, live or historical endpoint named in source_url",
            "candles": "Kalshi candlestick object from candle_source_url. Live schema uses close_dollars and volume_fp. Historical schema uses close and volume.",
            "fee_type": "series.fee_type from GET /series/{ticker}",
            "fee_multiplier": "series.fee_multiplier from GET /series/{ticker}",
            "settlement_sources": "series.settlement_sources from GET /series/{ticker}",
            "orderbook": "GET /markets/{ticker}/orderbook at fetched_at. Not a decision input.",
        },
    }
    (kalshi / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (kalshi / "failures.json").write_text(json.dumps(failures, indent=2))
    print(json.dumps({k: manifest[k] for k in ("fetched_at", "calls", "markets_stored", "markets_with_candles", "failure_count", "nobel_series", "panel_series")}, indent=2))
    return manifest
