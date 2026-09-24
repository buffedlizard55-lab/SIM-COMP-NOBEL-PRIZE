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

## The research program (2,000 strategies, 20 batches)

The program layer (`simcomp/research_program.py`, `simcomp/research_phase2.py`,
`simcomp/program.py`) is the same simulation under a batch discipline:

- Everything above applies unchanged: the decision clock, fill fields, size rules,
  fee reading and no participant-to-participant trading.
  - The two engines share `compute_fill`.
  - `tests/test_program.py ParityTests` proves they produce the same ledger,
    equity, P&L, fees and drawdown for the same strategies.
- 2,000 variants are enumerated one at a time in the registry, in 20 research
  topics of 100 variants each. Parameters and research cards were declared
  before any run.
- Batch-001 is the null reference: random valid entries driven by stored SHA-256
  seeds. 21 families also have a matched placebo in the same batch. The placebo
  runs the family's own trigger (same markets, timestamps and contract count) but
  picks the side of each buy with a seeded coin, which isolates the value of
  choosing the side.
- A program strategy receives at most the 24 prior candles of its own market.
- Program ledgers are compact CSV (`data/sim/program/trades/{batch}/{universe}.csv.gz`).
  - The price always names the stored candle field it came from (`YA`, `YB`,
    `NA`, `NB`, `MR`).
  - Settlement rows are the only rows that use the official result, and they
    sit exactly at `settlement_ts`.
- After every full pass, batches 001, 011, 013 and 018 are re-run in all three
  universes. Every per-participant ledger hash must match
  (`manifest.json → replay`), or the build refuses to write the bundle.
- Verdict rules are in `simcomp/analysis.py` and on the site's Research view;
  see docs/PROGRAM.md.

### Information channels (what a program strategy may read at decision time T)

Each research card lists the channels its family reads. The engine builds each
channel so that nothing dated after T can reach the strategy
(`simcomp/context.py`; tests in `tests/test_phase2.py ChannelLookahead`).

| Channel | What it contains at T | Source field |
| --- | --- | --- |
| `own_candles` | This market's decision candle and at most 24 prior candles: closing bid, ask, trade, volume and open interest. | Kalshi candlesticks, `end_period_ts <= T` |
| `own_book` | The participant's own simulated cash and position. | Engine state |
| `event_quotes` | The latest candle **at or before T** of every stored contract in the same Kalshi event. A sibling with no candle yet at T is absent, not zero. | Kalshi candlesticks plus `event_ticker` |
| `settled_pool` | Official results of markets whose `settlement_ts` is **strictly before T**. Includes each market's pre-settlement reference-price path (candles ending before its own settlement), for walk-forward calibration. | Kalshi `result` and `settlement_ts` |
| `schedule` | The event's published `strike_date`. Empty for Nobel events, which have none. | Kalshi Get Event `strike_date` |
| `clock` | The decision timestamp: UTC hour, weekday, and market age since `open_time`. | Candle `end_period_ts`, market `open_time` |
| `seed` | A SHA-256 draw from a fixed seed. Carries no market information. | Code |

No channel ever carries the following:

- `result`, `settlement_value` or `expiration_value` of the market being decided;
- any candle ending after T;
- `close_time` or `expected_expiration_time`.

On settled Nobel markets, `close_time` is revised to the moment trading was
halted after the announcement, which is after-the-fact information
(KXNOBELLIT-25 and KXNOBELECON-25 were checked on 2026-09-24).
`expected_expiration_time` is uninformative. The schedule parser refuses
`close_time`-style values.

Two field facts limit what can be tested on Nobel (checked against the Get Event
endpoint on 2026-09-24):

- Nobel events report `mutually_exclusive: false`.
- Nobel events have no `strike_date`.

As a result, the sum-over-event family `event_underround_yes` never fires on
Nobel (it shows NOT TESTED), and the batch-014 horizon rules are tested on the
panel only. Event families that read sibling prices still run on Nobel, behind a
probability-mass gate, because stored sibling sums are incomplete. The Kalshi
docs say nested markets of older historical events can be omitted.

## Reproduction

`python scripts/refresh.py` collects, simulates, and reruns the simulation to require an identical ledger. `python scripts/refresh.py --skip-collect` reruns from the stored snapshot. The input hash is the SHA-256 of `data/kalshi/markets.jsonl`.

## How scope was chosen

The useful complete set is every public Nobel contract Kalshi lists, plus a small settled panel so strategies can be compared after an official result. Downloading the entire exchange was not required to answer the research questions, and inventing the missing history would have made the answers false. The collector is scheduled so the snapshot can grow without hand entry.
