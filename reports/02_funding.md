# Study 2 - Funding carry, funding as a signal, post-settlement rebound

_Generated 2026-10-28 21:21 UTC. In-sample < 2024-01-01 <= out-of-sample._

45 symbols with both spot and perp daily data, 2020-01-01 to 2026-10-27.


## H2a - Cash-and-carry: long spot + short perp (per 1x notional, both legs)

Per-symbol always-on carry (no costs). `basis_pnl_ann` is the spot-minus-perp price drift (basis convergence/divergence).

|  | avg_funding_ann | share_days_funding>0 | carry_sharpe_always_on | carry_ann_ret_always_on | basis_pnl_ann |
|---|---|---|---|---|---|
| EOSUSDT | 0.155 | 0.907 | 6.184 | 0.167 | -0.002 |
| LTCUSDT | 0.146 | 0.851 | 7.578 | 0.144 | -0.002 |
| XRPUSDT | 0.144 | 0.794 | 2.763 | 0.140 | -0.004 |
| ETHUSDT | 0.137 | 0.873 | 7.695 | 0.134 | -0.003 |
| XLMUSDT | 0.136 | 0.732 | 5.030 | 0.134 | -0.004 |
| LINKUSDT | 0.135 | 0.838 | 5.959 | 0.134 | -0.001 |
| ADAUSDT | 0.132 | 0.792 | 6.030 | 0.131 | -0.003 |
| ALGOUSDT | 0.127 | 0.770 | 5.358 | 0.133 | -0.003 |
| MATICUSDT | 0.126 | 0.751 | 4.171 | 0.157 | -0.006 |
| UNIUSDT | 0.124 | 0.807 | 6.171 | 0.137 | -0.002 |
| AAVEUSDT | 0.124 | 0.753 | 5.156 | 0.138 | -0.003 |
| BTCUSDT | 0.116 | 0.872 | 8.686 | 0.115 | -0.001 |
| DOGEUSDT | 0.113 | 0.768 | 4.720 | 0.123 | 0.000 |
| ETCUSDT | 0.108 | 0.770 | 3.502 | 0.106 | -0.003 |
| ATOMUSDT | 0.094 | 0.615 | 3.454 | 0.092 | -0.003 |
| NEARUSDT | 0.091 | 0.695 | 4.163 | 0.099 | -0.003 |
| SANDUSDT | 0.077 | 0.628 | 3.003 | 0.088 | -0.003 |
| DOTUSDT | 0.070 | 0.578 | 3.198 | 0.075 | -0.002 |
| HBARUSDT | 0.063 | 0.628 | 2.999 | 0.077 | -0.000 |
| AVAXUSDT | 0.061 | 0.619 | 2.223 | 0.063 | -0.004 |
| GALAUSDT | 0.056 | 0.602 | 2.652 | 0.072 | -0.004 |
| FILUSDT | 0.055 | 0.724 | 0.033 | 0.005 | -0.057 |
| BCHUSDT | 0.052 | 0.617 | 1.608 | 0.048 | -0.003 |
| ORDIUSDT | 0.052 | 0.375 | 6.656 | 0.114 | -0.005 |
| ARBUSDT | 0.045 | 0.439 | 6.581 | 0.084 | -0.001 |
| OPUSDT | 0.044 | 0.498 | 3.612 | 0.066 | -0.002 |
| WIFUSDT | 0.043 | 0.301 | 1.660 | 0.057 | 0.000 |
| ICPUSDT | 0.031 | 0.478 | 0.247 | 0.049 | 0.011 |
| TRXUSDT | 0.031 | 0.616 | 1.143 | 0.028 | -0.003 |
| SUIUSDT | 0.027 | 0.369 | 4.167 | 0.050 | -0.003 |
| FETUSDT | 0.020 | 0.400 | 1.560 | 0.034 | -0.003 |
| TONUSDT | 0.019 | 0.230 | 1.103 | 0.023 | 0.002 |
| WLDUSDT | 0.018 | 0.326 | 2.067 | 0.036 | -0.002 |
| RENDERUSDT | 0.013 | 0.230 | 3.052 | 0.040 | -0.001 |
| TAOUSDT | 0.012 | 0.272 | 2.267 | 0.033 | -0.001 |
| SOLUSDT | 0.002 | 0.642 | -0.174 | -0.026 | -0.028 |
| BNBUSDT | -0.000 | 0.339 | -0.046 | -0.001 | -0.001 |
| JUPUSDT | -0.001 | 0.213 | -0.205 | -0.004 | -0.000 |
| POLUSDT | -0.004 | 0.165 | -1.013 | -0.015 | -0.001 |
| APTUSDT | -0.007 | 0.362 | -0.636 | -0.015 | -0.003 |
| TIAUSDT | -0.009 | 0.272 | -0.848 | -0.020 | -0.001 |
| INJUSDT | -0.012 | 0.363 | -0.782 | -0.021 | -0.001 |
| SEIUSDT | -0.022 | 0.219 | -2.110 | -0.048 | -0.002 |
| ENAUSDT | -0.048 | 0.194 | -4.356 | -0.130 | -0.003 |
| AXSUSDT | -0.248 | 0.335 | -3.462 | -0.285 | 0.001 |

Equal-weight across symbols currently in the trade. `cost` = bps per leg-pair per side (spot+perp), i.e. a round trip costs 2x. 10 bps ~ maker on both legs; 25 bps ~ taker + slippage. Returns are on 1x notional (ignoring margin: with 2x capital for spot + margin, divide by ~1.3).

| variant | sharpe | ann_ret | max_dd | t_nw | is_sharpe | oos_sharpe | oos_t_nw | oos_ann_ret |
|---|---|---|---|---|---|---|---|---|
| always_on_eqw_cost10 | 3.64 | 0.07 | -0.05 | 5.44 | 3.96 | 3.19 | 2.66 | 0.03 |
| filter_10_0_cost10 | 5.72 | 0.11 | -0.02 | 8.80 | 6.39 | 4.14 | 6.26 | 0.07 |
| filter_20_5_cost10 | 4.65 | 0.11 | -0.02 | 8.02 | 5.59 | 2.80 | 4.17 | 0.07 |
| filter_30_10_cost10 | 3.20 | 0.10 | -0.05 | 7.23 | 3.52 | 2.36 | 3.43 | 0.06 |
| always_on_eqw_cost25 | 3.64 | 0.07 | -0.05 | 5.44 | 3.96 | 3.19 | 2.66 | 0.03 |
| filter_10_0_cost25 | 4.81 | 0.09 | -0.03 | 7.38 | 5.54 | 3.06 | 4.46 | 0.05 |
| filter_20_5_cost25 | 4.20 | 0.10 | -0.02 | 7.34 | 5.12 | 2.38 | 3.63 | 0.06 |
| filter_30_10_cost25 | 2.86 | 0.09 | -0.05 | 6.55 | 3.21 | 1.90 | 2.87 | 0.04 |

Year-by-year, filter 10%/0%, 10 bps:

|  | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|
| return | 0.00 | 0.00 | 0.00 | 0.27 | 0.49 | 0.03 | 0.09 | 0.15 | 0.04 | 0.03 |
| sharpe |  |  |  | 10.22 | 12.55 | 2.16 | 10.70 | 13.40 | 5.70 | 1.13 |
| max_dd | 0.00 | 0.00 | 0.00 | -0.01 | -0.01 | -0.01 | -0.00 | -0.00 | -0.00 | -0.02 |

BTC+ETH only, filter 10%/0%, 10 bps: sharpe=6.67, ann_ret=0.09, max_dd=-0.02, t_nw=8.80, is_sharpe=6.62, oos_sharpe=9.70, oos_t_nw=7.77, oos_ann_ret=0.06


## H2b - Funding as a next-day directional signal (perp close-to-close returns)

| symbol | funding_quintile | avg_daily_funding_bps | next_day_ret_bps | t_nw | n |
|---|---|---|---|---|---|
| BTCUSDT | 0.0 | -0.9 | 37.8 | 2.8 | 499.0 |
| BTCUSDT | 1.0 | 1.1 | 7.2 | 0.7 | 498.0 |
| BTCUSDT | 2.0 | 2.2 | -12.1 | -1.0 | 498.0 |
| BTCUSDT | 3.0 | 3.0 | 19.6 | 1.3 | 565.0 |
| BTCUSDT | 4.0 | 11.7 | 21.6 | 1.2 | 431.0 |
| ETHUSDT | 0.0 | -1.0 | 29.6 | 1.7 | 499.0 |
| ETHUSDT | 1.0 | 1.2 | 3.6 | 0.3 | 498.0 |
| ETHUSDT | 2.0 | 2.7 | 8.9 | 0.7 | 990.0 |
| ETHUSDT | 3.0 | 3.1 | -168.3 |  | 6.0 |
| ETHUSDT | 4.0 | 13.3 | 54.6 | 2.5 | 498.0 |

All majors pooled, by daily funding bucket:

| bucket | n | next_day_ret_bps | t_nw |
|---|---|---|---|
| <-10bps | 2,633 | 61.3 | 2.7 |
| -10..0 | 20,260 | 10.7 | 1.3 |
| 0..3 | 27,818 | -2.7 | -0.4 |
| 3..10 | 26,314 | 20.8 | 2.4 |
| 10..30 | 4,550 | 53.3 | 2.5 |
| >30bps | 1,336 | 101.9 | 2.3 |

Cross-sectional 'funding reversal' portfolio (long lowest-funding quintile / short highest, daily, gross 1x):

| variant | sharpe | ann_ret | max_dd | t_nw | is_sharpe | oos_sharpe | oos_t_nw | oos_ann_ret |
|---|---|---|---|---|---|---|---|---|
| xs_funding_rev_cost7 | -0.18 | -0.16 | -0.93 | -0.43 | 0.19 | -0.97 | -1.52 | -0.31 |
| xs_funding_rev_cost0 | 0.37 | 0.07 | -0.86 | 0.89 | 0.65 | -0.21 | -0.33 | -0.12 |
| xs_funding_rev_cost0_price_only | -0.05 | -0.11 | -0.90 | -0.11 | 0.20 | -0.58 | -0.90 | -0.22 |


## H2c - Post-settlement rebound: long the perp for the hour after an extreme positive funding payment

47 symbols, 279,088 funding events. Returns in bps; `after` = hour following settlement.

| threshold_bps | cond | n | events_per_day | before_bps | after_bps | after_t | after_median_bps | after_hit |
|---|---|---|---|---|---|---|---|---|
| 2.9999999999999996 | funding>thr | 19379 | 7.86 | 4.80 | 15.04 | 9.97 | 8.76 | 0.53 |
| 2.9999999999999996 | funding<-thr | 10458 | 4.24 | 14.46 | -4.84 | -2.67 | -5.86 | 0.47 |
| 5.0 | funding>thr | 11628 | 4.72 | 2.67 | 22.34 | 11.04 | 14.00 | 0.54 |
| 5.0 | funding<-thr | 5059 | 2.05 | 24.59 | -6.48 | -2.13 | -9.03 | 0.46 |
| 10.0 | funding>thr | 4050 | 1.64 | -4.95 | 35.00 | 8.99 | 17.89 | 0.55 |
| 10.0 | funding<-thr | 1725 | 0.70 | 53.63 | -10.71 | -1.60 | -22.23 | 0.44 |
| 20.0 | funding>thr | 965 | 0.39 | -23.53 | 64.14 | 7.20 | 31.52 | 0.58 |
| 20.0 | funding<-thr | 571 | 0.23 | 80.54 | -10.77 | -0.65 | -37.25 | 0.41 |

Threshold 5 bps, by year (after-hour mean bps, t-stat, n):

|  | 2020 | 2021 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| mean | 13.6 | 21.2 | 0.9 | 38.4 | 54.8 | -0.5 |
| count | 2,324 | 6,625 | 402.0 | 2,266 | 2.0 | 9.0 |
| t | 4.4 | 8.0 | 0.1 | 7.1 |  |  |

Round-trip cost 4 bps, 1/max(5,n) sizing per event: Sharpe full 0.37, IS 0.41, OOS 0.34 (OOS t=0.46); ann. return 2.7%; sum of raw after-hour return per event 22.3 bps.

Round-trip cost 14 bps, 1/max(5,n) sizing per event: Sharpe full -0.56, IS -0.71, OOS -0.24 (OOS t=-0.34); ann. return -4.0%; sum of raw after-hour return per event 22.3 bps.

Per symbol (threshold 5 bps), top 15 by number of events:

| symbol | mean | count |
|---|---|---|
| XLMUSDT | 24.2 | 565.0 |
| XRPUSDT | 21.4 | 543.0 |
| ATOMUSDT | 23.1 | 517.0 |
| ADAUSDT | 18.0 | 493.0 |
| LTCUSDT | 20.2 | 463.0 |
| ETCUSDT | 20.9 | 450.0 |
| ETHUSDT | 22.1 | 448.0 |
| LINKUSDT | 15.0 | 445.0 |
| EOSUSDT | 31.2 | 436.0 |
| ALGOUSDT | 16.8 | 411.0 |
| BCHUSDT | 21.0 | 408.0 |
| DOGEUSDT | 29.4 | 380.0 |
| MATICUSDT | 43.8 | 368.0 |
| BNBUSDT | 23.3 | 360.0 |
| AAVEUSDT | 17.4 | 347.0 |
