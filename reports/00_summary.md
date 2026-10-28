# Research summary — where the edge is (and isn't)

Data: Binance public archive (spot since 2017, USD-M perps, funding and open interest since 2020), every symbol
ever listed. Costs: perps 5+2 bps/side, spot 10+2 bps/side unless stated. In-sample < 2024-01-01 <= out-of-sample.
Statistics: annualised Sharpe on daily returns, Newey-West t-statistics, stationary-bootstrap confidence intervals,
probabilistic/deflated Sharpe where parameters were searched.

| # | Study | Pre-registered hypothesis | Result | Verdict |
|---|---|---|---|---|
| 01 | Intraday & weekly seasonality (BTC/ETH spot, hourly, 2018-26) | Returns concentrate in US hours; weekend effect; pressure around funding settlements | Hour-of-day means are unstable across years; best IS window collapses OOS (BTC 0.37, ETH -0.24 Sharpe; DSR 0.05-0.10 after 552 windows); pre-registered 13-21 UTC window loses after costs. Only the post-settlement hour after extreme funding stands out (ETH +21 bps, t=3.9). | **No** (but it seeded the rebound overlay) |
| 02 | Funding carry / funding as signal / post-settlement rebound (45 majors) | Carry earns funding net of basis; funding predicts reversal; rebound after extreme funding | Filtered carry: Sharpe 5.7 (IS 6.4 / OOS 4.1), 11%/yr on notional, max DD 2%. Funding is not a reversal signal (U-shape; XS reversal portfolio loses). Rebound: +21 bps/hour over 12,598 events (t=10.9), positive every active year, rare since 2025. | **Yes** (carry), **No** (signal), **Yes with caveats** (rebound) |
| 03 | Time-series momentum + vol targeting (47 major perps, daily) | Trend following works in crypto | Sharpe 0.5-1.1 IS, 0.3-0.6 OOS, t < 1; long-only beats long-short because the short book loses; alpha over vol-scaled long beta 6%/yr but t=1.6. DSR 0.55. | **Weak / no** |
| 04 | Cross-sectional momentum & reversal (all ~900 USDT perps, weekly) | 1-4 week momentum (Liu-Tsyvinski-Wu); short-term reversal | See `04_xs_momentum.md` | see report |
| 05 | Liquidation cascades (BTC/ETH/SOL, 5-minute price + open interest) | Drops with deleveraging revert more than drops without | Cascade (z<=-3, OI<=-3%): +78 bps/24h pooled (t=2.9) vs +22 bps control (t=1.7); BTC +85 (t=2.6), SOL +149 (t=2.6), ETH nothing. 4h-hold strategy: 459 trades, +38 bps net, IS 0.91 / OOS 0.87 Sharpe. | **Yes** (BTC, SOL) |
| 06 | Hourly-resolution checks of 02/05 | Edges survive at the bot's cadence | Carry confirmed on hourly data (BTC 9.4%, ETH 11.9%, SOL 7.7%/yr net; OOS Sharpe 5.6-8.7). Cascade fades on hourly bars (OOS 0.35) -> 5-minute cadence required. Rebound: 4h-interval symbols +21 bps (t=3.0). | shaped the bot design |
| 07 | Shipped strategy through the bot's own code (5-minute, 2021-12 to 2026-10) | Combination is robust to costs, timing and sizing | Combo Sharpe 1.39 (CI 0.60-2.21), 9.4%/yr, max DD 11.7%, IS 1.14 / OOS 1.76 (t=2.85); carry-only 6.1; maker costs 1.73, pessimistic costs 0.87; OI one bar stale 1.39; BTC-only since 2020-09: 1.60, 13%/yr, 6 of 7 years positive. | **This is the bot** |

## The strategy in one paragraph

Hold a cash-and-carry (long spot, short perpetual, equal notional) in each of BTC, ETH and SOL whenever the trailing
7-day annualised funding is above 10%, and drop it when funding turns negative: this earns the funding stream with
2% drawdowns. On top of that, buy the perp for four hours after a liquidation cascade (hourly return below -3 sigma
with open interest down 3% or more), and for one hour after a settlement at which longs paid more than 5 bps. The
overlays are sized at half the carry leg, because they buy crashes and their worst day was the FTX collapse.

## What would make me stop trading it

* Funding regimes compress for good (carry rarely on; rebound never fires): the bot then sits flat, which is fine.
* Cascade reversals stop working: watch the running hit-rate of overlay trades; below ~45% over 50 trades, switch
  `cascade=False`.
* Exchange risk on the short leg: keep margin above 2x the 24h move you would not want to be liquidated in.
