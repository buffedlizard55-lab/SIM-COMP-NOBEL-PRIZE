# Simulated leaderboards

Every participant, trade, position, and P&L figure in this competition is simulated. None of it is a Kalshi order, a Kalshi user, or a real fill. Market prices, results, and volumes are Kalshi data only where a source URL is shown.

Kalshi snapshot: 2026-09-24T23:17:25Z

## Nobel markets, forward simulation

Id: `nobel-forward-primary`. Kind: forward_simulation. Markets used: 147.

| Rank | Participant | Strategy | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-ada-hold | hold_cash | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 1 | sim-basil-favorite | favorite_hold | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 1 | sim-jonas-exit | favorite_exit | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 4 | sim-gina-tight | tight_value | 8244.5940 | 0.0000 | -1755.4060 | 217.2100 | 71 |
| 5 | sim-kira-null | seeded_null | 8131.3050 | 0.0000 | -1868.6950 | 132.0600 | 67 |
| 6 | sim-cleo-longshot | longshot_hold | 7101.6000 | 0.0000 | -2898.4000 | 310.9000 | 94 |
| 7 | sim-elena-revert | mean_revert | 6456.5200 | -2431.2800 | -1112.2000 | 530.7100 | 166 |
| 8 | sim-hiro-slice | diversified_slice | 4520.5840 | 0.0000 | -5479.4160 | 458.1500 | 126 |
| 9 | sim-ines-volume | volume_momentum | 3495.2850 | -5458.8470 | -1045.8680 | 1451.5000 | 679 |
| 10 | sim-dmitri-momentum | momentum | 628.4140 | -9250.4870 | -121.0990 | 2063.9500 | 1397 |
| 11 | sim-farid-fade | contrarian | 411.4620 | -9282.4630 | -306.0750 | 2146.6200 | 1378 |

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

## The research program (2,000 simulated participants)

2000 simulated participants in 20 batches. 926317 ledger rows. Replay of batch-001, batch-011, batch-013, batch-018: matched. Same decision clock, size rules, and fee reading as the primary competitions above. Full board: `data/sim/program/leaderboard.json` (top 10 per universe below).

### Program, Nobel markets, forward simulation

| Rank | Participant | Strategy | Family | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-b013-079 | uniform-field-prior-b013-079 | uniform_field_prior | 10100.0000 | 0.0000 | 100.0000 | 6.9200 | 3 |
| 2 | sim-b011-091 | placebo-event-leader-b011-091 | placebo_event_leader | 10087.0500 | 0.0000 | 87.0500 | 9.3000 | 4 |
| 2 | sim-b011-095 | placebo-event-leader-b011-095 | placebo_event_leader | 10087.0500 | 0.0000 | 87.0500 | 9.3000 | 4 |
| 4 | sim-b013-082 | uniform-field-prior-b013-082 | uniform_field_prior | 10077.6800 | 0.0000 | 77.6800 | 4.7600 | 2 |
| 5 | sim-b013-046 | learned-base-rate-b013-046 | learned_base_rate | 10048.8300 | 0.0000 | 48.8300 | 6.0200 | 4 |
| 6 | sim-b017-064 | cash-reserve-gate-b017-064 | cash_reserve_gate | 10035.9000 | 0.0000 | 35.9000 | 8.2600 | 10 |
| 7 | sim-b013-032 | learned-base-rate-b013-032 | learned_base_rate | 10025.7200 | 0.0000 | 25.7200 | 9.1700 | 9 |
| 7 | sim-b013-034 | learned-base-rate-b013-034 | learned_base_rate | 10025.7200 | 0.0000 | 25.7200 | 9.1700 | 9 |
| 9 | sim-b013-013 | learned-bucket-calibration-b013-013 | learned_bucket_calibration | 10023.9770 | 0.0000 | 23.9770 | 17.5300 | 22 |
| 10 | sim-b015-054 | liquidity-gate-b015-054 | liquidity_gate | 10017.6800 | 0.0000 | 17.6800 | 6.9900 | 14 |

### Program, settled Nobel markets, historical backtest

| Rank | Participant | Strategy | Family | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-b013-087 | placebo-learned-bucket-calibration-b013-087 | placebo_learned_bucket_calibration | 10585.1700 | 585.1700 | 0.0000 | 24.7500 | 27 |
| 2 | sim-b001-044 | null-model-b001-044 | null_model | 10514.3900 | 514.3900 | 0.0000 | 70.8300 | 54 |
| 3 | sim-b019-008 | ablation-lagged-signal-b019-008 | ablation_lagged_signal | 10343.5700 | 343.5700 | 0.0000 | 52.5100 | 26 |
| 4 | sim-b016-084 | fade-the-rally-b016-084 | fade_the_rally | 10325.0000 | 325.0000 | 0.0000 | 15.8800 | 11 |
| 5 | sim-b016-081 | fade-the-rally-b016-081 | fade_the_rally | 10309.3300 | 309.3300 | 0.0000 | 15.2500 | 10 |
| 6 | sim-b016-069 | range-breakout-b016-069 | range_breakout | 10286.7400 | 286.7400 | 0.0000 | 57.4800 | 45 |
| 7 | sim-b015-032 | volume-spike-fade-b015-032 | volume_spike_fade | 10277.9200 | 277.9200 | 0.0000 | 38.2600 | 40 |
| 8 | sim-b013-024 | learned-bucket-calibration-b013-024 | learned_bucket_calibration | 10275.8600 | 275.8600 | 0.0000 | 24.2900 | 21 |
| 9 | sim-b016-083 | fade-the-rally-b016-083 | fade_the_rally | 10254.1400 | 254.1400 | 0.0000 | 18.9600 | 20 |
| 10 | sim-b013-085 | uniform-field-prior-b013-085 | uniform_field_prior | 10249.0700 | 249.0700 | 0.0000 | 29.1900 | 18 |

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