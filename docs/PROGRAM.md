# The 1000-strategy research program

This is the working plan for the simulated competition layer, and the record that it was carried out one strategy at a time, in batches. The machine-readable registry is `data/sim/program/strategies.json`; the build is `simcomp/program.py`; every check below is run by `python -m unittest discover -s tests -v` and by `scripts/audit_program.py`.

## Design rules (fixed before any run)

1. One simulation economy. The program engine shares `compute_fill` in `simcomp/engine.py` with the primary 11-participant competitions. A parity test reruns the primary strategies through both engines and compares the full ledger hash, participant equity, realized/unrealized P&L, fees, wins, losses, round trips, win rate, and drawdown. They are identical.
2. Same starting conditions: $10,000 paper cash, $100 entry target, $300 per-market cost cap, 5% cash fraction, 500-contract clip, quadratic taker-fee reading, closing-quote fills.
3. No lookahead. The decision clock of METHOD.md applies unchanged. A strategy sees at most the 24 prior candles of its market; the registry refuses a variant whose declared lookback needs more.
4. Predeclared parameters. Grids were written down in `simcomp/research_program.py` before results were computed. No variant was added, tuned, or deleted after looking at a leaderboard.
5. Nothing is read as skill unless it clears the null. Batch-001 is random valid entries; its distribution per universe is printed next to every family result.
6. Batches are completed one at a time. Each batch below lists its registry size and its own verification. All ten are complete as of the 2026-09-24 19:04 UTC build.

## Batch plan and completion status

| Batch | Topic | Variants | What it tests | Status |
| --- | --- | --- | --- | --- |
| batch-001 | Null models | 100 seeds (fire 30/1000 for 001–050, 10/1000 for 051–075, 60/1000 for 076–100) | The null distribution itself; activity-rate sensitivity of a random entry | Complete; replay-matched |
| batch-002 | Favorite band | 100 = 5 min-ask × 4 max-ask × 5 spread caps | Buy-and-hold favorites; favorite-longshot bias, band-width and spread sensitivity | Complete |
| batch-003 | Longshot band | 100 = 5 × 5 × 4 | Buy-and-hold longshots | Complete |
| batch-004 | Momentum | 100 = 5 thresholds × 4 spread caps × 5 prior-candle minima | Does following close-to-close moves beat the null at any grid point? | Complete |
| batch-005 | Contrarian fade | 100, same grid as batch-004 | The identical signal, faded; separates signal from side choice | Complete |
| batch-006 | Mean reversion | 100 = 5 lookbacks × 5 deviations × 4 spread caps | Entry below a prior mean, exit back at it | Complete |
| batch-007 | Exits and stops | 100 = 20 take×stop + 25 stop-only + 25 take-only + 30 re-entry | Exit rules read separately from entry rules | Complete |
| batch-008 | Volume and gates | 100 = 48 volume-window + 27 volatility gates + 25 relative-spread | Conditioning entries on activity, calm, and relative liquidity | Complete |
| batch-009 | Breakouts and entry timing | 100 = 36 breakouts + 50 timed favorites + 14 timed slices | New-high entries; the ordinal timing of the same band rule | Complete |
| batch-010 | Spread tolerance | 100 = 48 ranged tight-value + 24 wide favorites + 12 wide longshots + 16 slices | How much spread each entry style may sit through | Complete |

Totals: 1,000 variants, 1,000 simulated participants, 10 topics. Every variant has a non-empty hypothesis, unique strategy id and username, and JSON-serializable parameters (test `RegistryTests.test_at_least_one_thousand_strategies_one_by_one`).

## How a claim in this program is allowed to be made

Allowed: "On the 2026-09-24 snapshot, family X's median ending equity was A vs the null band's [p05, p95] of [B, C]; k% of its 100 variants ended above p95."

Not allowed: "Strategy X wins," "X would make money," "X predicts the prize." One snapshot, capped panel, quadratic-fee interpretation, closing-quote fills with no market-impact model.

## Verification so far

- Parity: the program engine reproduces the primary engine's ledger identically on a constructed market set (test `ParityTests`).
- Real-data ledger of the primary path is byte-identical before and after the 2026-09-24 engine refactor (ledger SHA `13490d89…` on both).
- Build replay: after each full program run, batch-001 is rerun across all three universes and all 300 per-participant ledger hashes must match; the build aborts otherwise (`manifest.json → replay`).
- Post-hoc audit (`python scripts/audit_program.py`, run 2026-09-24, re-run after the session-two review fixes): 796,804 ledger rows replayed from the CSVs — 0 decision-clock violations, 0 cash-chain breaks, 0 realized-P&L mismatches; 4,000 sampled fills matched the stored candle fields exactly (price, fee and cash-chain columns recomputed from raw candles); no settlement row exists in the forward universe; every row has exactly the 12 schema fields; the manifest sha-256 of every program file matched.
- Engine parity re-proved on the real snapshot, not only on synthetic candles: the 11 primary strategies produce byte-identical ledger hashes and boards in both engines on all three universes when the program engine exposes the full prior window (test `test_real_universe_ledgers_match_between_engines`). Divergence with the default 24-candle window was found for exactly one primary strategy — `volume_momentum`, whose median is over the whole unbounded prior list — and the registry now refuses any family whose declared lookback exceeds the window (`test_program_registry_lookbacks_all_bounded`; all 1,000 variants ≤ 15).
- Independent re-run of one batch (`python scripts/verify_program.py batch-001`): 300 participant ledgers reproduce the stored hashes.

## What the program does not do yet

- No per-participant equity curve in the program bundle (final equity and max drawdown are stored; per-fill curves exist for the primary 11 in `data/sim/equity.json`). A daily-sample curve is a candidate next step.
- No public-trades endpoint archive, so the decision clock is the candlestick close, not the trade tape.
- Three universes only. Expanding candle coverage is a collection problem, not an engine problem.
- No cross-universe portfolio. Each row is a separate paper account.
