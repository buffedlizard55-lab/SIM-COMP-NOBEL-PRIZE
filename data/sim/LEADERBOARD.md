# Simulated leaderboards

Every participant, trade, position, and P&L figure in this competition is simulated. None of it is a Kalshi order, a Kalshi user, or a real fill. Market prices, results, and volumes are Kalshi data only where a source URL is shown.

Kalshi snapshot: 2026-10-07T19:19:23Z

## Nobel markets, forward simulation

Id: `nobel-forward-primary`. Kind: forward_simulation. Markets used: 63.

| Rank | Participant | Strategy | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-ada-hold | hold_cash | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 1 | sim-basil-favorite | favorite_hold | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 1 | sim-jonas-exit | favorite_exit | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 4 | sim-kira-null | seeded_null | 9172.6900 | 0.0000 | -827.3100 | 70.7100 | 37 |
| 5 | sim-gina-tight | tight_value | 9032.6000 | 0.0000 | -967.4000 | 131.0000 | 60 |
| 6 | sim-hiro-slice | diversified_slice | 8770.0600 | 0.0000 | -1229.9400 | 136.4800 | 37 |
| 7 | sim-elena-revert | mean_revert | 8390.0600 | -1512.3300 | -97.6100 | 283.0500 | 98 |
| 8 | sim-cleo-longshot | longshot_hold | 8367.4600 | 0.0000 | -1632.5400 | 171.0400 | 60 |
| 9 | sim-ines-volume | volume_momentum | 4192.3910 | -5267.4810 | -540.1280 | 1399.6600 | 675 |
| 10 | sim-dmitri-momentum | momentum | 489.5930 | -9418.7780 | -91.6290 | 2171.1400 | 1382 |
| 11 | sim-farid-fade | contrarian | 391.0440 | -9409.5770 | -199.3790 | 2315.9600 | 1426 |

## Settled Nobel markets, historical backtest

Id: `nobel-settled-primary`. Kind: historical_backtest. Markets used: 157.

| Rank | Participant | Strategy | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-ada-hold | hold_cash | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 2 | sim-jonas-exit | favorite_exit | 9996.5500 | -3.4500 | 0.0000 | 6.1500 | 3 |
| 3 | sim-basil-favorite | favorite_hold | 9939.0100 | -60.9900 | 0.0000 | 3.8400 | 2 |
| 4 | sim-kira-null | seeded_null | 8443.2850 | -1556.7150 | 0.0000 | 168.3400 | 88 |
| 5 | sim-elena-revert | mean_revert | 6678.0500 | -3321.9500 | 0.0000 | 622.0400 | 171 |
| 6 | sim-gina-tight | tight_value | 5873.8300 | -4126.1700 | 0.0000 | 296.7900 | 111 |
| 7 | sim-ines-volume | volume_momentum | 4839.4600 | -5160.5400 | 0.0000 | 1531.3000 | 715 |
| 8 | sim-hiro-slice | diversified_slice | 3879.1500 | -6120.8500 | 0.0000 | 456.8300 | 123 |
| 9 | sim-cleo-longshot | longshot_hold | 3863.4300 | -6136.5700 | 0.0000 | 476.5700 | 148 |
| 10 | sim-dmitri-momentum | momentum | 3255.0100 | -6744.9900 | 0.0000 | 2001.5900 | 935 |
| 11 | sim-farid-fade | contrarian | 1548.0900 | -8451.9100 | 0.0000 | 2261.3300 | 1034 |

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

## The research program (2,000 simulated participants)

2000 simulated participants in 20 batches. 1024115 ledger rows. Replay of batch-001, batch-011, batch-013, batch-018: matched. Same decision clock, size rules, and fee reading as the primary competitions above. Full board: `data/sim/program/leaderboard.json` (top 10 per universe below).

### Program, Nobel markets, forward simulation

| Rank | Participant | Strategy | Family | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-b011-091 | placebo-event-leader-b011-091 | placebo_event_leader | 10092.9000 | 0.0000 | 92.9000 | 7.3400 | 3 |
| 1 | sim-b011-095 | placebo-event-leader-b011-095 | placebo_event_leader | 10092.9000 | 0.0000 | 92.9000 | 7.3400 | 3 |
| 3 | sim-b017-064 | cash-reserve-gate-b017-064 | cash_reserve_gate | 10080.4000 | 0.0000 | 80.4000 | 7.2100 | 10 |
| 4 | sim-b013-079 | uniform-field-prior-b013-079 | uniform_field_prior | 10073.3600 | 0.0000 | 73.3600 | 4.7600 | 2 |
| 4 | sim-b013-082 | uniform-field-prior-b013-082 | uniform_field_prior | 10073.3600 | 0.0000 | 73.3600 | 4.7600 | 2 |
| 6 | sim-b013-048 | learned-base-rate-b013-048 | learned_base_rate | 10067.4300 | 0.0000 | 67.4300 | 8.7300 | 4 |
| 7 | sim-b013-084 | uniform-field-prior-b013-084 | uniform_field_prior | 10066.0600 | 0.0000 | 66.0600 | 8.6500 | 4 |
| 8 | sim-b013-085 | uniform-field-prior-b013-085 | uniform_field_prior | 10063.4350 | 0.0000 | 63.4350 | 16.5100 | 17 |
| 9 | sim-b013-083 | uniform-field-prior-b013-083 | uniform_field_prior | 10062.4200 | 0.0000 | 62.4200 | 11.6700 | 9 |
| 10 | sim-b013-086 | uniform-field-prior-b013-086 | uniform_field_prior | 10047.8400 | 0.0000 | 47.8400 | 9.7900 | 6 |

### Program, settled Nobel markets, historical backtest

| Rank | Participant | Strategy | Family | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-b017-038 | edge-scaled-size-b017-038 | edge_scaled_size | 10758.8200 | 758.8200 | 0.0000 | 61.7300 | 100 |
| 2 | sim-b012-027 | logit-scale-b012-027 | logit_scale | 10758.4600 | 758.4600 | 0.0000 | 61.7000 | 100 |
| 2 | sim-b017-040 | edge-scaled-size-b017-040 | edge_scaled_size | 10758.4600 | 758.4600 | 0.0000 | 61.7000 | 100 |
| 4 | sim-b013-024 | learned-bucket-calibration-b013-024 | learned_bucket_calibration | 10753.1500 | 753.1500 | 0.0000 | 59.9000 | 53 |
| 5 | sim-b013-085 | uniform-field-prior-b013-085 | uniform_field_prior | 10743.6200 | 743.6200 | 0.0000 | 65.9900 | 52 |
| 6 | sim-b017-015 | kelly-fraction-b017-015 | kelly_fraction | 10727.2200 | 727.2200 | 0.0000 | 61.4000 | 102 |
| 7 | sim-b017-008 | kelly-fraction-b017-008 | kelly_fraction | 10724.0000 | 724.0000 | 0.0000 | 58.4800 | 92 |
| 8 | sim-b012-001 | logit-scale-b012-001 | logit_scale | 10722.2900 | 722.2900 | 0.0000 | 52.9600 | 68 |
| 9 | sim-b012-017 | logit-scale-b012-017 | logit_scale | 10721.4700 | 721.4700 | 0.0000 | 59.2800 | 100 |
| 10 | sim-b017-012 | kelly-fraction-b017-012 | kelly_fraction | 10715.8200 | 715.8200 | 0.0000 | 61.1900 | 102 |

### Program, settled panel, historical backtest

| Rank | Participant | Strategy | Family | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-b015-070 | spread-compression-b015-070 | spread_compression | 11014.1000 | 1014.1000 | 0.0000 | 33.5200 | 16 |
| 2 | sim-b013-075 | learned-age-calibration-b013-075 | learned_age_calibration | 10989.1900 | 989.1900 | 0.0000 | 79.3100 | 46 |
| 3 | sim-b013-073 | learned-age-calibration-b013-073 | learned_age_calibration | 10801.8400 | 801.8400 | 0.0000 | 58.2200 | 36 |
| 3 | sim-b013-077 | learned-age-calibration-b013-077 | learned_age_calibration | 10801.8400 | 801.8400 | 0.0000 | 58.2200 | 36 |
| 5 | sim-b013-013 | learned-bucket-calibration-b013-013 | learned_bucket_calibration | 10800.7100 | 800.7100 | 0.0000 | 57.8000 | 36 |
| 5 | sim-b013-017 | learned-bucket-calibration-b013-017 | learned_bucket_calibration | 10800.7100 | 800.7100 | 0.0000 | 57.8000 | 36 |
| 7 | sim-b001-066 | null-model-b001-066 | null_model | 10792.3500 | 792.3500 | 0.0000 | 33.9000 | 19 |
| 8 | sim-b013-014 | learned-bucket-calibration-b013-014 | learned_bucket_calibration | 10780.0100 | 780.0100 | 0.0000 | 56.5100 | 33 |
| 8 | sim-b013-018 | learned-bucket-calibration-b013-018 | learned_bucket_calibration | 10780.0100 | 780.0100 | 0.0000 | 56.5100 | 33 |
| 10 | sim-b020-082 | null-matched-rate-b020-082 | null_matched_rate | 10763.4900 | 763.4900 | 0.0000 | 94.5800 | 30 |

A null-model participant (batch-001) is a random valid entry, not a trader. Outranking batch-001's band is the floor any finding has to clear. Family verdicts under predeclared rules (null band, matched placebo, leave-one-event-out, power) are in `docs/RESEARCH.md`.