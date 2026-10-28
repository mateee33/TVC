# Study 5 - Liquidation cascades (price + open-interest) and reversal

_Generated 2026-10-28 21:35 UTC. In-sample < 2024-01-01 <= out-of-sample._

BTCUSDT: 646,790 5-minute bars with OI, 2020-09-01 to 2026-10-27.

ETHUSDT: 515,956 5-minute bars with OI, 2021-12-01 to 2026-10-27.

SOLUSDT: 514,499 5-minute bars with OI, 2021-12-01 to 2026-10-27.


## Sharp 1h drops (z <= -3): with deleveraging vs without

| group | symbol | n | fwd_1h_bps | t_1h | fwd_4h_bps | t_4h | fwd_12h_bps | t_12h | fwd_24h_bps | t_24h |
|---|---|---|---|---|---|---|---|---|---|---|
| drop & OI<=-3% (cascade) | BTCUSDT | 178 | 29.3 | 2.3 | 43.1 | 2.3 | 44.6 | 1.9 | 84.9 | 2.6 |
| drop & OI<=-3% (cascade) | ETHUSDT | 108 | 1.4 | 0.1 | -5.2 | -0.3 | -3.2 | -0.1 | -9.8 | -0.2 |
| drop & OI<=-3% (cascade) | SOLUSDT | 119 | 51.8 | 1.4 | 54.9 | 1.3 | 109.6 | 2.3 | 148.9 | 2.6 |
| drop & OI<=-3% (cascade) | ALL | 405 | 28.5 | 2.1 | 33.7 | 2.1 | 51.0 | 2.5 | 78.4 | 2.9 |
| drop & OI>-1% (no deleveraging) | BTCUSDT | 526 | 7.1 | 1.3 | 10.0 | 1.4 | 0.2 | 0.0 | 12.8 | 1.0 |
| drop & OI>-1% (no deleveraging) | ETHUSDT | 405 | -8.3 | -1.1 | -8.8 | -0.8 | -4.5 | -0.3 | 5.0 | 0.2 |
| drop & OI>-1% (no deleveraging) | SOLUSDT | 379 | 8.2 | 0.9 | 35.3 | 2.1 | 51.8 | 2.0 | 54.5 | 1.6 |
| drop & OI>-1% (no deleveraging) | ALL | 1310 | 2.7 | 0.7 | 11.5 | 1.7 | 13.7 | 1.4 | 22.5 | 1.7 |
| drop, any OI | BTCUSDT | 624 | 3.3 | 0.7 | 9.3 | 1.4 | -2.2 | -0.2 | 8.8 | 0.7 |
| drop, any OI | ETHUSDT | 498 | -13.2 | -2.0 | -6.1 | -0.6 | -14.6 | -1.1 | -3.3 | -0.2 |
| drop, any OI | SOLUSDT | 466 | 8.1 | 0.9 | 31.3 | 2.1 | 48.9 | 2.2 | 45.0 | 1.6 |
| drop, any OI | ALL | 1588 | -0.5 | -0.1 | 10.9 | 1.8 | 8.9 | 1.0 | 15.6 | 1.4 |


## Sharp 1h rises (z >= 3): short squeeze (OI drop) vs fresh longs (OI rise)

| group | symbol | n | fwd_1h_bps | t_1h | fwd_4h_bps | t_4h | fwd_12h_bps | t_12h | fwd_24h_bps | t_24h |
|---|---|---|---|---|---|---|---|---|---|---|
| rise & OI<=-3% (squeeze) | BTCUSDT | 127 | 24.0 | 1.7 | 12.4 | 0.5 | 13.9 | 0.5 | 35.9 | 0.9 |
| rise & OI<=-3% (squeeze) | ETHUSDT | 62 | -4.7 | -0.2 | -59.9 | -1.4 | 9.9 | 0.2 | 48.5 | 0.9 |
| rise & OI<=-3% (squeeze) | SOLUSDT | 84 | 8.9 | 0.3 | 54.1 | 1.1 | 17.8 | 0.2 | 113.2 | 1.2 |
| rise & OI<=-3% (squeeze) | ALL | 273 | 12.8 | 1.0 | 8.8 | 0.4 | 14.2 | 0.5 | 62.6 | 1.8 |
| rise & OI>=+1% (new longs) | BTCUSDT | 290 | 15.6 | 2.4 | 14.7 | 1.3 | 30.4 | 1.9 | 51.9 | 2.3 |
| rise & OI>=+1% (new longs) | ETHUSDT | 237 | 3.1 | 0.4 | 5.0 | 0.3 | 10.6 | 0.5 | 19.8 | 0.7 |
| rise & OI>=+1% (new longs) | SOLUSDT | 254 | -4.3 | -0.3 | -6.8 | -0.3 | 27.4 | 0.9 | 35.8 | 0.8 |
| rise & OI>=+1% (new longs) | ALL | 781 | 5.3 | 1.0 | 4.8 | 0.5 | 23.4 | 1.8 | 36.9 | 1.9 |
| rise, any OI | BTCUSDT | 646 | 9.7 | 2.3 | 11.6 | 1.6 | 11.6 | 1.0 | 25.3 | 1.9 |
| rise, any OI | ETHUSDT | 513 | 5.9 | 1.0 | 11.0 | 1.2 | 6.3 | 0.4 | 18.1 | 0.9 |
| rise, any OI | SOLUSDT | 489 | 12.9 | 1.6 | 4.7 | 0.3 | 26.2 | 1.3 | 36.1 | 1.3 |
| rise, any OI | ALL | 1648 | 9.5 | 2.8 | 9.4 | 1.5 | 14.3 | 1.6 | 26.3 | 2.3 |


## Milder thresholds (z <= -2, OI <= -2%) and OI-only signal

| group | symbol | n | fwd_1h_bps | t_1h | fwd_4h_bps | t_4h | fwd_12h_bps | t_12h | fwd_24h_bps | t_24h |
|---|---|---|---|---|---|---|---|---|---|---|
| z<=-2 & OI<=-2% | BTCUSDT | 391 | 14.8 | 2.5 | 27.9 | 2.8 | 28.2 | 2.1 | 46.6 | 2.6 |
| z<=-2 & OI<=-2% | ETHUSDT | 303 | 1.1 | 0.1 | -14.5 | -1.3 | -20.7 | -1.3 | -4.6 | -0.2 |
| z<=-2 & OI<=-2% | SOLUSDT | 315 | 5.3 | 0.5 | 24.5 | 1.6 | 60.3 | 2.7 | 81.1 | 2.7 |
| z<=-2 & OI<=-2% | ALL | 1009 | 7.7 | 1.7 | 14.1 | 2.0 | 23.5 | 2.3 | 42.0 | 3.2 |
| z<=-2 & OI>-0.5% | BTCUSDT | 957 | 0.5 | 0.2 | 5.4 | 1.1 | 2.9 | 0.4 | 9.4 | 0.9 |
| z<=-2 & OI>-0.5% | ETHUSDT | 728 | -3.4 | -0.9 | -10.0 | -1.3 | -9.5 | -0.8 | 1.2 | 0.1 |
| z<=-2 & OI>-0.5% | SOLUSDT | 737 | -2.9 | -0.6 | -5.9 | -0.6 | 4.5 | 0.3 | 7.1 | 0.3 |
| z<=-2 & OI>-0.5% | ALL | 2422 | -1.7 | -0.7 | -2.7 | -0.6 | -0.4 | -0.1 | 6.2 | 0.7 |
| OI<=-5% in 1h, any price | BTCUSDT | 174 | 8.3 | 0.8 | 0.5 | 0.0 | -7.8 | -0.3 | 35.3 | 1.3 |
| OI<=-5% in 1h, any price | ETHUSDT | 86 | 7.0 | 0.5 | -27.7 | -0.9 | -7.4 | -0.1 | -3.0 | -0.0 |
| OI<=-5% in 1h, any price | SOLUSDT | 157 | 29.9 | 1.6 | 52.8 | 1.5 | 60.1 | 1.3 | 87.0 | 1.5 |
| OI<=-5% in 1h, any price | ALL | 417 | 16.1 | 1.8 | 14.4 | 0.9 | 17.8 | 0.8 | 46.9 | 1.7 |


## Strategy test: long for 12h after a cascade event (z<=-3 & OI<=-3%), 14 bps round trip

Hold 4h: 459 trades (75/yr), mean 38 bps net, hit 55%, total 173.4% per 1x notional; Sharpe (daily P&L, 1x per trade) full 0.85, IS 0.91, OOS 0.87, OOS t=1.49.

Hold 12h: 426 trades (69/yr), mean 37 bps net, hit 57%, total 158.2% per 1x notional; Sharpe (daily P&L, 1x per trade) full 0.64, IS 0.38, OOS 1.17, OOS t=1.95.

Hold 24h: 405 trades (66/yr), mean 64 bps net, hit 56%, total 260.9% per 1x notional; Sharpe (daily P&L, 1x per trade) full 0.74, IS 0.50, OOS 1.49, OOS t=2.48.
