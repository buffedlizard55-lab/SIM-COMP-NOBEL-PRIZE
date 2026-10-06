# Simulated leaderboards

Every participant, trade, position, and P&L figure in this competition is simulated. None of it is a Kalshi order, a Kalshi user, or a real fill. Market prices, results, and volumes are Kalshi data only where a source URL is shown.

Kalshi snapshot: 2026-10-06T18:53:49Z

## Nobel markets, forward simulation

Id: `nobel-forward-primary`. Kind: forward_simulation. Markets used: 90.

| Rank | Participant | Strategy | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-ada-hold | hold_cash | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 1 | sim-basil-favorite | favorite_hold | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 1 | sim-jonas-exit | favorite_exit | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 4 | sim-kira-null | seeded_null | 8980.3500 | 0.0000 | -1019.6500 | 99.2900 | 47 |
| 5 | sim-gina-tight | tight_value | 8620.4600 | 0.0000 | -1379.5400 | 194.6400 | 86 |
| 6 | sim-elena-revert | mean_revert | 8222.9100 | -1789.4300 | 12.3400 | 331.2400 | 118 |
| 7 | sim-hiro-slice | diversified_slice | 7745.4400 | 0.0000 | -2254.5600 | 226.7100 | 65 |
| 8 | sim-cleo-longshot | longshot_hold | 7644.1600 | 0.0000 | -2355.8400 | 252.8400 | 88 |
| 9 | sim-ines-volume | volume_momentum | 4066.7480 | -5347.0510 | -586.2010 | 1436.9200 | 686 |
| 10 | sim-dmitri-momentum | momentum | 525.8150 | -9353.0680 | -121.1170 | 2166.0900 | 1367 |
| 11 | sim-farid-fade | contrarian | 433.6530 | -9384.4950 | -181.8520 | 2309.9100 | 1417 |

## Settled Nobel markets, historical backtest

Id: `nobel-settled-primary`. Kind: historical_backtest. Markets used: 127.

| Rank | Participant | Strategy | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-ada-hold | hold_cash | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 2 | sim-jonas-exit | favorite_exit | 9996.5500 | -3.4500 | 0.0000 | 6.1500 | 3 |
| 3 | sim-basil-favorite | favorite_hold | 9939.0100 | -60.9900 | 0.0000 | 3.8400 | 2 |
| 4 | sim-kira-null | seeded_null | 8942.8550 | -1057.1450 | 0.0000 | 139.7600 | 78 |
| 5 | sim-gina-tight | tight_value | 7092.1600 | -2907.8400 | 0.0000 | 223.4600 | 82 |
| 6 | sim-elena-revert | mean_revert | 7031.4200 | -2968.5800 | 0.0000 | 543.6700 | 144 |
| 7 | sim-hiro-slice | diversified_slice | 5627.6300 | -4372.3700 | 0.0000 | 357.9300 | 93 |
| 8 | sim-cleo-longshot | longshot_hold | 5388.9000 | -4611.1000 | 0.0000 | 386.1000 | 118 |
| 9 | sim-ines-volume | volume_momentum | 4840.5400 | -5159.4600 | 0.0000 | 1531.3400 | 714 |
| 10 | sim-dmitri-momentum | momentum | 3255.0100 | -6744.9900 | 0.0000 | 2001.5900 | 935 |
| 11 | sim-farid-fade | contrarian | 1548.0100 | -8451.9900 | 0.0000 | 2261.3200 | 1033 |

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

2000 simulated participants in 20 batches. 1007423 ledger rows. Replay of batch-001, batch-011, batch-013, batch-018: matched. Same decision clock, size rules, and fee reading as the primary competitions above. Full board: `data/sim/program/leaderboard.json` (top 10 per universe below).

### Program, Nobel markets, forward simulation

| Rank | Participant | Strategy | Family | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-b013-083 | uniform-field-prior-b013-083 | uniform_field_prior | 10101.0400 | 0.0000 | 101.0400 | 16.8200 | 12 |
| 2 | sim-b013-086 | uniform-field-prior-b013-086 | uniform_field_prior | 10097.5200 | 0.0000 | 97.5200 | 13.9200 | 8 |
| 3 | sim-b013-085 | uniform-field-prior-b013-085 | uniform_field_prior | 10094.8870 | 0.0000 | 94.8870 | 25.2600 | 23 |
| 4 | sim-b011-095 | placebo-event-leader-b011-095 | placebo_event_leader | 10093.8900 | 0.0000 | 93.8900 | 9.7200 | 4 |
| 5 | sim-b013-081 | uniform-field-prior-b013-081 | uniform_field_prior | 10092.1200 | 0.0000 | 92.1200 | 11.6000 | 6 |
| 6 | sim-b013-048 | learned-base-rate-b013-048 | learned_base_rate | 10090.3400 | 0.0000 | 90.3400 | 11.1100 | 5 |
| 7 | sim-b013-084 | uniform-field-prior-b013-084 | uniform_field_prior | 10088.9500 | 0.0000 | 88.9500 | 11.0300 | 5 |
| 8 | sim-b013-045 | learned-base-rate-b013-045 | learned_base_rate | 10084.3900 | 0.0000 | 84.3900 | 15.0400 | 9 |
| 9 | sim-b017-064 | cash-reserve-gate-b017-064 | cash_reserve_gate | 10078.3800 | 0.0000 | 78.3800 | 7.2100 | 10 |
| 10 | sim-b013-047 | learned-base-rate-b013-047 | learned_base_rate | 10078.0300 | 0.0000 | 78.0300 | 14.3400 | 8 |

### Program, settled Nobel markets, historical backtest

| Rank | Participant | Strategy | Family | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-b013-024 | learned-bucket-calibration-b013-024 | learned_bucket_calibration | 10632.0100 | 632.0100 | 0.0000 | 53.3200 | 49 |
| 2 | sim-b013-085 | uniform-field-prior-b013-085 | uniform_field_prior | 10605.2200 | 605.2200 | 0.0000 | 58.2200 | 46 |
| 3 | sim-b012-001 | logit-scale-b012-001 | logit_scale | 10601.3200 | 601.3200 | 0.0000 | 44.6300 | 51 |
| 4 | sim-b012-081 | fee-aware-logit-b012-081 | fee_aware_logit | 10575.1900 | 575.1900 | 0.0000 | 43.0900 | 47 |
| 5 | sim-b017-060 | cash-reserve-gate-b017-060 | cash_reserve_gate | 10572.8500 | 572.8500 | 0.0000 | 42.9500 | 50 |
| 6 | sim-b017-037 | edge-scaled-size-b017-037 | edge_scaled_size | 10520.7000 | 520.7000 | 0.0000 | 46.2800 | 54 |
| 7 | sim-b012-011 | logit-scale-b012-011 | logit_scale | 10519.6600 | 519.6600 | 0.0000 | 46.7300 | 54 |
| 7 | sim-b017-007 | kelly-fraction-b017-007 | kelly_fraction | 10519.6600 | 519.6600 | 0.0000 | 46.7300 | 54 |
| 7 | sim-b017-010 | kelly-fraction-b017-010 | kelly_fraction | 10519.6600 | 519.6600 | 0.0000 | 46.7300 | 54 |
| 7 | sim-b017-013 | kelly-fraction-b017-013 | kelly_fraction | 10519.6600 | 519.6600 | 0.0000 | 46.7300 | 54 |

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