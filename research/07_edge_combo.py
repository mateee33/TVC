"""Study 7 - The shipped strategy, backtested through the exact code the bot runs (tvc.strategies.edge.EdgeCombo).

5-minute bars, BTC/ETH/SOL spot + USD-M perps, funding events and open interest aligned to what is known at
each bar close. Costs: spot 10+2 bps, perp 5+2 bps per side (taker); maker and pessimistic variants shown.
Overlay size defaults to half the carry leg (see EdgeCombo docstring).
Component attribution, IS/OOS, year-by-year, bootstrap, and the perp-only mode (no spot account).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from tvc.backtest import Costs, align_funding, backtest_portfolio, stats
from tvc.config import OOS_START, REPORTS_DIR
from tvc.research.common import Report, bv, summarize_variants
from tvc.strategies.base import MarketData
from tvc.strategies.edge import EdgeCombo

PPY = 365
SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
START = "2021-12-01"  # all three have open-interest data from here
rep = Report("07_edge_combo", "Study 7 - Shipped strategy (carry core + cascade & rebound overlays), 5-minute backtest")


def load(symbols, start, oi_lag_bars=0):
    closes, funding, oi = {}, {}, {}
    for s in symbols:
        perp = bv.klines(s, "5m", "um")["close"]
        spot = bv.klines(s, "5m", "spot")["close"]
        met = bv.metrics(s)["sum_open_interest"]
        idx = perp.index[perp.index >= start]
        closes[s] = perp.reindex(idx)
        closes[f"{s}.spot"] = spot.reindex(idx)
        # OI known at the bar close (= next bar's open time), optionally lagged one bar to be conservative
        snap_times = idx + pd.Timedelta(minutes=5 * (1 - oi_lag_bars))
        o = met[~met.index.duplicated()].reindex(snap_times, method="nearest", tolerance=pd.Timedelta(minutes=2))
        oi[s] = pd.Series(o.to_numpy(), index=idx).ffill(limit=12)
        f = bv.funding(s)["funding_rate"]
        funding[s] = f[f.index >= start]
    close = pd.DataFrame(closes)
    return MarketData(close=close, funding=pd.DataFrame(funding), open_interest=pd.DataFrame(oi)), pd.DataFrame(funding)


md, funding = load(SYMS, START)
pairs = [[f"{s}.spot", s] for s in SYMS]
COSTS = {**{f"{s}.spot": Costs(10, 2) for s in SYMS}, **{s: Costs(5, 2) for s in SYMS}}
rep.p(f"{md.close.index[0]:%Y-%m-%d} to {md.close.index[-1]:%Y-%m-%d}, {len(md.close):,} 5-minute bars, pairs {pairs}.")


def run(strategy, costs=COSTS, md_=md):
    pos = strategy.target_positions(md_)
    return backtest_portfolio(md_.close, pos, costs, funding.reindex(columns=[p for _, p in strategy.params["pairs"]]))


def daily(res):
    return res.returns.resample("1D").sum()


variants, results = {}, {}
specs = {
    "combo": EdgeCombo(pairs),
    "carry_only": EdgeCombo(pairs, cascade=False, rebound=False),
    "cascade_only": EdgeCombo(pairs, carry=False, rebound=False),
    "rebound_only": EdgeCombo(pairs, carry=False, cascade=False),
    "perp_only_overlays": EdgeCombo([[None, s] for s in SYMS]),
}
for name, strat in specs.items():
    res = run(strat)
    results[name] = res
    variants[name] = daily(res)
rep.h("Components and the combination (daily-aggregated returns on total equity; gross up to 2x when carry is on)")
tab = summarize_variants(variants, PPY, OOS_START)
extra = {}
for name, res in results.items():
    extra[name] = {"gross_exposure": float(res.positions.abs().sum(axis=1).mean()),
                   "cost_drag_pa": float(res.costs.mean() * 288 * 365), "funding_pnl_pa": float(res.funding.mean() * 288 * 365),
                   "price_pnl_pa": float(res.gross.mean() * 288 * 365)}
tab = tab.join(pd.DataFrame(extra).T)
rep.table(tab, digits=3, csv="components")

combo = results["combo"]
d = variants["combo"]
s = stats.summary(d, PPY, n_boot=500, name="combo")
rep.h("Combo: statistics on daily returns")
rep.p(f"Sharpe {s['sharpe']:.2f} (bootstrap 95% CI {s['boot_ci_low']:.2f} to {s['boot_ci_high']:.2f}), NW t={s['t_stat_nw']:.2f}, PSR={s['psr_0']:.3f}; "
      f"ann. return {s['ann_return']:.1%} on equity, vol {s['ann_vol']:.1%}, max DD {s['max_dd']:.1%}, hit rate {s['hit_rate']:.0%}, skew {s['skew']:.2f}.")
yt = stats.yearly_table(d, PPY)[["return", "sharpe", "max_dd"]]
for name in ("carry_only", "cascade_only", "rebound_only"):
    yt[f"{name}_ret"] = stats.yearly_table(variants[name], PPY)["return"]
rep.table(yt.T, digits=3, csv="combo_yearly")

# per-symbol attribution of the combo
rep.h("Combo attribution by symbol (annualised P&L contribution on total equity)")
rows = {}
pos = combo.positions
ret = md.close.pct_change(fill_method=None).fillna(0.0)
held = pos.shift(1).fillna(0.0)
for s_ in SYMS:
    cols = [s_, f"{s_}.spot"]
    price_pnl = (held[cols] * ret[cols]).sum(axis=1)
    fr = pd.DataFrame({s_: align_funding(funding[s_], md.close.index)})
    fund_pnl = -(held[[s_]] * fr).sum(axis=1)
    rows[s_] = {"price_pnl_pa": price_pnl.mean() * 288 * 365, "funding_pnl_pa": fund_pnl.mean() * 288 * 365,
                "carry_time_on": float((pos[f"{s_}.spot"] > 0).mean()),
                "overlay_bars_share": float(((pos[s_] + pos[f"{s_}.spot"]) > 1e-9).mean())}
rep.table(pd.DataFrame(rows).T, digits=4)

# sensitivities
rep.h("Sensitivities (daily Sharpe / ann. return)")
sens = {}
sens["costs_maker_2+1/1+1"] = daily(run(EdgeCombo(pairs), {**{f"{s_}.spot": Costs(2, 1) for s_ in SYMS}, **{s_: Costs(1, 1) for s_ in SYMS}}))
sens["costs_pessimistic_15+5/10+5"] = daily(run(EdgeCombo(pairs), {**{f"{s_}.spot": Costs(15, 5) for s_ in SYMS}, **{s_: Costs(10, 5) for s_ in SYMS}}))
for hold in (1, 12, 24):
    sens[f"cascade_hold_{hold}h"] = daily(run(EdgeCombo(pairs, cascade_hold_hours=hold)))
sens["cascade_z-2.5_oi-2%"] = daily(run(EdgeCombo(pairs, cascade_z=-2.5, cascade_oi=-0.02)))
sens["rebound_thr_10bps"] = daily(run(EdgeCombo(pairs, rebound_thr_8h=0.001)))
sens["carry_enter20_exit5"] = daily(run(EdgeCombo(pairs, carry_enter=0.20, carry_exit=0.05)))
sens["carry_always_on(enter-1)"] = daily(run(EdgeCombo(pairs, carry_enter=-1.0, carry_exit=-2.0)))
sens["overlay_weight_full(1/n)"] = daily(run(EdgeCombo(pairs, overlay_weight=1.0 / len(SYMS))))
sens["overlay_weight_quarter"] = daily(run(EdgeCombo(pairs, overlay_weight=0.25 / len(SYMS))))
md_lag, _ = load(SYMS, START, oi_lag_bars=1)
sens["oi_one_bar_stale"] = daily(run(EdgeCombo(pairs), md_=md_lag))
rep.table(summarize_variants(sens, PPY, OOS_START), digits=2, csv="sensitivities")

# BTC only from 2020-09 (longer OI history)
rep.h("BTC only from 2020-09 (longest open-interest history)")
md_btc, f_btc = load(["BTCUSDT"], "2020-09-01")
funding = f_btc
rb = {}
for name, kw in (("btc_combo", {}), ("btc_carry", {"cascade": False, "rebound": False}), ("btc_cascade", {"carry": False, "rebound": False}), ("btc_rebound", {"carry": False, "cascade": False})):
    res = run(EdgeCombo([["BTCUSDT.spot", "BTCUSDT"]], **kw), {"BTCUSDT.spot": Costs(10, 2), "BTCUSDT": Costs(5, 2)}, md_btc)
    rb[name] = daily(res)
rep.table(summarize_variants(rb, PPY, OOS_START), digits=2)
rep.table(stats.yearly_table(rb["btc_combo"], PPY)[["return", "sharpe", "max_dd"]].T, digits=3)
pd.DataFrame(variants).to_csv(REPORTS_DIR / "07_edge_combo_daily_returns.csv")  # combo + components, daily
print(rep.write().read_text())
