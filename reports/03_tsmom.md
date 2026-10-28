# Study 3 - Time-series momentum with vol targeting (major perps, daily)

_Generated 2026-10-28 21:21 UTC. In-sample < 2024-01-01 <= out-of-sample._

Universe: 47 perps, 2020-01-01 to 2026-10-27. Costs 5+2 bps/side, funding included.


## All variants (full sample, in-sample, out-of-sample)

| variant | sharpe | ann_ret | max_dd | t_nw | is_sharpe | oos_sharpe | oos_t_nw | oos_ann_ret |
|---|---|---|---|---|---|---|---|---|
| tsmom_20d_LS | 0.85 | 0.11 | -0.17 | 2.22 | 1.07 | 0.51 | 0.86 | 0.06 |
| tsmom_20d_LO | 1.15 | 0.12 | -0.14 | 2.74 | 1.49 | 0.62 | 0.89 | 0.06 |
| tsmom_60d_LS | 0.63 | 0.08 | -0.17 | 1.70 | 0.72 | 0.49 | 0.88 | 0.06 |
| tsmom_60d_LO | 0.95 | 0.10 | -0.14 | 2.39 | 1.17 | 0.60 | 0.94 | 0.05 |
| tsmom_90d_LS | 0.27 | 0.03 | -0.24 | 0.71 | 0.18 | 0.40 | 0.65 | 0.04 |
| tsmom_90d_LO | 0.87 | 0.08 | -0.16 | 2.18 | 1.09 | 0.54 | 0.80 | 0.05 |
| tsmom_180d_LS | 0.11 | 0.01 | -0.34 | 0.28 | 0.58 | -0.53 | -0.86 | -0.07 |
| tsmom_180d_LO | 0.67 | 0.06 | -0.20 | 1.68 | 1.14 | -0.07 | -0.11 | -0.01 |
| ensemble_LS | 0.53 | 0.05 | -0.16 | 1.39 | 0.69 | 0.29 | 0.51 | 0.03 |
| ensemble_LO | 0.89 | 0.08 | -0.14 | 2.17 | 1.17 | 0.44 | 0.65 | 0.03 |
| bench_volscaled_long_only | 0.68 | 0.11 | -0.26 | 1.73 | 0.94 | 0.29 | 0.47 | 0.04 |
| bench_btc_buy_hold | 0.90 | 0.43 | -0.77 | 2.39 | 1.00 | 0.72 | 1.26 | 0.26 |
| btc_only_ensemble_LS | 0.99 | 0.01 | -0.01 | 2.30 | 1.17 | 0.68 | 1.11 | 0.00 |


## Primary spec: ensemble long-short

Sharpe 0.53 (bootstrap 95% CI -0.23 to 1.28, P(Sharpe<=0)=0.091), NW t=1.39, PSR=0.916, **DSR over 10 trials = 0.549**. Ann. return 5.0%, vol 10.2%, max DD -16.5%. Avg gross exposure 0.15x, turnover 11x/yr, cost drag 0.77%/yr, funding P&L -1.51%/yr.

|  | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| return | 0.05 | 0.22 | 0.00 | 0.01 | 0.10 | -0.02 | -0.01 |
| sharpe | 0.65 | 1.94 | 0.08 | 0.11 | 0.92 | -0.12 | -0.01 |
| max_dd | -0.05 | -0.06 | -0.13 | -0.07 | -0.10 | -0.10 | -0.07 |
| beta_bench_return | 0.21 | 0.52 | -0.22 | 0.29 | 0.22 | -0.13 | 0.04 |
| btc_bh_return | 3.02 | 0.60 | -0.64 | 1.56 | 1.21 | -0.06 | -0.08 |

Regression on the vol-scaled long-only benchmark: beta -0.08, alpha 6.4%/yr (NW t=1.64). Long/short split of the primary spec:

| variant | sharpe | ann_ret | max_dd | t_nw | is_sharpe | oos_sharpe | oos_t_nw | oos_ann_ret |
|---|---|---|---|---|---|---|---|---|
| long_book | 0.97 | 0.07 | -0.09 | 2.36 | 1.21 | 0.57 | 0.82 | 0.03 |
| short_book | -0.18 | -0.02 | -0.21 | -0.50 | -0.28 | -0.05 | -0.10 | -0.01 |


## Sensitivity (primary spec)

| variant | sharpe | ann_ret | max_dd | t_nw | is_sharpe | oos_sharpe | oos_t_nw | oos_ann_ret |
|---|---|---|---|---|---|---|---|---|
| cost_0bps | 0.60 | 0.06 | -0.16 | 1.59 | 0.77 | 0.37 | 0.64 | 0.03 |
| cost_3bps | 0.57 | 0.05 | -0.16 | 1.51 | 0.74 | 0.34 | 0.58 | 0.03 |
| cost_7bps | 0.53 | 0.05 | -0.16 | 1.39 | 0.69 | 0.29 | 0.51 | 0.03 |
| cost_15bps | 0.44 | 0.04 | -0.17 | 1.16 | 0.61 | 0.20 | 0.35 | 0.02 |
| band_0.0 | 0.47 | 0.04 | -0.17 | 1.25 | 0.64 | 0.23 | 0.41 | 0.02 |
| band_0.5 | 0.48 | 0.04 | -0.16 | 1.28 | 0.66 | 0.21 | 0.37 | 0.02 |
| target_vol_0.1 | 0.53 | 0.03 | -0.09 | 1.39 | 0.69 | 0.29 | 0.51 | 0.01 |
| target_vol_0.4 | 0.53 | 0.09 | -0.31 | 1.39 | 0.70 | 0.29 | 0.50 | 0.04 |
