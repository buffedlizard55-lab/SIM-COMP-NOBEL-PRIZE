# Simulated leaderboards

Every participant, trade, position, and P&L figure in this competition is simulated. None of it is a Kalshi order, a Kalshi user, or a real fill. Market prices, results, and volumes are Kalshi data only where a source URL is shown.

Kalshi snapshot: 2026-09-24T20:11:30Z

## Nobel markets, forward simulation

Id: `nobel-forward-primary`. Kind: forward_simulation. Markets used: 147.

| Rank | Participant | Strategy | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-ada-hold | hold_cash | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 1 | sim-basil-favorite | favorite_hold | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 1 | sim-jonas-exit | favorite_exit | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 4 | sim-kira-null | seeded_null | 8659.7660 | 0.0000 | -1340.2340 | 125.1400 | 63 |
| 5 | sim-gina-tight | tight_value | 8329.5740 | 0.0000 | -1670.4260 | 205.7300 | 67 |
| 6 | sim-cleo-longshot | longshot_hold | 8040.1500 | 0.0000 | -1959.8500 | 225.8500 | 67 |
| 7 | sim-elena-revert | mean_revert | 7480.2900 | -2431.2800 | -88.4300 | 432.0200 | 136 |
| 8 | sim-hiro-slice | diversified_slice | 6101.7140 | 0.0000 | -3898.2860 | 359.4600 | 96 |
| 9 | sim-ines-volume | volume_momentum | 3493.2850 | -5458.8470 | -1047.8680 | 1451.5000 | 679 |
| 10 | sim-dmitri-momentum | momentum | 628.3940 | -9250.4870 | -121.1190 | 2063.9500 | 1397 |
| 11 | sim-farid-fade | contrarian | 411.4790 | -9282.4630 | -306.0580 | 2146.6200 | 1378 |

## Settled Nobel markets, historical backtest

Id: `nobel-settled-primary`. Kind: historical_backtest. Markets used: 66.

| Rank | Participant | Strategy | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-ada-hold | hold_cash | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 2 | sim-jonas-exit | favorite_exit | 9996.5500 | -3.4500 | 0.0000 | 6.1500 | 3 |
| 3 | sim-basil-favorite | favorite_hold | 9939.0100 | -60.9900 | 0.0000 | 3.8400 | 2 |
| 4 | sim-kira-null | seeded_null | 9590.5700 | -409.4300 | 0.0000 | 66.2700 | 47 |
| 5 | sim-elena-revert | mean_revert | 9273.2300 | -726.7700 | 0.0000 | 192.7000 | 49 |
| 6 | sim-hiro-slice | diversified_slice | 9223.9200 | -776.0800 | 0.0000 | 126.2800 | 32 |
| 7 | sim-gina-tight | tight_value | 9094.0200 | -905.9800 | 0.0000 | 111.4400 | 56 |
| 8 | sim-cleo-longshot | longshot_hold | 8757.7600 | -1242.2400 | 0.0000 | 162.2400 | 57 |
| 9 | sim-ines-volume | volume_momentum | 6510.7100 | -3489.2900 | 0.0000 | 1235.9100 | 541 |
| 10 | sim-dmitri-momentum | momentum | 3255.0100 | -6744.9900 | 0.0000 | 2001.5900 | 935 |
| 11 | sim-farid-fade | contrarian | 1548.0700 | -8451.9300 | 0.0000 | 2261.3100 | 1032 |

## Settled panel, historical backtest

Id: `panel-settled-primary`. Kind: historical_backtest. Markets used: 50.

| Rank | Participant | Strategy | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-ada-hold | hold_cash | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 2 | sim-jonas-exit | favorite_exit | 9778.6800 | -221.3200 | 0.0000 | 58.7800 | 30 |
| 3 | sim-basil-favorite | favorite_hold | 9742.4000 | -257.6000 | 0.0000 | 31.3400 | 16 |
| 4 | sim-kira-null | seeded_null | 9353.3700 | -646.6300 | 0.0000 | 90.6500 | 37 |
| 5 | sim-cleo-longshot | longshot_hold | 8772.6000 | -1227.4000 | 0.0000 | 127.4000 | 37 |
| 6 | sim-gina-tight | tight_value | 8642.2700 | -1357.7300 | 0.0000 | 156.3600 | 45 |
| 7 | sim-hiro-slice | diversified_slice | 8264.9200 | -1735.0800 | 0.0000 | 177.4300 | 45 |
| 8 | sim-elena-revert | mean_revert | 7884.7200 | -2115.2800 | 0.0000 | 744.5200 | 216 |
| 9 | sim-ines-volume | volume_momentum | 3609.0500 | -6390.9500 | 0.0000 | 2353.4400 | 1045 |
| 10 | sim-dmitri-momentum | momentum | 3223.0200 | -6776.9800 | 0.0000 | 2428.1900 | 1072 |
| 11 | sim-farid-fade | contrarian | 1657.3600 | -8342.6400 | 0.0000 | 4089.6900 | 1429 |

## The 1000-strategy research program

1000 simulated participants in 10 batches. 796975 ledger rows. Replay of batch-001: matched. Same decision clock, size rules, and fee reading as the primary competitions above. Full board: `data/sim/program/leaderboard.json` (top 10 per universe below).

### Program, Nobel markets, forward simulation

| Rank | Participant | Strategy | Family | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-b002-001 | favorite-band-b002-001 | favorite_band | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 1 | sim-b002-002 | favorite-band-b002-002 | favorite_band | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 1 | sim-b002-003 | favorite-band-b002-003 | favorite_band | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 1 | sim-b002-004 | favorite-band-b002-004 | favorite_band | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 1 | sim-b002-005 | favorite-band-b002-005 | favorite_band | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 1 | sim-b002-006 | favorite-band-b002-006 | favorite_band | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 1 | sim-b002-007 | favorite-band-b002-007 | favorite_band | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 1 | sim-b002-008 | favorite-band-b002-008 | favorite_band | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 1 | sim-b002-009 | favorite-band-b002-009 | favorite_band | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 1 | sim-b002-010 | favorite-band-b002-010 | favorite_band | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |

### Program, settled Nobel markets, historical backtest

| Rank | Participant | Strategy | Family | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-b001-044 | null-model-b001-044 | null_model | 10514.3900 | 514.3900 | 0.0000 | 70.8300 | 54 |
| 2 | sim-b009-020 | breakout-hold-b009-020 | breakout_hold | 10169.1600 | 169.1600 | 0.0000 | 41.2200 | 10 |
| 2 | sim-b009-021 | breakout-hold-b009-021 | breakout_hold | 10169.1600 | 169.1600 | 0.0000 | 41.2200 | 10 |
| 4 | sim-b009-019 | breakout-hold-b009-019 | breakout_hold | 10165.9400 | 165.9400 | 0.0000 | 44.4300 | 10 |
| 5 | sim-b001-071 | null-model-b001-071 | null_model | 10158.7300 | 158.7300 | 0.0000 | 37.1500 | 31 |
| 6 | sim-b001-019 | null-model-b001-019 | null_model | 10132.8200 | 132.8200 | 0.0000 | 66.1000 | 50 |
| 7 | sim-b001-063 | null-model-b001-063 | null_model | 10126.3700 | 126.3700 | 0.0000 | 28.4600 | 22 |
| 8 | sim-b001-072 | null-model-b001-072 | null_model | 10107.1700 | 107.1700 | 0.0000 | 38.7900 | 31 |
| 9 | sim-b001-041 | null-model-b001-041 | null_model | 10098.2700 | 98.2700 | 0.0000 | 70.1000 | 54 |
| 10 | sim-b001-085 | null-model-b001-085 | null_model | 10074.8600 | 74.8600 | 0.0000 | 71.8300 | 61 |

### Program, settled panel, historical backtest

| Rank | Participant | Strategy | Family | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-b001-066 | null-model-b001-066 | null_model | 10792.3500 | 792.3500 | 0.0000 | 33.9000 | 19 |
| 2 | sim-b001-012 | null-model-b001-012 | null_model | 10705.5600 | 705.5600 | 0.0000 | 74.7900 | 39 |
| 3 | sim-b001-081 | null-model-b001-081 | null_model | 10592.9600 | 592.9600 | 0.0000 | 101.6500 | 45 |
| 4 | sim-b001-003 | null-model-b001-003 | null_model | 10554.3900 | 554.3900 | 0.0000 | 80.4900 | 37 |
| 5 | sim-b001-014 | null-model-b001-014 | null_model | 10554.3600 | 554.3600 | 0.0000 | 61.6900 | 34 |
| 6 | sim-b001-071 | null-model-b001-071 | null_model | 10553.8300 | 553.8300 | 0.0000 | 53.5400 | 23 |
| 7 | sim-b001-055 | null-model-b001-055 | null_model | 10551.5400 | 551.5400 | 0.0000 | 53.3400 | 19 |
| 8 | sim-b001-028 | null-model-b001-028 | null_model | 10526.8200 | 526.8200 | 0.0000 | 77.7500 | 34 |
| 9 | sim-b001-016 | null-model-b001-016 | null_model | 10404.1300 | 404.1300 | 0.0000 | 76.9200 | 33 |
| 10 | sim-b001-018 | null-model-b001-018 | null_model | 10350.9500 | 350.9500 | 0.0000 | 53.0700 | 31 |

A null-model participant (batch-001) is a random valid entry, not a trader. Outranking batch-001's band is the floor any finding has to clear.