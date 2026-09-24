# SIM-COMP Nobel Prize

A research desk with two layers that are not allowed to blur:

1. **Nobel Prize record** — prizes, laureates, the official motivation, and the other names on the public nomination list where that list is open.
2. **Simulated Kalshi competition** — 2,011 paper participants (11 primary + a 2,000-strategy research program in 20 batches of 100) with different predeclared strategies, run on the same stored Kalshi prices and the same starting cash. Every family has a research card (question, mechanism, information channels, predicted sign, falsification condition, verified sources) and is judged by predeclared rules against a random-entry null and, where one exists, a matched placebo.

The site is the repository root. After this branch is on `main`, GitHub Pages serves it at [https://buffedlizard55-lab.github.io/SIM-COMP-NOBEL-PRIZE/](https://buffedlizard55-lab.github.io/SIM-COMP-NOBEL-PRIZE/). The working competition leaderboard is the **Program board** view. The **Research** view is the verdict table: which strategy ideas beat the random-entry null, their own placebo, and a leave-one-event-out check, and which did not.

Two questions organize the site. **Maximize P(Win):** the leaderboard's P(Win) card lists the families most often in the top decile of each settled universe. **Own the Outcome:** every simulated number is recomputable from stored Kalshi data (`scripts/audit_program.py`, `scripts/verify_program.py`), and every verdict prints the rule, the evidence, and the condition that would overturn it.

Simulated names, orders, positions, and P&L are not Kalshi users and not real fills. The leaderboard says so on every view.

This project is not affiliated with, endorsed by, or sponsored by Kalshi, Nobel Prize Outreach, or the Nobel Foundation.

## Read this first

| Question | Where |
| --- | --- |
| The working leaderboard (2,000 strategies) | Site **Program board**, or `data/sim/program/leaderboard.json` / `.csv` |
| Which strategy ideas held up, and why? | Site **Research**, `data/sim/program/research.json`, or [docs/RESEARCH.md](docs/RESEARCH.md) (generated each build) |
| Who is ahead in the primary 11, and why is that paper? | Site leaderboard, or `data/sim/LEADERBOARD.md` |
| Show me a simulated order | `data/sim/trades.csv` (primary) and `data/sim/program/trades/{batch}/{universe}.csv.gz` (program) |
| The twenty research topics and 2,000 hypotheses | Site **Topics**, or `docs/PROGRAM.md` and `data/sim/program/strategies.json` |
| Family results vs the null band | Site **Families**, or `data/sim/program/families.json` |
| What Kalshi actually published? | `data/kalshi/markets.jsonl` and the API link on each market |
| What failed to download? | `data/kalshi/failures.json` |
| Prize, motivation, other nominees | `data/nobel/prizes.csv`, `data/nobel/nominations.csv`, site Nobel record |
| Rules of the simulation | [docs/METHOD.md](docs/METHOD.md) |
| Program batch plan and verification | [docs/PROGRAM.md](docs/PROGRAM.md) |
| What is still wrong or unfinished | [LIMITATIONS.md](LIMITATIONS.md) |

The earlier Nobel desk, used as the source of the prize catalog, is [buffedlizard55-lab/NOBEL-PRIZE](https://github.com/buffedlizard55-lab/NOBEL-PRIZE) and [its site](https://buffedlizard55-lab.github.io/NOBEL-PRIZE/). Provenance is in `data/nobel/PROVENANCE.md`.

## Refresh and verify

The collector uses only the Python standard library and the public Kalshi Trade API. No API key. No paid endpoint.

```bash
python scripts/refresh.py                 # collect, build the 11 primary competitions, run the 2,000-strategy program
python -m unittest discover -s tests -v   # engine, parity, registry, and catalog tests
python scripts/audit_program.py           # line-by-line audit of the program ledger against stored candles
python scripts/verify_program.py batch-004 # re-run one batch and compare ledger hashes
python scripts/verify_program.py global   # re-run all twenty batches (slow)
python scripts/refresh.py --skip-collect  # rebuild everything from the stored snapshot
python scripts/refresh.py --skip-collect --skip-program  # primary competitions only
```

`refresh.py` collects, builds, and runs the program. The build reruns the primary competitions twice and refuses a mismatched ledger; the program replays batches 001, 011, 013 and 018 (null, event channel, settled-pool channel, exits) across all three universes and aborts on hash mismatch. A full rebuild from the stored snapshot takes about 5 minutes in the development sandbox.

GitHub Actions workflow **Collect Kalshi and simulate** runs on a schedule and on changes to `simcomp/` or `scripts/`, and commits `data/kalshi`, `data/sim` and `docs/RESEARCH.md`. Workflow **Tests** runs the unit tests and a syntax check of `app.js` on pull requests. The build sandbox used for development cannot open TLS to Kalshi or nobelprize.org. Actions can. Failed requests are recorded and left empty.

## Competitions

Primary runs, each with its own $10,000 paper bankroll:

- `nobel-forward-primary` — open Nobel markets. Unsettled. Rank is a liquidation mark, not a win rate.
- `nobel-settled-primary` — settled Nobel markets whose candles end before `settlement_ts`.
- `panel-settled-primary` — a capped settled panel (`KXHIGHNY`, `KXFEDDECISION`) among the first 2000 historical rows per series, not the whole exchange.

Assumption runs (fees off, larger size, wider momentum threshold, fill at last trade) are separate competitions. They are not the primary leaderboard.

The research program reruns the same three universes with 2,000 parameterized strategies in 20 batches. Besides a market's own candles, program strategies may read declared information channels: sibling contracts in the same Kalshi event at or before T, official results of markets settled strictly before T, and Kalshi's published `strike_date` (never `close_time`; see METHOD.md). Program competition ids are `program-nobel-forward`, `program-nobel-settled`, and `program-panel-settled`. Batch-001 is the random-entry null reference; its per-universe band is the floor any family has to clear.

## Sources

- [Kalshi market data quick start](https://docs.kalshi.com/getting_started/quick_start_market_data) — public endpoints, no key
- [Kalshi historical data](https://docs.kalshi.com/getting_started/historical_data)
- [Kalshi fee schedule](https://kalshi.com/fee-schedule) — range used to interpret quadratic taker fees
- [Nobel Prize API](https://www.nobelprize.org/about/developer-zone-2/)
- [Nomination archive](https://www.nobelprize.org/nomination/archive/) and its [manual](https://www.nobelprize.org/nomination/archive/manual.php)
