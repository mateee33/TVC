"""Study 3 - Time-series momentum (trend following) with volatility targeting on major USD-M perps.

Pre-registered primary specification (chosen before seeing results):
  * universe: the fixed MAJORS list (large, liquid perps; includes delisted MATIC) with >= 1y of data
  * signal: ensemble of sign(trailing return) over 20/60/90/180 days, in [-1, 1]
  * sizing: 20% annualised vol target per asset from 30d realised vol, max 1.5x, equal budget per asset
  * daily rebalance at 00:00 UTC with a 25% relative no-trade band; costs 5 bps fee + 2 bps slippage
    per side; funding paid/received on the perp position
  * benchmarks: BTC buy & hold, and the same vol-scaled portfolio WITHOUT the trend filter (long-only beta)
Variants (10 trials in total) are shown to judge robustness, and the DSR accounts for them.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from tvc.backtest import Costs, backtest_portfolio, apply_no_trade_band, stats
from tvc.config import OOS_START, REPORTS_DIR
from tvc.research.common import Report, load_majors_daily, summarize_variants
from tvc.strategies.base import realized_vol, vol_target_scale

PPY = 365
TARGET_VOL, MAX_LEV, VOL_WIN, BAND = 0.20, 1.5, 30, 0.25
COSTS = Costs(5, 2)
LOOKBACKS = [20, 60, 90, 180]

rep = Report("03_tsmom", "Study 3 - Time-series momentum with vol targeting (major perps, daily)")
close, qv, funding = load_majors_daily()
rep.p(f"Universe: {len(close.columns)} perps, {close.index[0]:%Y-%m-%d} to {close.index[-1]:%Y-%m-%d}. "
      f"Costs {COSTS.fee_bps:.0f}+{COSTS.slippage_bps:.0f} bps/side, funding included.")
vol = realized_vol(close, VOL_WIN, PPY)
scale = vol_target_scale(vol, TARGET_VOL, MAX_LEV)


def positions(signal: pd.DataFrame, band: float = BAND) -> pd.DataFrame:
    valid = signal.notna() & (scale > 0)
    n_valid = valid.sum(axis=1).replace(0, np.nan)
    pos = (signal.fillna(0.0) * scale).div(n_valid, axis=0).where(valid, 0.0)
    return apply_no_trade_band(pos, band)


def tsmom_signal(lookbacks, long_only: bool) -> pd.DataFrame:
    sigs = []
    for N in lookbacks:
        m = close / close.shift(N) - 1
        sigs.append(np.sign(m) if not long_only else (m > 0).astype(float).where(m.notna()))
    return sum(sigs) / len(sigs)


results = {}
for N in LOOKBACKS:
    for lo in (False, True):
        name = f"tsmom_{N}d_{'LO' if lo else 'LS'}"
        results[name] = backtest_portfolio(close, positions(tsmom_signal([N], lo)), COSTS, funding).returns
for lo in (False, True):
    name = f"ensemble_{'LO' if lo else 'LS'}"
    results[name] = backtest_portfolio(close, positions(tsmom_signal(LOOKBACKS, lo)), COSTS, funding).returns
n_trials = len(results)
# benchmarks
ones = pd.DataFrame(1.0, index=close.index, columns=close.columns).where(close.notna())
bench_beta = backtest_portfolio(close, positions(ones), COSTS, funding)
results["bench_volscaled_long_only"] = bench_beta.returns
btc = close[["BTCUSDT"]]
results["bench_btc_buy_hold"] = backtest_portfolio(btc, pd.DataFrame(1.0, index=btc.index, columns=btc.columns), Costs(0, 0)).returns
btc_ens = backtest_portfolio(btc, positions(tsmom_signal(LOOKBACKS, False))[["BTCUSDT"]], COSTS, funding[["BTCUSDT"]])
results["btc_only_ensemble_LS"] = btc_ens.returns

rep.h("All variants (full sample, in-sample, out-of-sample)")
tab = summarize_variants(results, PPY, OOS_START)
rep.table(tab, digits=2, csv="variants")

primary = backtest_portfolio(close, positions(tsmom_signal(LOOKBACKS, False)), COSTS, funding)
r = primary.returns
s = primary.summary(PPY, n_boot=1000, name="ensemble_LS")
sr_trials = [stats.sharpe(v, 1) for k, v in results.items() if not k.startswith("bench") and not k.startswith("btc_only")]
dsr = stats.deflated_sharpe(r, n_trials=n_trials, var_sr_trials=float(np.var(sr_trials)))
rep.h("Primary spec: ensemble long-short")
rep.p(f"Sharpe {s['sharpe']:.2f} (bootstrap 95% CI {s['boot_ci_low']:.2f} to {s['boot_ci_high']:.2f}, "
      f"P(Sharpe<=0)={s['boot_p_value']:.3f}), NW t={s['t_stat_nw']:.2f}, PSR={s['psr_0']:.3f}, "
      f"**DSR over {n_trials} trials = {dsr:.3f}**. Ann. return {s['ann_return']:.1%}, vol {s['ann_vol']:.1%}, "
      f"max DD {s['max_dd']:.1%}. Avg gross exposure {s['avg_gross_exposure']:.2f}x, turnover {s['avg_turnover_per_year']:.0f}x/yr, "
      f"cost drag {primary.costs.mean() * PPY:.2%}/yr, funding P&L {primary.funding.mean() * PPY:+.2%}/yr.")
yt = stats.yearly_table(r, PPY)[["return", "sharpe", "max_dd"]]
yt["beta_bench_return"] = stats.yearly_table(bench_beta.returns, PPY)["return"]
yt["btc_bh_return"] = stats.yearly_table(results["bench_btc_buy_hold"], PPY)["return"]
rep.table(yt.T, digits=2, csv="primary_yearly")

# Does the trend filter add value beyond beta? Regress strategy on the beta benchmark.
x = bench_beta.returns.reindex(r.index).fillna(0.0)
beta = np.cov(r, x)[0, 1] / np.var(x)
alpha = (r - beta * x)
rep.p(f"Regression on the vol-scaled long-only benchmark: beta {beta:.2f}, alpha {alpha.mean() * PPY:.1%}/yr "
      f"(NW t={stats.nw_tstat(alpha):.2f}). Long/short split of the primary spec:")
pos = primary.positions
longs = backtest_portfolio(close, pos.clip(lower=0), COSTS, funding).returns
shorts = backtest_portfolio(close, pos.clip(upper=0), COSTS, funding).returns
rep.table(summarize_variants({"long_book": longs, "short_book": shorts}, PPY, OOS_START), digits=2)

# Sensitivity: cost level and band
rep.h("Sensitivity (primary spec)")
rows = {}
for c in (Costs(0, 0), Costs(2, 1), Costs(5, 2), Costs(10, 5)):
    rows[f"cost_{c.fee_bps + c.slippage_bps:.0f}bps"] = backtest_portfolio(close, positions(tsmom_signal(LOOKBACKS, False)), c, funding).returns
for b in (0.0, 0.5):
    rows[f"band_{b}"] = backtest_portfolio(close, positions(tsmom_signal(LOOKBACKS, False), b), COSTS, funding).returns
for tv in (0.10, 0.40):
    sc = vol_target_scale(vol, tv, MAX_LEV)
    sig = tsmom_signal(LOOKBACKS, False)
    valid = sig.notna() & (sc > 0)
    p = (sig.fillna(0.0) * sc).div(valid.sum(axis=1).replace(0, np.nan), axis=0).where(valid, 0.0)
    rows[f"target_vol_{tv}"] = backtest_portfolio(close, apply_no_trade_band(p, BAND), COSTS, funding).returns
rep.table(summarize_variants(rows, PPY, OOS_START), digits=2)

r.to_csv(REPORTS_DIR / "03_tsmom_primary_returns.csv")
print(rep.write().read_text())
