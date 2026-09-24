# The 2,000-strategy research program

This is the working plan for the simulated competition layer. It also records that the plan was carried out one strategy at a time, in 20 batches of 100. The registry the code reads is `data/sim/program/strategies.json`. The research cards are in `simcomp/research_cards.py`, the build is `simcomp/program.py` and the verdict rules are in `simcomp/analysis.py`. Every check below is run by `python -m unittest discover -s tests -v`, `scripts/audit_program.py` and `scripts/verify_program.py`.

Everything in the program is simulated. No participant is a Kalshi user, no order was sent, and no fill is real. Market prices and official results are Kalshi data and link to the API URL they came from.

**Focal point.** Two questions come first on the site:

- **Maximize P(Win):** which predeclared family most often finishes in the top decile of a settled universe? The leaderboard card answers this.
- **Own the Outcome:** can every simulated number be recomputed from stored Kalshi data, and does every verdict name the conditions that would overturn it? The audit, replay, research cards and the "flip condition" on each card answer this.

## Design rules (fixed before any run)

1. **One simulation economy.** The program engine uses the same `compute_fill` as the 11 primary competitions, and parity tests compare full ledgers between the two engines. Starting conditions are the same for every participant:
   - $10,000 paper cash;
   - $100 entry target, 5% cash fraction and a $300 per-market cost cap;
   - a 500-contract clip;
   - the quadratic taker-fee reading (0.07 coefficient; see METHOD.md);
   - fills at the closing quote.
2. **No lookahead.** A decision at candle end T sees only what METHOD.md → *Information channels* allows. Two rules matter most:
   - Each family declares its channels on its card, and a test checks that the view never carries a later candle, a result or `close_time`.
   - A strategy sees at most 24 prior candles of its own market (`PROGRAM_PRIOR_WINDOW`), and the registry refuses a variant whose declared lookback needs more.
3. **Predeclared parameters and cards.** Every family has a research card with these fields:
   - `question`: the hypothesis;
   - `mechanism`: why it could work;
   - `channels`: what it reads;
   - `predicts`: the expected sign;
   - `falsified_if`: the flip condition, i.e. the observation that would make the verdict wrong;
   - `sources`: at least one source verified on 2026-09-24 (`simcomp/research_sources.py`), or an explicit `none-technical-rule` / `none-design-control` tag;
   - `kind`: signal, exit, sizing, ablation, placebo, control or null.

   The yardsticks it is judged against are the batch-001 null and, where one exists, its matched placebo (`placebo_family` in research.json).

   Grids and cards were written in `simcomp/research_program.py`, `simcomp/research_phase2.py` and `simcomp/research_cards.py` before results were read. No variant was added, tuned or deleted after looking at a leaderboard.
4. **Nothing counts as skill unless it clears three yardsticks:**
   - the batch-001 random-entry null (100 seeds);
   - a matched placebo, where one exists. The placebo runs the family's own trigger (same markets, same timestamps, same contract count) but picks the side of each buy with a seeded coin, in the same batch. Beating it shows that choosing the side carried information, not just the timing and market selection;
   - a leave-one-event-out check.
5. **Batches are completed one at a time.** Each batch lists its registry size, and each has been replayed or re-verified. All 20 are complete as of the 2026-09-24 21:48 UTC build.

## Batch plan and completion status

Family counts include placebo and control families. Every batch has 100 variants.

| Batch | Topic | Families | What it tests |
| --- | --- | --- | --- |
| batch-001 | Null models | 1 | Random valid entries at three activity rates. This is the null distribution. |
| batch-002 | Favorite band | 1 | Buy-and-hold favorites; favorite-longshot bias. |
| batch-003 | Longshot band | 1 | Buy-and-hold longshots. |
| batch-004 | Momentum | 1 | Following close-to-close moves. |
| batch-005 | Contrarian fade | 1 | The batch-004 signal, faded. |
| batch-006 | Mean reversion | 1 | Entry below a prior mean, exit back at it. |
| batch-007 | Exits and stops | 4 | Exit rules read separately from entry rules. |
| batch-008 | Volume and gates | 3 | Conditioning on activity, calm and relative liquidity. |
| batch-009 | Breakouts and entry timing | 3 | New-high entries; ordinal timing of the same band rule. |
| batch-010 | Spread tolerance | 4 | How much spread each entry style can sit through. |
| batch-011 | Event structure | 11 | Sibling contracts in the same Kalshi event. Includes normalized share, overround NO, underround YES, leader, rank-k, field NO, concentration, leader change and rotation. |
| batch-012 | Literature calibration priors | 8 | Favorite-longshot bias as a logit rescale, Prelec inverse weighting, fee-aware logit, longshot NO writer and high-favorite YES. |
| batch-013 | Walk-forward learning | 8 | Calibration learned only from markets settled strictly before T. Covers bucket, base rate, logit slope, recency and age. |
| batch-014 | Time, age and schedule | 9 | Market age, Kalshi `strike_date` horizon, UTC hour, weekday and pre-strike exit. |
| batch-015 | Liquidity, volume, open interest | 14 | Open-interest growth and decline, volume spikes, dormant wake-up, liquidity gates, spread compression and stale quotes. |
| batch-016 | Trend and reversal constructions | 15 | Moving-average crossover, time-series momentum, big moves, RSI, Bollinger bands, runs, ranges, dips and rallies. |
| batch-017 | Position sizing | 11 | Kelly fraction, fixed contracts, edge-scaled size, cash fraction, payout target, reserve gate, ladders and split entry. |
| batch-018 | Exits and holding period | 13 | Time, clock, trailing, breakeven, target, edge-gone, stop-and-reverse, volatility, partial, ladder and max-loss exits. Includes a hold control and a random-exit control. |
| batch-019 | Information and timing ablations | 12 | Lagged signal, delayed entry, price source, decision frequency, noisy price, coarse grid, first quote and window truncation. |
| batch-020 | Ensembles and a second null | 16 | Votes, regime switch, logit and momentum agreement or conflict, leader with open interest, consensus favorite, mixtures and a rate-matched null. |

The registry holds:

- 2,000 variants, 2,000 simulated participants, 20 topics and 137 families;
- by family kind: 74 signal, 16 exit, 9 sizing, 9 ablation, 21 placebo, 6 control and 2 null.

Ids follow the pattern `family-slug-bNNN-III`, and usernames follow `sim-bNNN-III`. Tests confirm that every variant has a non-empty hypothesis, a unique id and username, JSON-serializable parameters and a complete card with verified sources.

## Verdicts (`simcomp/analysis.py`, printed on the site under Research)

Each (family, settled universe) pair gets exactly one verdict. Medians use only the variants that traded, so a family whose variants all sit in cash cannot look safe.

| Verdict | Rule |
| --- | --- |
| REFERENCE | Null, control or placebo family; it is a yardstick. |
| NOT TESTED | No variant filled an order. |
| INCONCLUSIVE-LOW-POWER | Any of: fewer than 3 variants traded; fills touched fewer than 3 settled events; no touched event had a YES outcome. |
| SUPPORTED-ON-SNAPSHOT | All of: traded median > null p95 and > $10,000; traded median > the matched placebo's traded median (if a placebo exists); worst leave-one-event-out median > null median. |
| NOT SUPPORTED | Traded median ≤ null median. |
| INCONCLUSIVE | Anything in between. |
| UNSETTLED | Forward universe. Positions are marked at the closing bid and no outcome exists yet. |

## Results on the 2026-09-24 snapshot

**Null band (batch-001, n = 100):**

| Universe | Settled events (with a YES) | Markets with candles | p05 | Median | p95 | Top-decile cut |
| --- | --- | --- | --- | --- | --- | --- |
| nobel_settled | 5 (3) | 66 | $8,649.31 | $9,455.51 | $10,098.72 | $10,026.65 |
| panel_settled | 35 (11) | 50 | $9,056.27 | $9,767.24 | $10,553.86 | $10,127.09 |
| nobel_forward | 0 of 6 | 147 | $8,319.23 | $8,673.31 | $9,220.44 | (marks only) |

**Verdict counts:**

- nobel_settled: 4 SUPPORTED-ON-SNAPSHOT, 41 INCONCLUSIVE, 31 LOW-POWER, 26 NOT SUPPORTED, 6 NOT TESTED, 29 REFERENCE.
- panel_settled: 1 SUPPORTED-ON-SNAPSHOT, 53 INCONCLUSIVE, 6 LOW-POWER, 48 NOT SUPPORTED, 29 REFERENCE.
- Over the 173 tests that reached a verdict, about **8.7 would clear a 5% bar by chance alone**. Five cleared it, so the count of supported families is itself consistent with luck.

**What cleared the bar.** Each family cleared it in one universe only. None is SUPPORTED in both settled universes.

| Family | Universe | Traded variants | Traded median | Top event (share of P&L) | Worst LOO median |
| --- | --- | --- | --- | --- | --- |
| learned_age_calibration | panel | 6 | $10,718.26 | KXFEDDECISION-26SEP (14%) | $10,590.01 |
| fade_the_rally | nobel | 6 | $10,195.62 | KXTRUMPNOBEL-25OCT15 (44%) | $10,075.06 |
| kelly_fraction | nobel | 16 | $10,188.91 | KXNOBELPEACE-25 (47%) | $10,062.23 |
| edge_scaled_size | nobel | 8 | $10,108.97 | KXNOBELPEACE-25 (46%) | $10,025.88 |
| logit_momentum_agree | nobel | 4 | $10,105.46 | KXNOBELPEACE-25 (42%) | $10,006.78 |

How to read this table:

- Three of the four Nobel results lean on the same event, KXNOBELPEACE-25.
- Three of the five sit on the logit / favorite-longshot machinery: Kelly sizing and edge-scaled sizing both size by the logit edge.
- These are correlated tests, not five independent discoveries.
- `logit_skip_conflict` also beat the Nobel null p95. It had only 2 traded variants, so it is LOW-POWER by the minimum-variants rule.

**What clearly did not work.** Batch-004 momentum and batch-005 contrarian are both NOT SUPPORTED in both settled universes:

| Family | panel median | nobel median |
| --- | --- | --- |
| momentum | $3,866.58 | $5,294.22 |
| contrarian | $3,988.07 | $4,760.47 |

- A signal and its mirror both lost heavily. That points to trading cost and wide closing spreads, not to direction.
- `volume_momentum_window` and batch-006 mean reversion are also NOT SUPPORTED in panel.

**Direction across universes** (signal, exit, sizing and ablation families):

- 46 families are above the null median in both settled universes;
- 18 are below it in both;
- 38 point in different directions in the two;
- 6 traded in only one.

## How a claim in this program may be made

Allowed: "On the 2026-09-24 snapshot, family X's traded median ending equity was A, against a null band of [B, C]. Its worst leave-one-event-out median was D, and it depends on event E for k% of P&L."

Not allowed:

- "Strategy X wins", "X would make money" or "X predicts the prize";
- "X is SUPPORTED" without the words "on snapshot" and the multiple-testing note.

The limits behind this: one snapshot, 5 settled Nobel events, a capped panel, an interpretation of the fee schedule, closing-quote fills and no market-impact model.

## Verification (2026-09-24 21:48 UTC build)

- **Build replay.** After the full pass, four batches are re-run across all three universes, and every per-participant ledger hash must match or the build aborts: batch-001 (null), batch-011 (event channel), batch-013 (settled-pool channel) and batch-018 (exits). Result: `manifest.json → replay → status: matched`.
- **Independent re-run.** `python scripts/verify_program.py batch-013` and `... batch-018` each reproduce 300 participant ledgers (100 variants × 3 universes) against the stored hashes. The verifier loads the same event and settled-pool channels as the build.
- **Post-hoc audit.** `python scripts/audit_program.py` checked 912,971 ledger rows. It found:
  - 0 decision-clock violations, 0 cash-chain violations and 0 realized-P&L violations;
  - 4,000 sampled fills matching the stored candle fields exactly;
  - 64,360 open-position rows;
  - 6,000 board rows;
  - 0 manifest mismatches.
- **Engine parity.** The 11 primary strategies produce identical ledgers and boards in both engines on all three real universes (`real parity ... 11 ledgers and 11 boards match`).
- **Channel lookahead tests** (`tests/test_phase2.py`):
  - The event view contains only candles at or before T, whatever order markets are visited in.
  - The settled pool contains only markets settled strictly before T.
  - The schedule parser refuses `close_time`-style stamps.
  - The decision view never carries `result` or `close_time`.
- **Placebo tests.** A placebo trades the same markets at the same times as its family, and re-used strategy instances reproduce ledgers after `reset()`.
- **Verdict boundary tests.** Every rule above is exercised on hand-built statistics, and removing the minimum-variants rule makes the test fail.
- **Deterministic output.** Gzip files are written with `mtime=0`, so two runs on the same snapshot produce byte-identical files and manifest hashes.

## Kalshi field spot-check (2026-09-24)

Three stored events were re-read from the public API and compared field by field:

- [KXFEDDECISION-26SEP](https://external-api.kalshi.com/trade-api/v2/events/KXFEDDECISION-26SEP)
  - `strike_date` 2026-09-16T18:00:00Z and `mutually_exclusive` true.
  - The H25 contract has result `yes` and settlement_ts 2026-09-16T18:08:08Z.
  - Matches the stored data.
- [KXHIGHNY-26JAN05](https://external-api.kalshi.com/trade-api/v2/events/KXHIGHNY-26JAN05)
  - `strike_date` 2026-01-06T04:59:00Z and `mutually_exclusive` true.
  - `markets` is empty, because nested markets of historical events are omitted, as the [historical-data docs](https://docs.kalshi.com/getting_started/historical_data) say.
  - Matches the stored data.
- [KXNOBELPEACE-25](https://external-api.kalshi.com/trade-api/v2/events/KXNOBELPEACE-25)
  - No `strike_date`, and `mutually_exclusive` false.
  - Matches the stored data.
  - Stored KXNOBELPEACE-25-MARI has result `yes` and settlement 2025-10-10T12:24:01Z.

Two consequences:

- **Nobel events are not flagged mutually exclusive and have no strike date.** Sum-over-event families (`event_underround_yes`) and schedule families (batch-014 horizon rules) therefore cannot fire on Nobel. They show NOT TESTED or low power there, and their only test is the panel.
- **`close_time` on settled Nobel markets is an after-the-fact early close** (seen on KXNOBELLIT-25 and KXNOBELECON-25). No channel exposes it.

## What the program does not do yet

- No per-participant equity curve in the program bundle. Final equity, drawdown and per-event P&L are stored.
- Cash is not recycled: settlement cash arrives after the decision loop, so a participant cannot redeploy winnings within a universe.
- No public-trades archive. The decision clock is the candle close, not the trade tape.
- Three universes. The panel is two series capped at 25 markets each, selected by lifetime volume (see LIMITATIONS).
- No cross-universe portfolio. Each row is a separate paper account.
