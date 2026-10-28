# Study 7 - Shipped strategy (carry core + cascade & rebound overlays), 5-minute backtest

_Generated 2026-10-28 22:03 UTC. In-sample < 2024-01-01 <= out-of-sample._

2021-12-01 to 2026-10-27, 516,096 5-minute bars, pairs [['BTCUSDT.spot', 'BTCUSDT'], ['ETHUSDT.spot', 'ETHUSDT'], ['SOLUSDT.spot', 'SOLUSDT']].


## Components and the combination (daily-aggregated returns on total equity; gross up to 2x when carry is on)

| variant | sharpe | ann_ret | max_dd | t_nw | is_sharpe | oos_sharpe | oos_t_nw | oos_ann_ret | gross_exposure | cost_drag_pa | funding_pnl_pa | price_pnl_pa |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| combo | 1.390 | 0.094 | -0.117 | 3.378 | 1.143 | 1.763 | 2.846 | 0.093 | 0.857 | 0.032 | 0.047 | 0.077 |
| carry_only | 6.098 | 0.039 | -0.007 | 6.884 | 4.392 | 7.649 | 5.836 | 0.045 | 0.858 | 0.007 | 0.045 | 0.000 |
| cascade_only | 0.723 | 0.045 | -0.117 | 1.860 | 0.830 | 0.653 | 1.158 | 0.029 | 0.007 | 0.020 | 0.002 | 0.064 |
| rebound_only | 0.589 | 0.008 | -0.014 | 1.291 | -0.740 | 1.002 | 1.674 | 0.017 | 0.000 | 0.006 | 0.000 | 0.014 |
| perp_only_overlays | 0.809 | 0.053 | -0.117 | 2.057 | 0.770 | 0.907 | 1.583 | 0.046 | 0.008 | 0.025 | 0.002 | 0.076 |


## Combo: statistics on daily returns

Sharpe 1.39 (bootstrap 95% CI 0.60 to 2.21), NW t=3.38, PSR=0.999; ann. return 9.4% on equity, vol 6.6%, max DD -11.7%, hit rate 74%, skew 3.28.

|  | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| return | 0.007 | -0.009 | 0.210 | 0.215 | 0.049 | 0.009 |
| sharpe | 7.341 | -0.037 | 3.407 | 3.460 | 0.796 | 0.591 |
| max_dd | -0.001 | -0.117 | -0.028 | -0.033 | -0.029 | -0.007 |
| carry_only_ret | 0.004 | 0.002 | 0.058 | 0.119 | 0.013 | -0.000 |
| cascade_only_ret | 0.002 | -0.011 | 0.155 | 0.038 | 0.036 | 0.009 |
| rebound_only_ret | 0.000 | 0.000 | -0.009 | 0.048 | 0.000 | 0.000 |


## Combo attribution by symbol (annualised P&L contribution on total equity)

|  | price_pnl_pa | funding_pnl_pa | carry_time_on | overlay_bars_share |
|---|---|---|---|---|
| BTCUSDT | 0.0106 | 0.0156 | 0.4912 | 0.0159 |
| ETHUSDT | -0.0031 | 0.0154 | 0.4576 | 0.0138 |
| SOLUSDT | 0.0692 | 0.0160 | 0.3380 | 0.0160 |


## Sensitivities (daily Sharpe / ann. return)

| variant | sharpe | ann_ret | max_dd | t_nw | is_sharpe | oos_sharpe | oos_t_nw | oos_ann_ret |
|---|---|---|---|---|---|---|---|---|
| costs_maker_2+1/1+1 | 1.73 | 0.12 | -0.11 | 4.10 | 1.51 | 2.08 | 3.25 | 0.11 |
| costs_pessimistic_15+5/10+5 | 0.87 | 0.06 | -0.13 | 2.19 | 0.59 | 1.26 | 2.13 | 0.06 |
| cascade_hold_1h | 1.39 | 0.08 | -0.14 | 2.78 | 0.56 | 2.43 | 3.77 | 0.11 |
| cascade_hold_12h | 1.32 | 0.12 | -0.16 | 3.20 | 0.64 | 2.30 | 3.65 | 0.15 |
| cascade_hold_24h | 0.93 | 0.11 | -0.27 | 2.49 | 0.30 | 2.10 | 3.61 | 0.16 |
| cascade_z-2.5_oi-2% | 0.85 | 0.07 | -0.13 | 2.11 | 0.67 | 1.16 | 1.84 | 0.07 |
| rebound_thr_10bps | 1.30 | 0.08 | -0.12 | 3.25 | 1.20 | 1.55 | 2.62 | 0.07 |
| carry_enter20_exit5 | 1.12 | 0.07 | -0.12 | 2.72 | 0.87 | 1.48 | 2.38 | 0.08 |
| carry_always_on(enter-1) | 1.54 | 0.10 | -0.11 | 3.70 | 1.19 | 2.14 | 3.51 | 0.10 |
| overlay_weight_full(1/n) | 1.10 | 0.15 | -0.22 | 2.75 | 0.96 | 1.34 | 2.26 | 0.14 |
| overlay_weight_quarter | 1.95 | 0.07 | -0.06 | 4.43 | 1.51 | 2.57 | 3.76 | 0.07 |
| oi_one_bar_stale | 1.39 | 0.09 | -0.11 | 3.21 | 1.06 | 2.01 | 2.93 | 0.09 |


## BTC only from 2020-09 (longest open-interest history)

| variant | sharpe | ann_ret | max_dd | t_nw | is_sharpe | oos_sharpe | oos_t_nw | oos_ann_ret |
|---|---|---|---|---|---|---|---|---|
| btc_combo | 1.60 | 0.13 | -0.13 | 3.42 | 1.75 | 1.50 | 2.66 | 0.08 |
| btc_carry | 4.70 | 0.08 | -0.02 | 7.00 | 4.76 | 8.00 | 6.71 | 0.05 |
| btc_cascade | 0.72 | 0.05 | -0.14 | 1.58 | 0.88 | 0.47 | 0.85 | 0.02 |
| btc_rebound | -0.04 | -0.00 | -0.09 | -0.13 | -0.21 | 0.55 | 1.39 | 0.01 |

|  | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| return | 0.066 | 0.625 | -0.096 | 0.113 | 0.094 | 0.085 | 0.042 |
| sharpe | 1.888 | 3.466 | -1.587 | 1.809 | 1.621 | 1.617 | 1.186 |
| max_dd | -0.027 | -0.047 | -0.124 | -0.038 | -0.061 | -0.022 | -0.004 |
