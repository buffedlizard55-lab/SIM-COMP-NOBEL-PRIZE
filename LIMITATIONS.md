# Limitations for the next session

## 2026-09-24 (third session): 2,000 strategies, information channels, verdicts

**What changed.** The program doubled to 2,000 variants in 20 batches of 100, so there are 2,011 simulated participants including the primary 11.

- Batches 011–020 add families that read declared information channels:
  - sibling contracts in the same Kalshi event, at or before T;
  - official results of markets settled strictly before T;
  - Kalshi's `strike_date`.
- Every family has a research card with sources verified on 2026-09-24.
- 21 families have a matched placebo, and every (family, settled universe) pair gets a predeclared verdict (`simcomp/analysis.py`). The results are shown in the site's Research view and in the P(Win) card on the leaderboard.
- The build replays four batches instead of one.
- A **Tests** workflow runs on pull requests.
- The collect workflow now also commits `docs/RESEARCH.md`.

**New or sharpened limits.** Read these before quoting any verdict.

1. **Five SUPPORTED-ON-SNAPSHOT results out of 173 tests, against about 8.7 expected false passes at 5%.** The supported count is consistent with luck.
   - None of the five is supported in both settled universes.
   - Three of the four Nobel ones get 42–47% of their P&L from KXNOBELPEACE-25.
   - Three of the five share the logit / favorite-longshot entry (`kelly_fraction` and `edge_scaled_size` size off the logit edge, and `logit_momentum_agree`).

   Correlated families are not independent tests. The binomial p-value in research.json assumes independent variants and overstates the evidence; it is shown for transparency, not as a significance test.
2. **Only 5 settled Nobel events, and 3 of them have a YES.**
   - Any Nobel verdict rests on a handful of outcomes.
   - The panel (35 events, 11 with a YES) is Fed and weather markets, not Nobel markets.
   - A result that holds on the panel says nothing direct about Nobel markets.
3. **Chemistry, medicine and physics have no settled history in the snapshot.**
   - Their 2025 contracts were not returned by the public endpoints.
   - They trade only in the forward universe, and no settled result speaks to them.
   - The flag `nobel_subjects_without_settled_history` is computed from the data each build, not hardcoded.
4. **Nobel events report `mutually_exclusive: false` and have no `strike_date`** (spot-checked against the Get Event endpoint on 2026-09-24).
   - `event_underround_yes` is NOT TESTED on Nobel.
   - Schedule and horizon families are tested on the panel only.
   - Event families that read sibling prices run behind a probability-mass gate, because stored sibling sets can be incomplete: Kalshi omits nested markets of older historical events.
5. **Verdict medians use only the variants that traded.**
   - `median_eq_all_variants` is also stored.
   - A family that mostly stays in cash can have a strong traded median from a few variants. `entered` / `n` is shown next to every result.
   - Families with fewer than 3 traded variants are LOW-POWER by rule. This demoted `logit_skip_conflict` (2 traded variants, above the Nobel null p95).
6. **Cash is not recycled.** Settlement cash is applied after the decision loop, so a participant cannot redeploy a win inside the same universe. This understates compounding strategies and makes the per-event leave-one-out an exact subtraction. Changing it would change every ledger hash.
7. **Panel selection uses lifetime volume.** The panel is the top 25 settled markets by final volume among the first 2,000 historical rows per series. Final volume is known only after the fact. That is a selection bias in which markets exist in the panel; it is not a lookahead inside any decision. It is listed as a data-quality flag.
8. **`close_time` is excluded everywhere.** On settled Nobel markets it is revised to the post-announcement halt, which would leak the outcome date. Families that need a Nobel announcement date therefore cannot be built from Kalshi fields, and no date was typed in by hand.
9. **The P(Win) card is for settled universes only.** In the forward universe the top-decile cut is exactly $10,000, because unsettled positions are marked at the bid and almost nobody is above starting cash, so `p_top_decile` there means nothing.
10. **Runtime.** A full rebuild from the stored snapshot takes about 5 minutes in the development sandbox (912,971 ledger rows, program bundle about 20 MB), up from about 2 minutes. The Actions timeout (60 minutes) is still ample.
11. **No browser render in this session.** The sandbox has no headless browser. `app.js` was syntax-checked (`node --check`), and the JSON it loads was checked, but the Research view and P(Win) card have not been looked at in a browser before merge. Check the live Pages site after merge.

**Verified this session.**

- 39 unit tests pass.
- `scripts/audit_program.py` is clean on 912,971 rows.
- `verify_program.py batch-013` and `batch-018` reproduce 300 ledgers each.
- The four-batch build replay matched.
- The 11 primary strategies have real-data parity in both engines.
- Three Kalshi events were spot-checked field by field (URLs in docs/PROGRAM.md).

### Suggested next session, in order (supersedes the lists below)

1. After 6–13 October 2026, when the 2026 Nobel markets settle on Kalshi, re-run with no code change. This is the out-of-sample test the program was built for.
   - The five SUPPORTED-ON-SNAPSHOT families and their placebos are the predeclared hypotheses to check.
   - Take settlements from Kalshi `result` only, and ingest prizes from the Nobel API, not from headlines.
2. Look at the live site's Research view and P(Win) card in a browser, on desktop and mobile.
3. Recover 2025 physics, chemistry and medicine contracts, if any public endpoint returns them (for example event-by-ticker on `KXNOBELPHYSICS-25`). Record a failure rather than filling a gap.
4. Add cash recycling as a separate, versioned engine option with its own competitions. Do not change the default ledger.
5. Add a family-level correction for correlated tests, for example a block bootstrap over events, and report it next to the current rules.
6. Add a trade-tape archive (`GET /markets/trades`) so the decision clock can move from candle closes to trades.
7. Widen the panel to more event-structured series with `mutually_exclusive: true`, to give the event families more than one testing ground. Select by a pre-registered rule that does not use final volume.

## 2026-09-24 (second session): the 1000-strategy program

What changed this session: the simulated layer grew from 11 primary strategies to 1,011 participants. The research program (`simcomp/research_program.py`, `simcomp/program.py`) runs 1,000 parameterized strategies in 10 batches of 100 over the same three universes, with the same decision clock, size rules, and fee reading. Both engines share `compute_fill`; parity between them is tested; batch-001 is replayed after every full pass and the build aborts on mismatch. New limits this session:

1. The program runs 1,000 participants per universe in one pass and streams ledgers to 30 gzipped CSVs. Runtime in the sandbox was about 115 seconds for 796,804 ledger rows, plus the primary competitions (which run twice for the replay proof). The GitHub Actions workflow timeout was raised to 60 minutes because collection plus the older double-run plus the program now shares one job. If collection gets slower, split collect and simulate into two jobs.
2. Program ledgers are compact: note codes instead of full reason strings, and no candle fields copied onto each row. The full numeric justification for a row is reproducible from `data/sim/candles/{ticker}.json` plus the variant's parameters; `data/sim/program/SCHEMA.md` is the recipe. The primary 11-participant ledger keeps the rich per-field format. If a reviewer wants program rows in the rich format, the only honest way is a re-run per batch (`scripts/verify_program.py`); storing both formats for ~800k rows would roughly double repository size.
3. The strategy view is a 24-candle window. Every registered lookback fits inside it and the registry refuses a variant that needs more; a future family with a longer lookback must raise `PROGRAM_PRIOR_WINDOW` deliberately, not silently.
4. The null band is 100 random-entry variants. It is a floor, not a significance test at 100 trials; the share-above-p95 statistic is descriptive.
5. Program equity curves are not stored — only final equity, drawdown, and per-market rollups. Investigating "when did this variant go wrong" uses the ledger rows, not a curve.
6. The site board loads `leaderboard.json` (~1.1 MB) and participant drill-down decompresses a whole batch ledger in the browser. That was acceptable here; if batches grow, move to per-participant files.
7. The audit in `scripts/audit_program.py` recomputes cash, P&L, fill prices against stored candles, ledger-row field counts, forward-universe settlement absence, and manifest hashes (run 2026-09-24: 796,804 rows, 0 clock/cash/P&L violations, 4,000 price samples matched, manifest clean). It does not re-derive the strategy intents — that is what the replay proof and parity tests are for.
8. 2025 physics, chemistry, and medicine 2025 Kalshi contracts are still absent from the stored snapshot for the historical endpoint reasons documented below; the forward universe covers the 2026 events. No 2026 Nobel settlement exists yet (announcements start 6 October 2026), so every 2026-universe rank is a liquidation mark.

Second review session, what it caught and fixed (kept here because they are easy to re-break):

1. Site + ledger CSV: the site ledger parser split naively on commas. Two latent bugs — notes could carry a comma and Python's csv module writes CRLF (a bare `\r` would have glued itself to the last column). The build now guarantees comma-free, `\r`-free note codes, and the site parser is a small quoted/CRLF-safe CSV reader. Keeping rows comma-free at the writer instead of only hardening the reader is done on purpose: `awk` and `split(",")` keep working for a reviewer.
2. Engine parity probe: running the program engine with full-history views exposed a genuine divergence for exactly one primary strategy — `volume_momentum` reads the unbounded prior list. Registered program families are all window-bounded (deepest lookback 15 of 24), so program results are unaffected, and a test now refuses any registry entry that breaks the window. Full-history runs stay byte-identical to the primary engine.
3. `markets.json` existed with no consumer: program market-by-market rollups are now on every market page, under the primary results, with the null cohort median for reference. Program activity per day and program data flags are on the Activity and Flags views.
4. The audit now also rejects ledger rows with the wrong field count and any settlement row in the forward universe.

### Suggested next session, in order (updated)

1. After the Actions run on `main`, diff the fresh snapshot: confirm `failures.json`, re-read the null band and the family medians before trusting any rank, and rerun `scripts/audit_program.py`.
2. After 6–13 October 2026, ingest the new prize records from the official API (not from Kalshi prices), then let the forward competitions settle from the Kalshi `result` field only. Do not type winners in by hand from headlines.
3. Re-fetch the Nobel API and one nomination year page from a network that can reach nobelprize.org; diff against `catalog.json`.
4. Add `GET /markets/trades` archiving so the decision clock can move from candle closes to the trade tape, with the same no-lookahead rule.
5. Add a daily-sampled equity curve per program participant if the site needs time-series views beyond the primary 11.
6. Consider splitting the Actions job (collect → simulate) and caching `data/sim/candles` between runs.

## 2026-09-24 (first session): after the first working desk

These are the gaps that still block a stronger project. They are not hidden in the leaderboard.

## Collection

1. This sandbox cannot open TLS to `api.nobelprize.org`, `www.nobelprize.org`, or the Kalshi API hosts (`SSL_ERROR_SYSCALL`). Collection runs in GitHub Actions, where the public API is reachable. If that workflow did not commit a snapshot, the leaderboard files will be missing until someone runs `python scripts/refresh.py` on a network that can reach Kalshi.
2. The Nobel market universe is complete only for series the collector actually received. A series whose title does not contain "NOBEL" and that is not in the known list will be missed. Physics is `KXNOBELPHYSICS`, not `KXNOBELPHYS`.
3. The settled panel is a cap, not a history of the exchange. Twenty-five markets per series, two series (`KXHIGHNY`, `KXFEDDECISION`). Weather markets are short-lived. Fed markets use `fee_type=quadratic_with_maker_fees`; the engine charges the taker formula only and says so.
4. Candles are hourly when the open-to-settlement span is 10 days or less, when the market opened within two days of the fetch, or when a daily request returns an empty list. One-minute candles are not stored. Intra-hour path is not available to strategies, on purpose. An empty candle list is not a price.
5. Public trades (`GET /markets/trades`) are not yet archived. The decision clock is the candlestick close. A trade-level backtest would need that endpoint, with the same no-lookahead rule.
6. The fetch-time order book is stored for up to 15 open Nobel markets and is not used for decisions. There is no historical order-book replay. Quote closes are the book history the API actually returned.
7. `close_time` and `expected_expiration_time` on a settled payload may have been revised. Primary strategies do not use them. A "late entry" strategy would need point-in-time metadata this API snapshot does not provide.
8. Rate limits and partial pagination are recorded in `failures.json`. A stopped page is a hole, not a zero. The first snapshot (2026-09-24T17:29:32Z) had 575 HTTP 400s because `mve_filter` was sent with `series_ticker` or `event_ticker` on `/historical/markets`. Those filters are mutually exclusive. That bug is why `nobel_settled` was 0. The collector no longer sends `mve_filter` on historical calls. Do not treat that empty settled book as a finding about Kalshi.

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
22. The leaderboard does not download the full trade ledger. Each competition's ledger is `data/sim/trades_by_competition/{id}.json`. `trades.json` remains the full audit file.

## What the 2026-09-24 17:47 UTC snapshot actually contains

Checked against the stored files and, for the holes, against the public Kalshi endpoints on the same day.

- Settled Nobel events stored: `KXNOBELECON-25`, `KXNOBELLIT-25`, `KXNOBELPEACE-25`, `KXTRUMPNOBEL-25OCT15`, `NOBELLIT-23`. Official yes contracts in that set: László Krasznahorkai, María Corina Machado, Jon Fosse. Those names match the Nobel catalog for literature 2025, peace 2025, and literature 2023.
- `GET /historical/markets?series_ticker=KXNOBELPHYSICS`, `KXNOBELCHEM`, and `KXNOBELMED` returned empty lists. Live `/events` for those series returned only the 2026 events. No 2025 physics, chemistry, or medicine contracts were stored because the public endpoints used here did not return them. That is not a finding that those prizes were not awarded.
- `KXNOBELECON-25` has 20 stored contracts, every one `result=no`. The catalog laureates Joel Mokyr, Philippe Aghion, and Peter Howitt are not among the stored contract names. The event endpoint's market list, read on 2026-09-24, also did not include them. No yes market was added.
- `KXTRUMPNOBEL-25OCT15` settled `no`. It is a name match, not the Peace Prize winner market.
- `KXNOBELPEACE-25` (the event-level contract, volume 0) had an empty daily candle response. An hourly retry asked for about 7096 candles and Kalshi rejected it at the 5000 cap. The child contracts in that event do have candles. The parent is not a traded price that was dropped.
- The 17:59 UTC collect named the caps: `KXHIGHNY` events stopped at 500, and `KXHIGHNY` historical markets stopped at 2000. The panel is the top 25 among those rows, not a global volume rank. The unfiltered series catalog still stops at 5000. Known Nobel series are requested by ticker after that page stops.
- The oversized hourly candle request for `KXNOBELPEACE-25` is no longer sent. That parent contract has volume 0. Its child contracts still have candles.
- The series catalog page stopped at 5000 rows, and one events page stopped at 500. Known Nobel series were still requested by ticker.

## Suggested next session, in order

1. Confirm the Actions snapshot committed, and read `failures.json` before trusting a zero.
2. Re-fetch the Nobel API and one nomination year page from a network that can reach nobelprize.org. Diff against `catalog.json`.
3. Add `GET /markets/trades` for the settled panel, still barred from use before the trade timestamp.
4. After 6–13 October 2026, ingest the new prize records and let the forward competition settle from Kalshi `result` only. Do not type the winners in by hand from a headline.
5. Decide whether the fee coefficient should be replaced by a downloaded fee-schedule PDF quote, if Kalshi publishes the formula in that PDF.
