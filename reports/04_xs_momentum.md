# Study 4 - Cross-sectional momentum / reversal, all USDT perps, weekly

_Generated 2026-10-28 22:23 UTC. In-sample < 2024-01-01 <= out-of-sample._

897 symbols ever listed, 2020-01-01 to 2026-10-27.

Eligible names per day: median 100, min 3, max 100.


## Weekly quintile long-short portfolios (gross 1x, dollar neutral)

| variant | sharpe | ann_ret | max_dd | t_nw | is_sharpe | oos_sharpe | oos_t_nw | oos_ann_ret |
|---|---|---|---|---|---|---|---|---|
| mom_ret_7d | 0.47 | 0.10 | -0.46 | 1.33 | 0.59 | 0.36 | 0.67 | 0.07 |
| rev_ret_7d | -0.79 | -0.25 | -0.90 | -2.23 | -0.92 | -0.68 | -1.26 | -0.26 |
| mom_ret_14d | 0.80 | 0.23 | -0.33 | 2.25 | 0.77 | 0.86 | 1.66 | 0.27 |
| rev_ret_14d | -1.10 | -0.32 | -0.95 | -3.06 | -1.10 | -1.10 | -2.12 | -0.36 |
| mom_ret_28d | 0.96 | 0.28 | -0.34 | 2.49 | 0.72 | 1.25 | 2.09 | 0.45 |
| rev_ret_28d | -1.11 | -0.32 | -0.94 | -2.86 | -0.83 | -1.43 | -2.40 | -0.42 |
| mom_ret_90d_skip7 | 0.29 | 0.04 | -0.48 | 0.76 | 0.46 | 0.14 | 0.23 | -0.01 |
| rev_ret_90d_skip7 | -0.42 | -0.15 | -0.70 | -1.07 | -0.47 | -0.38 | -0.65 | -0.17 |


## Primary: 28d momentum, weekly

Sharpe 0.96 (bootstrap 95% CI 0.29 to 1.67), NW t=2.49, **DSR over 8 trials = 0.306**. Ann. return 28.2%, vol 30.6%, max DD -33.8%, turnover 41x/yr, cost drag 2.85%/yr, funding P&L +10.05%/yr.

|  | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| return | 0.36 | 0.48 | -0.13 | 0.09 | 0.12 | 0.81 | 0.41 |
| sharpe | 1.25 | 1.31 | -0.37 | 0.51 | 0.54 | 1.76 | 1.29 |
| max_dd | -0.17 | -0.23 | -0.24 | -0.13 | -0.17 | -0.22 | -0.22 |

Long and short books separately (each 0.5x gross):

| variant | sharpe | ann_ret | max_dd | t_nw | is_sharpe | oos_sharpe | oos_t_nw | oos_ann_ret |
|---|---|---|---|---|---|---|---|---|
| long_book | 0.63 | 0.20 | -0.62 | 1.77 | 0.87 | 0.27 | 0.48 | 0.02 |
| short_book | 0.03 | -0.09 | -0.81 | 0.08 | -0.41 | 0.68 | 1.18 | 0.23 |


## Daily rebalance check for the 7-day signal (higher turnover)

| variant | sharpe | ann_ret | max_dd | t_nw | is_sharpe | oos_sharpe | oos_t_nw | oos_ann_ret |
|---|---|---|---|---|---|---|---|---|
| mom_7d_daily_cost0 | 0.93 | 0.29 | -0.34 | 2.50 | 0.94 | 0.94 | 1.53 | 0.33 |
| mom_7d_daily_cost7 | 0.51 | 0.12 | -0.61 | 1.37 | 0.49 | 0.54 | 0.89 | 0.15 |
| rev_7d_daily_cost0 | -0.89 | -0.30 | -0.93 | -2.39 | -0.85 | -0.94 | -1.53 | -0.35 |
| rev_7d_daily_cost7 | -1.31 | -0.39 | -0.97 | -3.53 | -1.30 | -1.33 | -2.18 | -0.44 |
