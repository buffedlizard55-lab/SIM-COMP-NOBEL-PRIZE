# SIM-COMP Nobel Prize

A research desk with two layers that are not allowed to blur:

1. **Nobel Prize record** — prizes, laureates, the official motivation, and the other names on the public nomination list where that list is open.
2. **Simulated Kalshi competition** — paper participants with different strategies, run on the same stored Kalshi prices and the same starting cash.

The site is the repository root. After this branch is on `main`, GitHub Pages serves it at [https://buffedlizard55-lab.github.io/SIM-COMP-NOBEL-PRIZE/](https://buffedlizard55-lab.github.io/SIM-COMP-NOBEL-PRIZE/).

Simulated names, orders, positions, and P&L are not Kalshi users and not real fills. The leaderboard says so on every view.

This project is not affiliated with, endorsed by, or sponsored by Kalshi, Nobel Prize Outreach, or the Nobel Foundation.

## Read this first

| Question | Where |
| --- | --- |
| Who is ahead, and why is that number paper? | Site leaderboard, or `data/sim/LEADERBOARD.md` |
| Show me the simulated order | `data/sim/trades.csv` |
| What Kalshi actually published? | `data/kalshi/markets.jsonl` and the API link on each market |
| What failed to download? | `data/kalshi/failures.json` |
| Prize, motivation, other nominees | `data/nobel/prizes.csv`, `data/nobel/nominations.csv`, site Nobel record |
| Rules of the simulation | [docs/METHOD.md](docs/METHOD.md) |
| What is still wrong or unfinished | [LIMITATIONS.md](LIMITATIONS.md) |

The earlier Nobel desk, used as the source of the prize catalog, is [buffedlizard55-lab/NOBEL-PRIZE](https://github.com/buffedlizard55-lab/NOBEL-PRIZE) and [its site](https://buffedlizard55-lab.github.io/NOBEL-PRIZE/). Provenance is in `data/nobel/PROVENANCE.md`.

## Refresh

The collector uses only the Python standard library and the public Kalshi Trade API. No API key. No paid endpoint.

```bash
python scripts/refresh.py
python -m unittest discover -s tests -v
```

`refresh.py` collects, simulates, then reruns the simulation and requires the same ledger. `--skip-collect` reruns from the stored snapshot.

GitHub Actions workflow **Collect Kalshi and simulate** runs on a schedule and on changes to `simcomp/` or `scripts/`. The build sandbox used for the first version could not open TLS to Kalshi or nobelprize.org. Actions can. Failed requests are recorded and left empty.

## Competitions

Primary runs, each with its own $10,000 paper bankroll:

- `nobel-forward-primary` — open Nobel markets. Unsettled. Rank is a liquidation mark, not a win rate.
- `nobel-settled-primary` — settled Nobel markets whose candles end before `settlement_ts`.
- `panel-settled-primary` — a capped settled panel (`KXHIGHNY`, `KXFEDDECISION`), not the whole exchange.

Assumption runs (fees off, larger size, wider momentum threshold, fill at last trade) are separate competitions. They are not the primary leaderboard.

## Sources

- [Kalshi market data quick start](https://docs.kalshi.com/getting_started/quick_start_market_data) — public endpoints, no key
- [Kalshi historical data](https://docs.kalshi.com/getting_started/historical_data)
- [Kalshi fee schedule](https://kalshi.com/fee-schedule) — range used to interpret quadratic taker fees
- [Nobel Prize API](https://www.nobelprize.org/about/developer-zone-2/)
- [Nomination archive](https://www.nobelprize.org/nomination/archive/) and its [manual](https://www.nobelprize.org/nomination/archive/manual.php)
