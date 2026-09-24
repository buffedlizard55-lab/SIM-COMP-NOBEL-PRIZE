# Program data schema and verification recipe

Everything under `data/sim/program/` is produced by `simcomp/program.py` from the stored
Kalshi snapshot `data/kalshi/markets.jsonl`. Everything here is simulated except the
market fields, which are copied from Kalshi payloads and always carry a source URL in
`markets.json`.

## Files

| File | Contents |
| --- | --- |
| `manifest.json` | Program version, counts, per-universe ledger hashes, replay proof, decision-clock rule, sha-256+size of every program file |
| `strategies.json` | One row per variant: batch, topic, family, strategy_id, username, hypothesis, parameters, class |
| `participants.json` | One row per simulated participant (username, display name, strategy link, hypothesis) |
| `leaderboard.json` / `leaderboard.csv` | One row per participant per universe with rank and P&L fields |
| `families.json` | Per family per universe aggregate stats and the batch-001 null band per universe |
| `markets.json` | Per market per universe rollups: participants traded, family P&L medians, official result |
| `batches/batch-001.json` … `batch-010.json` | Batch report: topic statement, full 100-row leaderboard per universe, parameter sensitivity, null band |
| `notes.json` | Decision-note codes that occurred, per family, with counts |
| `activity.json` | Per universe, per UTC day: number of ledger rows across all 1,000 participants |
| `positions.csv.gz` | Every open simulated position at the final mark: universe, participant, ticker, side, qty, entry, cost, liquidation, unrealized P&L, mark source and time |
| `trades/{batch}/{universe}.csv.gz` | The full simulated ledger, one gzipped CSV per batch and universe |

## Leaderboard fields

`p` participant id · `b` batch · `f` family · `s` strategy id · `u` universe ·
`r` rank within the universe (ties share a rank) · `eq` ending equity = cash +
liquidation mark · `cash` simulated cash · `mtm` liquidation value of open
positions · `real` realized P&L · `unreal` unrealized P&L (eq − start − real) ·
`fees` simulated taker fees · `n` filled simulated orders (settlements not
counted) · `sett` settlement rows · `w`/`l` settled or closed round trips won /
lost · `trips` settled round trips · `wr` win rate over `trips` or null · `dd`
max drawdown · `roi` (eq − 10000) / 10000 · `mkts` markets traded · `open`
open positions at the final mark · `t0`/`t1` first / last ledger timestamp (unix).

Universes: `nobel_forward` (open Nobel markets; rank is a mark, not a result),
`nobel_settled`, `panel_settled` (historical backtests; see LIMITATIONS for scope).

## Ledger CSV columns

`participant_id, ts_unix, ticker, action, side, price, qty, fee, cash_after, realized_pnl, fill_src, note`

- `action`: `buy` | `sell` | `settlement`
- `fill_src`: `YA` yes_ask.close · `YB` yes_bid.close · `NA` NO ask derived from
  yes_bid.close · `NB` NO bid derived from yes_ask.close · `MR` official
  `market.result`, applied only at settlement_ts
- `note`: the strategy's decision note (see `notes.json`) or
  `settlement_result_yes` / `settlement_result_no`
- `price`, `fee`, `cash_after`, `realized_pnl` are dollar strings rounded to 4
  places, the same rounding as the primary ledger

## Verify a line, end to end

1. Pick a ledger row: `zcat data/sim/program/trades/batch-004/nobel_forward.csv.gz | head -50`.
2. Its price must equal the named candle field: open
   `data/sim/candles/{ticker}.json`, find the object with
   `end_period_ts == ts_unix`, and compare `yes_ask_close` (for a YES buy, `YA`),
   `yes_bid_close` (YB), `1 − yes_bid_close` (NA), `1 − yes_ask_close` (NB).
3. Confirm the decision used no later information: `ts_unix` is strictly less
   than the market's `settlement_ts` in `data/sim/market_index.json` (settled
   universes only), and settlement rows have `ts_unix == settlement_ts`.
4. Replay any batch: `python scripts/verify_program.py batch-004` re-runs that
   batch against the stored candles and compares per-participant ledger hashes
   against `manifest.json`. `global` replays all ten batches (slow).
5. The universe-level check is `manifest.json → universes → {universe} →
   combined_ledger_sha256`: a fold of the sorted per-participant ledger hashes.
   The replay proof in `manifest.json → replay` shows batch-001 was re-run after
   the full pass and matched.

## What is not in these files

- No equity curve per participant (drawdown and final equity are; see
  LIMITATIONS for why). The primary 11-participant competitions keep per-fill
  equity points in `data/sim/equity.json`.
- No invented prices. A missing candle is a missing row, not a zero.
- No real Kalshi user activity. `sim-` usernames are invented for the simulation.
