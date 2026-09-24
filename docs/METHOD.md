# Method

This note is the rule book for the desk. The site summarizes it. If they disagree, this file and the code win, and the disagreement should be fixed.

## What is real, and what is paper

Kalshi fields come from the public Trade API at `https://external-api.kalshi.com/trade-api/v2`. Each stored market names the URL it came from. Candles name the candlestick URL. The fetch time is in `data/kalshi/manifest.json`.

Simulated usernames, orders, positions, fees, and P&L are produced by `simcomp/engine.py`. They are not orders on Kalshi. Participants do not trade with each other. A shared invented order book would be invented prices, so the competition is a parallel paper run on the same stored quotes and the same starting cash.

## Decision clock

A decision at candle end T may use:

- that market's candles with `end_period_ts <= T`
- only if T is strictly before `settlement_ts`, when a settlement timestamp exists
- the participant's own simulated cash and position

It may not use:

- `result`, `settlement_value`, or `expiration_value`
- a candle that ends at or after settlement
- the high or low inside a candle as a fill price
- the order book fetched at collection time, which is later than the candle close
- another participant's orders

Fills use the closing quote: buy YES at the yes-ask close, sell YES at the yes-bid close, buy NO at `1 - yes bid close`, sell NO at `1 - yes ask close`. A quote of 0 or 1 is treated as an empty book, not a price. If the quote is missing, there is no fill.

If a market is finalized and `settlement_ts` is missing, the engine does not trade it and does not invent a settlement time.

The official result is copied onto the ledger after the decision loop. The column says it was not used in the decision. Settlement cash is applied at `settlement_ts` by the engine, not by a strategy.

## Size and fees

Every participant starts with $10,000 simulated cash. A new entry targets $100 of premium, capped at 5% of starting cash, 500 contracts, and $300 of cost basis in one market. Those caps are competition rules, so strategy differences are about when and what they trade. The size-250 runs relax the entry target and the per-market cap.

`fee_type` and `fee_multiplier` come from the series payload. The 0.07 coefficient does not. The [Kalshi fee schedule](https://kalshi.com/fee-schedule), retrieved 2026-09-24, lists most markets at multiplier 1 with a taker fee range of $0.07–$1.75 per 100 contracts. The engine charges

`round up to the next cent of multiplier × 0.07 × contracts × price × (1 − price)`

on taker-style fills when `fee_type` starts with `quadratic`. That formula matches the published range at a 1-cent price and at 50 cents. It is an interpretation of the schedule page, not a field in the market payload. Fee-off runs exist so the rank can be checked without it. Series marked `quadratic_with_maker_fees` are charged the taker formula only; the maker schedule is not applied, and the fee model id says so. No separate settlement fee is charged, because the fetched market payload does not show one.

## Universes

Nobel universe: every non-multivariate market the collector could retrieve for a series whose ticker or title contains `NOBEL`, from both the live and historical market endpoints. Open or unsettled markets go to the forward competition. Markets with an official `yes` or `no` result and a settlement timestamp go to the historical Nobel competition.

Panel universe: not the whole exchange. For `KXHIGHNY` and `KXFEDDECISION`, the collector keeps at most 25 settled binary markets with a settlement timestamp, at least six hours between open and settlement, and volume greater than zero, highest volume first, among the first 2000 historical rows returned for that series. That is not a global volume ranking. If a series 404s, it is listed in `failures.json` and left empty.

A series whose ticker contains `NOBEL` is not automatically a prize-winner market. `KXTRUMPNOBEL` is a name match. The contract rules are the market.

Failed requests are not filled in.

## Nobel archive

Prize rows, names, portions, amounts, dates, and motivations come from the Nobel Prize API, via the 2026-09-24 catalog in `data/nobel/`. The stated reason a prize was given is the official motivation. The institutions do not publish a ranked explanation of why that work was chosen over other nominated work. Nomination counts are not votes. See the [nomination archive manual](https://www.nobelprize.org/nomination/archive/manual.php).

Other candidates are the names on stored nomination-archive list pages. Sealed years have empty nominee lists. Economic sciences is not in the public nomination archive. Neither gap is filled with guesses.

## The research program (1,000 strategies, 10 batches)

The program layer (`simcomp/research_program.py`, `simcomp/program.py`) is the same
simulation under a batch discipline:

- Everything above applies unchanged: decision clock, fill fields, size rules, fee
  reading, no participant-to-participant trading. The two engines share
  `compute_fill`, and `tests/test_program.py ParityTests` proves they produce the
  same ledger, equity, P&L, fees, and drawdown for the same strategies.
- 1,000 variants are enumerated one at a time in the registry, grouped into 10
  research topics of 100 variants each. Parameters are predeclared before any run.
- Batch-001 is the null reference: random valid entries driven by stored SHA-256
  seeds. Every family result is displayed next to the null band. A median inside
  the band is not an edge.
- A program strategy receives at most the 24 prior candles of its market. Every
  declared lookback fits inside the window; the registry and tests refuse a
  variant that needs more.
- Program ledgers are compact CSV (`data/sim/program/trades/{batch}/{universe}.csv.gz`).
  The price always names the stored candle field it came from (`YA`, `YB`, `NA`,
  `NB`, `MR`). Settlement rows are the only rows that use the official result,
  and they sit exactly at `settlement_ts`.
- After every full pass, batch-001 is rerun in all three universes and every
  per-participant ledger hash must match (`manifest.json → replay`), or the build
  refuses to write the bundle.
- `scripts/audit_program.py` replays the CSV ledgers against the stored candles:
  cash chain, realized P&L, decision clock, sampled fill prices, and manifest
  hashes. `scripts/verify_program.py` re-runs a batch end to end.

## Reproduction

`python scripts/refresh.py` collects, simulates, and reruns the simulation to require an identical ledger. `python scripts/refresh.py --skip-collect` reruns from the stored snapshot. The input hash is the SHA-256 of `data/kalshi/markets.jsonl`.

## How scope was chosen

The useful complete set is every public Nobel contract Kalshi lists, plus a small settled panel so strategies can be compared after an official result. Downloading the entire exchange was not required to answer the research questions, and inventing the missing history would have made the answers false. The collector is scheduled so the snapshot can grow without hand entry.
