# Kalshi field sources

Collected by `simcomp/collect.py` from the public Trade API. No API key.

Base URL: `https://external-api.kalshi.com/trade-api/v2`

| Stored field | Official source | Notes |
| --- | --- | --- |
| `market` object in `markets.jsonl` | `GET /markets/{ticker}` or `GET /historical/markets?series_ticker=` | The exact URL is `source_url`. Live and historical rows are not merged. If both exist, the live payload is the one stored, and the tier says `live`. |
| `candles` | `GET /series/{series}/markets/{ticker}/candlesticks` or `GET /historical/markets/{ticker}/candlesticks` | URL is `candle_source_url`. Live candles use `close_dollars` and `volume_fp`. Historical candles use `close` and `volume`. The parser accepts both. |
| `series.fee_type`, `series.fee_multiplier` | `GET /series/{ticker}` | Not computed. |
| `series.settlement_sources` | `GET /series/{ticker}` | Named by Kalshi. Nobel series point at nobelprize.org. |
| `series.contract_url`, `contract_terms_url` | `GET /series/{ticker}` | Kalshi-hosted PDFs. |
| Order books in `orderbooks.json` | `GET /markets/{ticker}/orderbook` at `fetched_at` | Later than the candle closes. Not a decision input. |
| `historical_cutoff` | `GET /historical/cutoff` | Markets settled before `market_settled_ts` are queried on the historical route. |
| Exchange status | `GET /exchange/status` | Stored so a closed exchange is visible. |

Simulated fields live under `data/sim/`. They are not Kalshi fields. `later_official_result` on a trade row is copied from the stored market after the decision loop and is marked unused at decision time.

Empty candle prices stay empty. A zero bid is treated as no bid. Nothing is interpolated.
