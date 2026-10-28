"""Study 2 - Perpetual funding: carry, directional information and the post-settlement rebound.

Pre-registered hypotheses:
  H2a  Cash-and-carry (long spot, short perp) earns the funding rate net of basis changes; a trailing-funding
       filter (enter when 7d avg annualised funding > 10%, exit < 0) improves on always-on carry after costs.
  H2b  Funding has directional information at the daily horizon: extreme positive funding -> lower next-day
       perp returns (crowded longs), extreme negative -> higher.
  H2c  (from Study 1) After an extreme positive funding payment, the perp rebounds in the following hour.
       Test across all majors on hourly perp data; thresholds 3/5/10 bps per 8h.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from tvc.backtest import Costs, align_funding, backtest_portfolio, stats
from tvc.backtest.stats import nw_tstat, sharpe
from tvc.config import OOS_START
from tvc.research.common import MAJORS, Report, bv, is_oos_mask, load_majors_daily, summarize_variants

PPY = 365
rep = Report("02_funding", "Study 2 - Funding carry, funding as a signal, post-settlement rebound")

perp, qv, funding = load_majors_daily()
spot = bv.load_many([c for c in perp.columns], "1d", "spot", "close")
common = [c for c in perp.columns if c in spot.columns and spot[c].notna().sum() > 365]
perp, spot, funding = perp[common], spot.reindex(columns=common), funding.reindex(columns=common)
rep.p(f"{len(common)} symbols with both spot and perp daily data, {perp.index[0]:%Y-%m-%d} to {perp.index[-1]:%Y-%m-%d}.")

# funding received per day by a short perp (sum of the 3 settlements that fall in the day)
fday = pd.DataFrame({c: align_funding(funding[c], perp.index) for c in common})
ann_f = fday.rolling(7).mean() * PPY  # trailing 7d annualised funding

# ---------------------------------------------------------------- H2a carry
rep.h("H2a - Cash-and-carry: long spot + short perp (per 1x notional, both legs)")
sp_r = spot.pct_change(fill_method=None)
pp_r = perp.pct_change(fill_method=None)
carry_r = (sp_r - pp_r + fday)  # daily return of the hedged pair before costs
desc = pd.DataFrame({
    "avg_funding_ann": fday.mean() * PPY, "share_days_funding>0": (fday > 0).mean(),
    "carry_sharpe_always_on": carry_r.apply(lambda v: sharpe(v.dropna(), PPY)),
    "carry_ann_ret_always_on": carry_r.mean() * PPY,
    "basis_pnl_ann": (sp_r - pp_r).mean() * PPY,
}).sort_values("avg_funding_ann", ascending=False)
rep.p("Per-symbol always-on carry (no costs). `basis_pnl_ann` is the spot-minus-perp price drift (basis convergence/divergence).")
rep.table(desc, digits=3, csv="carry_by_symbol")

# Filtered carry: in when trailing 7d annualised funding > enter, out when < exit. Costs: 4 legs per round trip.
def filtered_carry(enter: float, exit_: float, cost_pair_bps: float, symbols=None) -> pd.Series:
    symbols = symbols or common
    rows = []
    for c in symbols:
        a = ann_f[c]
        state = np.zeros(len(a))
        on = False
        av = a.to_numpy()
        for i in range(len(av)):
            if not np.isnan(av[i]):
                if not on and av[i] > enter:
                    on = True
                elif on and av[i] < exit_:
                    on = False
            state[i] = 1.0 if on else 0.0
        pos = pd.Series(state, index=a.index).shift(1).fillna(0.0)  # decided at close, held next day
        r = pos * carry_r[c].fillna(0.0) - pos.diff().abs().fillna(0.0) * cost_pair_bps / 1e4
        rows.append(r)
    R = pd.concat(rows, axis=1)
    n_on = (R != 0).sum(axis=1).replace(0, np.nan)
    return R.sum(axis=1) / n_on.fillna(1)  # equal weight across symbols currently on


variants = {}
for cost in (10.0, 25.0):
    variants[f"always_on_eqw_cost{cost:.0f}"] = (carry_r.fillna(0.0).sum(axis=1) / carry_r.notna().sum(axis=1).replace(0, np.nan)).fillna(0.0)
    for enter, exit_ in ((0.10, 0.0), (0.20, 0.05), (0.30, 0.10)):
        variants[f"filter_{int(enter*100)}_{int(exit_*100)}_cost{cost:.0f}"] = filtered_carry(enter, exit_, cost)
tab = summarize_variants(variants, PPY, OOS_START)
rep.p("Equal-weight across symbols currently in the trade. `cost` = bps per leg-pair per side (spot+perp), i.e. a "
      "round trip costs 2x. 10 bps ~ maker on both legs; 25 bps ~ taker + slippage. Returns are on 1x notional "
      "(ignoring margin: with 2x capital for spot + margin, divide by ~1.3).")
rep.table(tab, digits=2, csv="carry_variants")
best = variants["filter_10_0_cost10"]
yt = stats.yearly_table(best, PPY)[["return", "sharpe", "max_dd"]]
rep.p("Year-by-year, filter 10%/0%, 10 bps:")
rep.table(yt.T, digits=2)
btc_eth = filtered_carry(0.10, 0.0, 10.0, ["BTCUSDT", "ETHUSDT"])
rep.p("BTC+ETH only, filter 10%/0%, 10 bps: " + ", ".join(f"{k}={v:.2f}" for k, v in
      summarize_variants({"x": btc_eth}, PPY, OOS_START).iloc[0].items()))

# ---------------------------------------------------------------- H2b funding as a directional signal (daily)
rep.h("H2b - Funding as a next-day directional signal (perp close-to-close returns)")
nxt = pp_r.shift(-1)
rows = []
for c in ["BTCUSDT", "ETHUSDT"]:
    f = fday[c]; y = nxt[c]
    df = pd.DataFrame({"f": f, "y": y}).dropna()
    q = pd.qcut(df.f, 5, labels=False, duplicates="drop")
    g = df.groupby(q).y
    for k in sorted(g.groups):
        rows.append({"symbol": c, "funding_quintile": k, "avg_daily_funding_bps": df.f[q == k].mean() * 1e4,
                     "next_day_ret_bps": g.mean()[k] * 1e4, "t_nw": nw_tstat(df.y[q == k].to_numpy()), "n": int((q == k).sum())})
rep.table(pd.DataFrame(rows).set_index("symbol"), digits=1)
# panel: all majors pooled, by funding bucket in bps/day
df = pd.DataFrame({"f": fday.stack(), "y": nxt.stack()}).dropna()
bins = [-1, -0.001, 0.0, 0.0003, 0.001, 0.003, 1]
labels = ["<-10bps", "-10..0", "0..3", "3..10", "10..30", ">30bps"]
df["bucket"] = pd.cut(df.f, bins=bins, labels=labels)
g = df.groupby("bucket", observed=True).y
tab = pd.DataFrame({"n": g.size(), "next_day_ret_bps": g.mean() * 1e4, "t_nw": g.apply(lambda v: nw_tstat(v.to_numpy()))})
rep.p("All majors pooled, by daily funding bucket:")
rep.table(tab, digits=1, csv="funding_buckets")
# Cross-sectional: each day long the lowest-funding quintile, short the highest
fr = fday.where(pp_r.notna())
rank = fr.rank(axis=1, pct=True)
n_cs = fr.notna().sum(axis=1)
sig = pd.DataFrame(0.0, index=fr.index, columns=fr.columns)
sig[rank <= 0.2] = 1.0
sig[rank > 0.8] = -1.0
sig = sig.where(n_cs >= 10, 0.0)
sig = sig.div(sig.abs().sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)  # dollar neutral, gross 1
cs = backtest_portfolio(perp, sig, Costs(5, 2), funding)
cs0 = backtest_portfolio(perp, sig, Costs(0, 0), funding)
rep.p("Cross-sectional 'funding reversal' portfolio (long lowest-funding quintile / short highest, daily, gross 1x):")
rep.table(summarize_variants({"xs_funding_rev_cost7": cs.returns, "xs_funding_rev_cost0": cs0.returns,
                              "xs_funding_rev_cost0_price_only": cs0.gross}, PPY, OOS_START), digits=2)

# ---------------------------------------------------------------- H2c post-settlement rebound (hourly, all majors)
rep.h("H2c - Post-settlement rebound: long the perp for the hour after an extreme positive funding payment")
rows = []
events_all = {}
for c in MAJORS:
    try:
        k = bv.klines(c, "1h", "um")["close"]
        f = bv.funding(c)["funding_rate"]
    except Exception as e:
        continue
    if len(k) < 24 * 200:
        continue
    f = f[(f.index.minute == 0)]
    r = k.pct_change()
    # r is indexed by bar open time: r[X] is the return over [X, X+1h)
    r_after = r.reindex(f.index)                             # hour after settlement: [T, T+1h)
    r_before = r.reindex(f.index - pd.Timedelta(hours=1))    # hour before settlement: [T-1h, T)
    ev = pd.DataFrame({"f": f.to_numpy(), "after": r_after.to_numpy(), "before": r_before.to_numpy()}, index=f.index).dropna()
    events_all[c] = ev
ev = pd.concat(events_all, names=["symbol", "time"])
rep.p(f"{len(events_all)} symbols, {len(ev):,} funding events. Returns in bps; `after` = hour following settlement.")
rows = []
for thr in (0.0003, 0.0005, 0.001, 0.002):
    for name, m in (("funding>thr", ev.f > thr), ("funding<-thr", ev.f < -thr)):
        sub = ev[m]
        rows.append({"threshold_bps": thr * 1e4, "cond": name, "n": len(sub), "events_per_day": len(sub) / ((ev.index.get_level_values(1).max() - ev.index.get_level_values(1).min()).days),
                     "before_bps": sub.before.mean() * 1e4, "after_bps": sub.after.mean() * 1e4, "after_t": nw_tstat(sub.after.to_numpy()),
                     "after_median_bps": sub.after.median() * 1e4, "after_hit": (sub.after > 0).mean()})
rep.table(pd.DataFrame(rows).set_index("threshold_bps"), digits=2, csv="rebound")
# by year, threshold 5 bps, and IS/OOS, with costs
sub = ev[ev.f > 0.0005].reset_index()
sub["year"] = sub.time.dt.year
rep.p("Threshold 5 bps, by year (after-hour mean bps, t-stat, n):")
yt = sub.groupby("year").after.agg(["mean", "count"])
yt["mean"] *= 1e4
yt["t"] = sub.groupby("year").after.apply(lambda v: nw_tstat(v.to_numpy()))
rep.table(yt.T, digits=1)
# strategy: equal $ per event, 1h hold, costs round trip
for rt_cost in (4.0, 14.0):
    daily = (sub.set_index("time").after - rt_cost / 1e4).groupby(pd.Grouper(freq="1D")).sum()
    cnt = sub.set_index("time").after.groupby(pd.Grouper(freq="1D")).count()
    daily = daily.reindex(pd.date_range(daily.index.min(), daily.index.max(), freq="1D", tz="UTC")).fillna(0.0)
    # scale: position per event = 1/ max(5, events that day) so the daily gross stays <= ~1x
    scaled = daily / cnt.reindex(daily.index).fillna(1).clip(lower=5)
    is_m, oos_m = is_oos_mask(scaled.index)
    rep.p(f"Round-trip cost {rt_cost:.0f} bps, 1/max(5,n) sizing per event: Sharpe full {sharpe(scaled, PPY):.2f}, "
          f"IS {sharpe(scaled[is_m], PPY):.2f}, OOS {sharpe(scaled[oos_m], PPY):.2f} (OOS t={nw_tstat(scaled[oos_m].to_numpy()):.2f}); "
          f"ann. return {scaled.mean() * PPY:.1%}; sum of raw after-hour return per event {sub.after.mean() * 1e4:.1f} bps.")
# which symbols drive it? top by n
bysym = sub.groupby("symbol").after.agg(["mean", "count"]).sort_values("count", ascending=False)
bysym["mean"] *= 1e4
rep.p("Per symbol (threshold 5 bps), top 15 by number of events:")
rep.table(bysym.head(15), digits=1)

print(rep.write().read_text())
