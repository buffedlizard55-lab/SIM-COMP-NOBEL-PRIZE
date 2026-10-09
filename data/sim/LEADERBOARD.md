# Simulated leaderboards

Every participant, trade, position, and P&L figure in this competition is simulated. None of it is a Kalshi order, a Kalshi user, or a real fill. Market prices, results, and volumes are Kalshi data only where a source URL is shown.

Kalshi snapshot: 2026-10-09T18:47:50Z

## Nobel markets, forward simulation

Id: `nobel-forward-primary`. Kind: forward_simulation. Markets used: 12.

| Rank | Participant | Strategy | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-ada-hold | hold_cash | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 1 | sim-basil-favorite | favorite_hold | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 1 | sim-jonas-exit | favorite_exit | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 4 | sim-kira-null | seeded_null | 9909.1200 | 0.0000 | -90.8800 | 19.0600 | 12 |
| 5 | sim-gina-tight | tight_value | 9880.4500 | 0.0000 | -119.5500 | 29.5500 | 12 |
| 6 | sim-cleo-longshot | longshot_hold | 9811.9800 | 0.0000 | -188.0200 | 33.0200 | 11 |
| 7 | sim-hiro-slice | diversified_slice | 9738.8800 | 0.0000 | -261.1200 | 36.1200 | 10 |
| 8 | sim-ines-volume | volume_momentum | 9511.9900 | -425.2800 | -62.7300 | 127.2900 | 59 |
| 9 | sim-elena-revert | mean_revert | 9292.1700 | -695.4600 | -12.3700 | 125.3900 | 42 |
| 10 | sim-farid-fade | contrarian | 8217.8000 | -1662.9800 | -119.2200 | 335.7500 | 168 |
| 11 | sim-dmitri-momentum | momentum | 7981.4800 | -1943.5000 | -75.0200 | 318.2000 | 168 |

## Settled Nobel markets, historical backtest

Id: `nobel-settled-primary`. Kind: historical_backtest. Markets used: 219.

| Rank | Participant | Strategy | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-ada-hold | hold_cash | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 2 | sim-jonas-exit | favorite_exit | 9996.5500 | -3.4500 | 0.0000 | 6.1500 | 3 |
| 3 | sim-basil-favorite | favorite_hold | 9939.0100 | -60.9900 | 0.0000 | 3.8400 | 2 |
| 4 | sim-kira-null | seeded_null | 7524.8950 | -2475.1050 | 0.0000 | 226.4700 | 121 |
| 5 | sim-elena-revert | mean_revert | 5503.4900 | -4496.5100 | 0.0000 | 815.6700 | 257 |
| 6 | sim-gina-tight | tight_value | 4430.4100 | -5569.5900 | 0.0000 | 412.8100 | 173 |
| 7 | sim-ines-volume | volume_momentum | 4216.0180 | -5783.9820 | 0.0000 | 1822.1900 | 997 |
| 8 | sim-dmitri-momentum | momentum | 3255.0100 | -6744.9900 | 0.0000 | 2001.5900 | 935 |
| 9 | sim-hiro-slice | diversified_slice | 2500.0600 | -7499.9400 | 0.0000 | 563.7600 | 152 |
| 10 | sim-cleo-longshot | longshot_hold | 2500.0200 | -7499.9800 | 0.0000 | 588.7800 | 191 |
| 11 | sim-farid-fade | contrarian | 1548.0000 | -8452.0000 | 0.0000 | 2261.3400 | 1035 |

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

2000 simulated participants in 20 batches. 893979 ledger rows. Replay of batch-001, batch-011, batch-013, batch-018: matched. Same decision clock, size rules, and fee reading as the primary competitions above. Full board: `data/sim/program/leaderboard.json` (top 10 per universe below).

### Program, Nobel markets, forward simulation

| Rank | Participant | Strategy | Family | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-b017-093 | placebo-kelly-fraction-b017-093 | placebo_kelly_fraction | 10068.1000 | 0.0000 | 68.1000 | 14.7100 | 10 |
| 2 | sim-b011-099 | placebo-event-field-no-b011-099 | placebo_event_field_no | 10033.0600 | 0.0000 | 33.0600 | 10.8200 | 10 |
| 3 | sim-b017-090 | placebo-kelly-fraction-b017-090 | placebo_kelly_fraction | 10030.4400 | 0.0000 | 30.4400 | 13.5700 | 10 |
| 4 | sim-b011-002 | event-normalized-b011-002 | event_normalized | 10027.1600 | 0.0000 | 27.1600 | 6.5400 | 2 |
| 5 | sim-b011-004 | event-normalized-b011-004 | event_normalized | 10021.1200 | 0.0000 | 21.1200 | 2.5800 | 1 |
| 5 | sim-b011-091 | placebo-event-leader-b011-091 | placebo_event_leader | 10021.1200 | 0.0000 | 21.1200 | 2.5800 | 1 |
| 5 | sim-b011-092 | placebo-event-leader-b011-092 | placebo_event_leader | 10021.1200 | 0.0000 | 21.1200 | 2.5800 | 1 |
| 5 | sim-b011-093 | placebo-event-leader-b011-093 | placebo_event_leader | 10021.1200 | 0.0000 | 21.1200 | 2.5800 | 1 |
| 5 | sim-b011-094 | placebo-event-leader-b011-094 | placebo_event_leader | 10021.1200 | 0.0000 | 21.1200 | 2.5800 | 1 |
| 5 | sim-b011-095 | placebo-event-leader-b011-095 | placebo_event_leader | 10021.1200 | 0.0000 | 21.1200 | 2.5800 | 1 |

### Program, settled Nobel markets, historical backtest

| Rank | Participant | Strategy | Family | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-b013-085 | uniform-field-prior-b013-085 | uniform_field_prior | 10935.4230 | 935.4230 | 0.0000 | 79.3800 | 67 |
| 2 | sim-b013-024 | learned-bucket-calibration-b013-024 | learned_bucket_calibration | 10901.0900 | 901.0900 | 0.0000 | 75.5700 | 69 |
| 3 | sim-b012-001 | logit-scale-b012-001 | logit_scale | 10850.2620 | 850.2620 | 0.0000 | 68.2900 | 100 |
| 4 | sim-b017-010 | kelly-fraction-b017-010 | kelly_fraction | 10821.5630 | 821.5630 | 0.0000 | 71.8000 | 100 |
| 5 | sim-b011-025 | event-overround-no-b011-025 | event_overround_no | 10818.4810 | 818.4810 | 0.0000 | 51.7500 | 100 |
| 6 | sim-b012-029 | logit-scale-b012-029 | logit_scale | 10817.8630 | 817.8630 | 0.0000 | 72.9900 | 98 |
| 7 | sim-b012-011 | logit-scale-b012-011 | logit_scale | 10816.3330 | 816.3330 | 0.0000 | 73.4300 | 100 |
| 7 | sim-b017-039 | edge-scaled-size-b017-039 | edge_scaled_size | 10816.3330 | 816.3330 | 0.0000 | 73.4300 | 100 |
| 9 | sim-b017-007 | kelly-fraction-b017-007 | kelly_fraction | 10813.9930 | 813.9930 | 0.0000 | 69.3700 | 100 |
| 10 | sim-b017-037 | edge-scaled-size-b017-037 | edge_scaled_size | 10810.3930 | 810.3930 | 0.0000 | 72.6900 | 100 |

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