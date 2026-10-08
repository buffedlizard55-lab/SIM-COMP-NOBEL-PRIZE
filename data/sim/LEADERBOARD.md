# Simulated leaderboards

Every participant, trade, position, and P&L figure in this competition is simulated. None of it is a Kalshi order, a Kalshi user, or a real fill. Market prices, results, and volumes are Kalshi data only where a source URL is shown.

Kalshi snapshot: 2026-10-08T19:15:51Z

## Nobel markets, forward simulation

Id: `nobel-forward-primary`. Kind: forward_simulation. Markets used: 51.

| Rank | Participant | Strategy | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-ada-hold | hold_cash | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 1 | sim-basil-favorite | favorite_hold | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 1 | sim-jonas-exit | favorite_exit | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 4 | sim-kira-null | seeded_null | 9270.6000 | 0.0000 | -729.4000 | 61.5500 | 32 |
| 5 | sim-gina-tight | tight_value | 9031.1600 | 0.0000 | -968.8400 | 97.4400 | 51 |
| 6 | sim-hiro-slice | diversified_slice | 8875.6000 | 0.0000 | -1124.4000 | 96.4400 | 26 |
| 7 | sim-elena-revert | mean_revert | 8662.5600 | -1305.7300 | -31.7100 | 234.2300 | 86 |
| 8 | sim-cleo-longshot | longshot_hold | 8409.5800 | 0.0000 | -1590.4200 | 133.9200 | 49 |
| 9 | sim-ines-volume | volume_momentum | 5447.6990 | -4339.1810 | -213.1200 | 1219.7700 | 595 |
| 10 | sim-dmitri-momentum | momentum | 584.8930 | -9326.7460 | -88.3610 | 2214.4800 | 1220 |
| 11 | sim-farid-fade | contrarian | 396.2080 | -9368.8820 | -234.9100 | 2301.4500 | 1243 |

## Settled Nobel markets, historical backtest

Id: `nobel-settled-primary`. Kind: historical_backtest. Markets used: 169.

| Rank | Participant | Strategy | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-ada-hold | hold_cash | 10000.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| 2 | sim-jonas-exit | favorite_exit | 9996.5500 | -3.4500 | 0.0000 | 6.1500 | 3 |
| 3 | sim-basil-favorite | favorite_hold | 9939.0100 | -60.9900 | 0.0000 | 3.8400 | 2 |
| 4 | sim-kira-null | seeded_null | 8190.7650 | -1809.2350 | 0.0000 | 181.2100 | 96 |
| 5 | sim-elena-revert | mean_revert | 6230.7000 | -3769.3000 | 0.0000 | 689.3900 | 193 |
| 6 | sim-gina-tight | tight_value | 5752.2100 | -4247.7900 | 0.0000 | 333.4100 | 123 |
| 7 | sim-ines-volume | volume_momentum | 4796.7100 | -5203.2900 | 0.0000 | 1541.1200 | 750 |
| 8 | sim-cleo-longshot | longshot_hold | 3709.9600 | -6290.0400 | 0.0000 | 515.0400 | 160 |
| 9 | sim-hiro-slice | diversified_slice | 3614.8900 | -6385.1100 | 0.0000 | 501.0900 | 135 |
| 10 | sim-dmitri-momentum | momentum | 3255.0100 | -6744.9900 | 0.0000 | 2001.5900 | 935 |
| 11 | sim-farid-fade | contrarian | 1548.0000 | -8452.0000 | 0.0000 | 2261.3600 | 1037 |

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

2000 simulated participants in 20 batches. 1026104 ledger rows. Replay of batch-001, batch-011, batch-013, batch-018: matched. Same decision clock, size rules, and fee reading as the primary competitions above. Full board: `data/sim/program/leaderboard.json` (top 10 per universe below).

### Program, Nobel markets, forward simulation

| Rank | Participant | Strategy | Family | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-b012-001 | logit-scale-b012-001 | logit_scale | 10114.5460 | 0.0000 | 114.5460 | 18.2800 | 35 |
| 2 | sim-b012-009 | logit-scale-b012-009 | logit_scale | 10114.1470 | 0.0000 | 114.1470 | 19.0400 | 44 |
| 3 | sim-b012-079 | fee-aware-logit-b012-079 | fee_aware_logit | 10112.0590 | 0.0000 | 112.0590 | 18.8400 | 43 |
| 4 | sim-b012-011 | logit-scale-b012-011 | logit_scale | 10106.5100 | 0.0000 | 106.5100 | 17.3400 | 29 |
| 4 | sim-b017-007 | kelly-fraction-b017-007 | kelly_fraction | 10106.5100 | 0.0000 | 106.5100 | 17.3400 | 29 |
| 4 | sim-b017-010 | kelly-fraction-b017-010 | kelly_fraction | 10106.5100 | 0.0000 | 106.5100 | 17.3400 | 29 |
| 4 | sim-b017-013 | kelly-fraction-b017-013 | kelly_fraction | 10106.5100 | 0.0000 | 106.5100 | 17.3400 | 29 |
| 4 | sim-b017-039 | edge-scaled-size-b017-039 | edge_scaled_size | 10106.5100 | 0.0000 | 106.5100 | 17.3400 | 29 |
| 4 | sim-b017-058 | cash-reserve-gate-b017-058 | cash_reserve_gate | 10106.5100 | 0.0000 | 106.5100 | 17.3400 | 29 |
| 4 | sim-b017-060 | cash-reserve-gate-b017-060 | cash_reserve_gate | 10106.5100 | 0.0000 | 106.5100 | 17.3400 | 29 |

### Program, settled Nobel markets, historical backtest

| Rank | Participant | Strategy | Family | Ending equity | Realized | Unrealized | Fees | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sim-b013-085 | uniform-field-prior-b013-085 | uniform_field_prior | 10779.5500 | 779.5500 | 0.0000 | 69.9400 | 55 |
| 2 | sim-b012-019 | logit-scale-b012-019 | logit_scale | 10759.1700 | 759.1700 | 0.0000 | 62.9500 | 100 |
| 3 | sim-b017-016 | kelly-fraction-b017-016 | kelly_fraction | 10754.1900 | 754.1900 | 0.0000 | 63.0900 | 104 |
| 4 | sim-b013-024 | learned-bucket-calibration-b013-024 | learned_bucket_calibration | 10744.1600 | 744.1600 | 0.0000 | 66.7600 | 62 |
| 5 | sim-b017-014 | kelly-fraction-b017-014 | kelly_fraction | 10737.0900 | 737.0900 | 0.0000 | 62.8900 | 104 |
| 6 | sim-b012-001 | logit-scale-b012-001 | logit_scale | 10721.6400 | 721.6400 | 0.0000 | 60.3100 | 80 |
| 7 | sim-b017-011 | kelly-fraction-b017-011 | kelly_fraction | 10718.3600 | 718.3600 | 0.0000 | 62.1400 | 104 |
| 8 | sim-b017-008 | kelly-fraction-b017-008 | kelly_fraction | 10705.4800 | 705.4800 | 0.0000 | 61.1000 | 104 |
| 9 | sim-b017-058 | cash-reserve-gate-b017-058 | cash_reserve_gate | 10694.2200 | 694.2200 | 0.0000 | 58.4900 | 75 |
| 10 | sim-b012-087 | fee-aware-logit-b012-087 | fee_aware_logit | 10690.5800 | 690.5800 | 0.0000 | 66.1200 | 99 |

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