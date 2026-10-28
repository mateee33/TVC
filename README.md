# TVC — a research-driven crypto trading bot

TVC is a complete pipeline: free historical data, a cost-aware backtester with
multiple-testing-aware statistics, seven research studies that hunt for an edge
with pre-registered hypotheses, and a bot that runs the surviving strategy in paper
or live mode on any ccxt exchange. The same strategy code runs in the backtests and
in the bot, so there is no backtest/live drift.

## The edge, in one paragraph

Six candidate edges were tested on 2020–2026 Binance data (survivorship-bias free,
realistic fees, in-sample before 2024 / out-of-sample 2024–2026). Three survived and
are combined in `EdgeCombo` (`tvc/strategies/edge.py`):

| Component | Rule | Evidence (see `reports/`) |
|---|---|---|
| **Funding-filtered cash-and-carry** (core) | Long spot + short perp while trailing-7d annualised funding > 10%; exit when it drops below 0. | Sharpe 6.1, max drawdown 0.7%, 4–12%/yr on notional; out-of-sample Sharpe 7.6 (better than in-sample). Structural: longs pay for leverage. |
| **Liquidation-cascade reversal** (overlay) | When the 1h return is ≤ −3σ *and* open interest fell ≥ 3% in that hour (forced deleveraging), buy the perp for 4h. Detected on 5-minute bars. | 405 events across BTC/ETH/SOL: +78 bps over 24h (t=2.9) vs +22 bps for equally sharp drops without deleveraging. Mostly BTC and SOL; ETH shows nothing. |
| **Post-settlement rebound** (overlay) | For the hour after a funding settlement whose 8h-equivalent rate exceeded 5 bps, hold the perp long. | 12,598 events across 47 perps: +21 bps/hour (t=10.9), positive in every active year; dormant when funding is calm (2025–26). The least robust piece; switch off with `rebound=False`. |

Backtested through the bot's own strategy code on 5-minute data for BTC, ETH and SOL
(Dec 2021 – Oct 2026, taker fees + slippage, funding paid/received):

| | Sharpe | Ann. return | Max DD | In-sample Sharpe | Out-of-sample Sharpe (t) |
|---|---|---|---|---|---|
| Combo (default sizing) | **1.39** (bootstrap 95% CI 0.60–2.21) | 9.4% | −11.7% | 1.14 | **1.76** (2.85) |
| Carry only | 6.10 | 3.9% | −0.7% | 4.39 | 7.65 |
| Cascade only | 0.72 | 4.5% | −11.7% | 0.83 | 0.65 |
| Rebound only | 0.59 | 0.8% | −1.4% | −0.74 | 1.00 |
| BTC only, Sep 2020 – Oct 2026 | 1.60 | 13.1% | −12.6% | 1.75 | 1.50 |

Returns are on total equity with the carry sized at 1/3 of equity per leg per pair
(gross up to 2x when all three carries are on) and overlays at half that. The
combo has positive skew (3.3) and 74% positive days, but the overlays buy crashes:
the worst day was the FTX collapse (8 Nov 2022). Full-size overlays raise the
return to 14.6%/yr at the cost of a 22.5% drawdown; quarter-size gives Sharpe 1.95
at 7%/yr. The daily-loss and drawdown kill switches in the bot exist for exactly
that tail.

## What did *not* survive (and is documented, not hidden)

| Study | Verdict |
|---|---|
| 01 Intraday / weekly seasonality | Not tradeable. The best in-sample hour window collapses out-of-sample (BTC Sharpe 0.37, ETH −0.24); deflated Sharpe ≈ 0.05–0.10 after 552 windows searched. |
| 02 Funding as a daily directional signal | No reversal effect; extreme funding of either sign precedes *positive* next-day returns. Cross-sectional funding-reversal portfolio loses after costs. |
| 03 Time-series momentum with vol targeting | Weakly positive (Sharpe 0.5–1.1 in-sample, 0.3–0.6 out-of-sample, t < 1) and no alpha over vol-scaled long-only beta (t = 1.6). |
| 04 Cross-sectional momentum / reversal (all 900 USDT perps, weekly) | See `reports/04_xs_momentum.md`. |
| 06 Cascade detected on hourly bars | Fades (out-of-sample Sharpe 0.35): most of the rebound happens in the first hour, so the bot runs on 5-minute bars. |

## Quickstart

```bash
pip install -e .                     # python >= 3.11; deps: numpy, pandas, scipy, pyarrow, requests, ccxt
tvc download --stages AE             # funding for all perps + 5m bars/open interest for BTC, ETH, SOL (~10 min)
tvc research --only 07               # re-run the shipped-strategy backtest -> reports/07_edge_combo.md
tvc research                         # all studies (needs stages ABCDE, ~1 h of downloads)

# paper trading on OKX public data (no API keys), one cycle:
tvc run --strategy edge --exchange okx --timeframe 5m \
    --pair BTC/USDT,BTC/USDT:USDT --pair ETH/USDT,ETH/USDT:USDT --pair SOL/USDT,SOL/USDT:USDT --once
# continuous paper trading (one cycle per 5-minute bar, state in ./state/bot.json):
tvc run --strategy edge --exchange okx --timeframe 5m --pair BTC/USDT,BTC/USDT:USDT --pair ETH/USDT,ETH/USDT:USDT --pair SOL/USDT,SOL/USDT:USDT
tvc status
```

Perp-only account (no spot leg, overlays only): `--pair ,BTC/USDT:USDT`.
Carry only: `--strategy carry`. Tune any parameter with `-p key=value`
(e.g. `-p carry_enter=0.2 -p cascade_hold_hours=12 -p rebound=false`).

### Live trading

```bash
export TVC_API_KEY=... TVC_API_SECRET=... [TVC_API_PASSWORD=...]   # or TVC_WALLET + TVC_API_SECRET for Hyperliquid
tvc run --strategy edge --exchange okx --timeframe 5m --pair BTC/USDT,BTC/USDT:USDT --live --sandbox   # testnet first
tvc run --strategy edge --exchange okx --timeframe 5m --pair BTC/USDT,BTC/USDT:USDT --live
```

Live mode has been exercised only through the exchange's unified ccxt interface
in this repository, not with a funded account: start on the testnet (`--sandbox`),
then with small size. Requirements for the carry leg: an account where spot and
USDT-margined perps share collateral (unified/portfolio margin on OKX, Bybit,
Binance), or enough free margin on the perp side to survive a rally against the
short. Risk limits (`--max-gross`, `--max-weight`, `--max-daily-loss 0.05`,
`--max-drawdown 0.25`) flatten and halt the bot when breached; the halt persists in
the state file until you clear it.

Behind a corporate proxy, set `HTTPS_PROXY` and `REQUESTS_CA_BUNDLE`; the broker
passes them to ccxt.

## How it works

```
tvc/data/binance_vision.py   free archive (data.binance.vision): spot & perp klines, funding, open interest,
                             premium index; every symbol ever listed; cached as parquet
tvc/backtest/engine.py       vectorised target-position backtester: fees + slippage per unit turnover,
                             funding settled to the position actually holding at the settlement, per-symbol costs
tvc/backtest/stats.py        Sharpe, Newey-West t, stationary bootstrap CI, probabilistic & deflated Sharpe
tvc/strategies/base.py       MarketData + Strategy: one `target_positions(md)` for research and live
tvc/strategies/edge.py       the shipped strategy (carry core + cascade & rebound overlays)
tvc/strategies/tsmom.py      trend following with vol targeting (research baseline, available in the bot)
tvc/live/datafeed.py         incremental 5m cache of bars, funding history and open interest per exchange
tvc/live/broker.py           PaperBroker (fees, slippage, funding accrual) and CcxtBroker (real orders)
tvc/live/bot.py              the loop: data -> strategy -> risk -> orders -> persisted state
research/0x_*.py             the studies; each writes reports/0x_*.md (+ CSVs)
```

Timing conventions (shared by engine and bot): bars are indexed by open time; a
position decided at the close of bar *t* earns bar *t+1*; a funding settlement at
time *T* is paid by the position in place during the bar ending at *T*, so a
position opened at the settlement does not pay it. Open interest used at bar *t*
is the snapshot at that bar's close (one bar stale makes no difference: Sharpe
1.39 → 1.39).

## Methodology

* **Pre-registration.** Each study states its hypotheses and primary spec before
  the data is looked at; variants are reported, not cherry-picked. When a parameter
  was searched (552 seasonality windows, 10 trend variants, 8 cross-sectional
  variants) the Deflated Sharpe Ratio of Bailey & López de Prado is reported.
* **Costs.** Perps 5 bps fee + 2 bps slippage per side (Binance/OKX taker tier),
  spot 10 + 2 bps. Maker and pessimistic (2x) variants are in the reports.
* **Funding** is paid or received on every perp position at each settlement.
* **Survivorship.** The cross-sectional study uses every USDT perp that ever listed,
  including delisted ones.
* **Out-of-sample** is everything from 2024-01-01; the combination was fixed from
  the in-sample evidence and its out-of-sample Sharpe (1.76) exceeds in-sample (1.14).

## Honest limitations

* 2021-12 to 2026-10 is five years and one full cycle; 405 cascade events is a
  modest sample and the SOL leg contributes most of the overlay return.
* The carry's Sharpe reflects basis risk only. Exchange/counterparty risk (FTX),
  liquidation on the short leg in a violent rally, and delisting basis gaps are not
  in the data. Size for those.
* The rebound overlay has had almost no events since 2025; its in-sample stretch on
  these three symbols was negative. It is included because the 47-symbol evidence
  is strong, and it is a one-flag switch.
* Paper mode uses last price ± slippage; real fills, partial fills and exchange
  downtime are not simulated.
* Nothing here is investment advice. Past funding regimes and liquidation
  behaviour can change, and have.
