# Limitations for the next session

Written 2026-09-24, after the first working desk. These are the gaps that still block a stronger project. They are not hidden in the leaderboard.

## Collection

1. This sandbox cannot open TLS to `api.nobelprize.org`, `www.nobelprize.org`, or the Kalshi API hosts (`SSL_ERROR_SYSCALL`). Collection runs in GitHub Actions, where the public API is reachable. If that workflow did not commit a snapshot, the leaderboard files will be missing until someone runs `python scripts/refresh.py` on a network that can reach Kalshi.
2. The Nobel market universe is complete only for series the collector actually received. A series whose title does not contain "NOBEL" and that is not in the known list will be missed. Physics is `KXNOBELPHYSICS`, not `KXNOBELPHYS`.
3. The settled panel is a cap, not a history of the exchange. Twenty-five markets per series, two series (`KXHIGHNY`, `KXFEDDECISION`). Weather markets are short-lived. Fed markets use `fee_type=quadratic_with_maker_fees`; the engine charges the taker formula only and says so.
4. Candles are hourly when a market's open-to-settlement span is 10 days or less, otherwise daily. One-minute candles are not stored. Intra-hour path is not available to strategies, on purpose.
5. Public trades (`GET /markets/trades`) are not yet archived. The decision clock is the candlestick close. A trade-level backtest would need that endpoint, with the same no-lookahead rule.
6. The fetch-time order book is stored for up to 15 open Nobel markets and is not used for decisions. There is no historical order-book replay. Quote closes are the book history the API actually returned.
7. `close_time` and `expected_expiration_time` on a settled payload may have been revised. Primary strategies do not use them. A "late entry" strategy would need point-in-time metadata this API snapshot does not provide.
8. Rate limits and partial pagination are recorded in `failures.json`. A stopped page is a hole, not a zero.

## Simulation

9. Fills assume the closing quote was tradeable for the simulated size. The candle does not prove the size was resting at that close. Large simulated size against a thin close is an assumption. The size cap exists to keep that assumption smaller, not to remove it.
10. The 0.07 fee coefficient is inferred from the fee-schedule range, not returned as a number by the market endpoint. Fee-off runs are required reading before anyone treats a rank as robust.
11. Mark-to-market uses the closing bid. A wide book makes a new long look like a loss immediately. That is the liquidation mark, not a Kalshi account balance.
12. No market impact, no queue position, no self-trade between participants. Head-to-head means "same prices, same cash," not "they took each other's liquidity."
13. Forward Nobel markets cannot have a realized win rate until the October 2026 announcements settle. Ranking them before settlement is a mark, and the site says so.
14. Strategy thresholds were chosen as round cent bands before looking at a leaderboard. They were not optimized. The next session can add a threshold sweep without changing stored candles.

## Nobel archive

15. Nomination detail pages (`show.php`) are linked, not copied. The motivation on a nomination is not in this repo.
16. The 50-year seal still covers 1976 onward, as of the September 2026 archive tables. Medicine's public table stops at 1953. Economic sciences nominations are not in the public archive. Do not fill these.
17. Official nomination totals disagree with each other (homepage table versus search page, and some medicine pages versus their own counts). Both numbers are kept in the source catalog. Do not average them.
18. This environment could not re-download the nomination HTML. The rows are the 2026-09-24 copy from `buffedlizard55-lab/NOBEL-PRIZE`, with a physics-2025 API spot check. A full re-fetch belongs in the next session, on a network that can reach nobelprize.org.
19. 2026 prizes were not awarded as of 24 September 2026. Add them only after the announcements, from the API, not from Kalshi prices.

## Site and delivery

20. GitHub Pages serves the repository root from `main`. It updates after merge, not from this branch. The preview in the build sandbox is the local static server.
21. The Kalshi website link on a market page is a path built from the series ticker. The API URL is the one to trust if they disagree.
22. The desk loads the full trade ledger in the browser. If a later snapshot grows past a few hundred thousand rows, split the ledger by competition before the page gets slow.

## Suggested next session, in order

1. Confirm the Actions snapshot committed, and read `failures.json` before trusting a zero.
2. Re-fetch the Nobel API and one nomination year page from a network that can reach nobelprize.org. Diff against `catalog.json`.
3. Add `GET /markets/trades` for the settled panel, still barred from use before the trade timestamp.
4. After 6–13 October 2026, ingest the new prize records and let the forward competition settle from Kalshi `result` only. Do not type the winners in by hand from a headline.
5. Decide whether the fee coefficient should be replaced by a downloaded fee-schedule PDF quote, if Kalshi publishes the formula in that PDF.
