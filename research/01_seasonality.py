"""Study 1 - Intraday and weekly seasonality in BTC/ETH.

Pre-registered hypotheses (from the literature, before looking at the data):
  H1a  Returns are concentrated in US trading hours (roughly 13:00-21:00 UTC); Asian hours are flat/negative.
  H1b  Day-of-week: weekend returns differ from weekday returns.
  H1c  Price pressure around the 8-hourly perp funding settlement (00/08/16 UTC): the hour before a positive
       funding payment is negative (longs close to avoid paying), the hour after is positive.
  H1d  Tradeable test: holding spot only during the best in-sample window (selected 2018-2023) survives
       out-of-sample (2024-2026) after costs. We account for the 552 windows searched (deflated Sharpe).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sps

from tvc.backtest import stats
from tvc.backtest.stats import sharpe, nw_tstat
from tvc.research.common import Report, bv, is_oos_mask

SYMS = ["BTCUSDT", "ETHUSDT"]
START = "2018-01-01"
rep = Report("01_seasonality", "Study 1 - Intraday & weekly seasonality (BTC, ETH spot, hourly)")

hourly = {}
for s in SYMS:
    k = bv.klines(s, "1h", "spot")
    k = k[k.index >= START]
    hourly[s] = k["close"]
close = pd.DataFrame(hourly)
# log return accrued during the hour starting at the bar's open_time
r = np.log(close).diff().dropna()
rep.p(f"Sample: {r.index[0]:%Y-%m-%d} to {r.index[-1]:%Y-%m-%d}, {len(r):,} hourly bars per symbol.")

# ---------------------------------------------------------------- H1a hour-of-day
rep.h("H1a - Mean return by UTC hour (bps per hour)")
for s in SYMS:
    x = r[s]
    g = x.groupby(x.index.hour)
    tab = pd.DataFrame({"mean_bps": g.mean() * 1e4, "t_nw": g.apply(lambda v: nw_tstat(v.to_numpy()))})
    byyear = x.groupby([x.index.year, x.index.hour]).mean().unstack(0) * 1e4
    tab["years_positive"] = (byyear > 0).sum(axis=1).astype(int).astype(str) + "/" + str(byyear.shape[1])
    for y in byyear.columns:
        tab[str(y)] = byyear[y]
    tab.index.name = "hour_utc"
    rep.p(f"**{s}**")
    rep.table(tab, digits=1, csv=f"hour_{s}")

rep.h("H1a - Sessions (sum of hourly means, bps/day) by year")
sessions = {"asia_00_07": range(0, 7), "europe_07_13": range(7, 13), "us_13_21": range(13, 21), "late_21_24": range(21, 24)}
for s in SYMS:
    x = r[s]
    rows = {}
    for name, hrs in sessions.items():
        m = x[x.index.hour.isin(list(hrs))]
        daily = m.groupby(m.index.date).sum()
        row = {"all_mean_bps": daily.mean() * 1e4, "all_t_nw": nw_tstat(daily.to_numpy()),
               "all_sharpe": sharpe(daily.to_numpy(), 365)}
        for y, g in daily.groupby(pd.to_datetime(daily.index).year):
            row[str(y)] = g.mean() * 1e4
        rows[name] = row
    tab = pd.DataFrame(rows).T
    tab.index.name = "session"
    rep.p(f"**{s}** (mean bps per day earned inside the session; `all_sharpe` is of the daily session return, annualised)")
    rep.table(tab, digits=1, csv=f"sessions_{s}")

# ---------------------------------------------------------------- H1b day of week
rep.h("H1b - Day-of-week (daily log return, bps; 00:00 UTC close-to-close)")
daily_close = close.resample("1D").last()
dr = np.log(daily_close).diff().dropna()
rows = {}
for s in SYMS:
    g = dr[s].groupby(dr.index.dayofweek)
    rows[f"{s}_mean_bps"] = g.mean() * 1e4
    rows[f"{s}_t"] = g.apply(lambda v: nw_tstat(v.to_numpy()))
tab = pd.DataFrame(rows)
tab.index = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
tab.index.name = "weekday"
rep.table(tab, digits=1, csv="weekday")
for s in SYMS:
    wk = dr[s][dr.index.dayofweek < 5]
    we = dr[s][dr.index.dayofweek >= 5]
    t, p = sps.ttest_ind(wk, we, equal_var=False)
    rep.p(f"{s}: weekday mean {wk.mean()*1e4:.1f} bps vs weekend {we.mean()*1e4:.1f} bps, Welch t={t:.2f} (p={p:.3f})")

# ---------------------------------------------------------------- H1c funding hours
rep.h("H1c - Hour before / after funding settlement, conditioned on the sign of the funding paid (perp prices, 2020+)")
for s in SYMS:
    perp = bv.klines(s, "1h", "um")["close"]
    pr = np.log(perp).diff().dropna()
    fund = bv.funding(s)["funding_rate"]
    fund = fund[fund.index.hour.isin([0, 8, 16]) & (fund.index.minute == 0)]
    rows = []
    for label, offset in [("hour_before (T-1h..T)", -1), ("hour_after (T..T+1h)", 0), ("2h_before", -2), ("hour T+1..T+2", 1)]:
        # bar with open_time = T + offset hours
        idx = fund.index + pd.Timedelta(hours=offset)
        rr = pr.reindex(idx)
        df = pd.DataFrame({"r": rr.to_numpy(), "f": fund.to_numpy()}).dropna()
        for cond, mask in [("funding>0", df.f > 0), ("funding<=0", df.f <= 0), ("funding>5bps", df.f > 5e-4), ("all", df.f.notna())]:
            v = df.r[mask]
            rows.append({"window": label, "cond": cond, "n": len(v), "mean_bps": v.mean() * 1e4, "t_nw": nw_tstat(v.to_numpy())})
    tab = pd.DataFrame(rows).set_index(["window", "cond"])
    rep.p(f"**{s}**")
    rep.table(tab.reset_index().set_index("window"), digits=1)

# ---------------------------------------------------------------- H1d tradeable window test
rep.h("H1d - Tradeable: long spot only inside a fixed UTC window (IS-selected, OOS-evaluated)")
rep.p("Each day the strategy buys at the window open and sells at the window close (two trades/day). "
      "Costs are per side; 2 bps approximates spot maker fees, 7 bps approximates taker fee + slippage. "
      "552 windows (start 0-23h, length 1-23h) are searched in-sample; the Deflated Sharpe Ratio (DSR) is the "
      "probability the best in-sample Sharpe beats what the best of 552 skill-less windows would show.")
simple = close.pct_change().dropna()
for s in SYMS:
    x = simple[s]
    # day x hour matrix of simple returns (hour label = open hour)
    df = pd.DataFrame({"r": x, "d": x.index.floor("D"), "h": x.index.hour}).pivot_table(index="d", columns="h", values="r")
    df = df.dropna()
    M = np.hstack([df.to_numpy(), np.vstack([df.to_numpy()[1:], np.full((1, 24), np.nan)])])  # 48 cols for wrap
    days = df.index
    is_m, oos_m = is_oos_mask(days)
    results = []
    for h in range(24):
        for L in range(1, 24):
            daily = np.nansum(M[:, h:h + L], axis=1)
            daily[-1] = np.nan if h + L > 24 else daily[-1]
            results.append((h, L, daily))
    for cost_bps in (2.0, 7.0):
        c = 2 * cost_bps / 1e4
        rows = []
        sr_is_all = []
        for h, L, daily in results:
            d = daily - c
            d_is = d[is_m]; d_oos = d[oos_m]
            d_is = d_is[~np.isnan(d_is)]; d_oos = d_oos[~np.isnan(d_oos)]
            sr_is = sharpe(d_is, 365); sr_oos = sharpe(d_oos, 365)
            sr_is_all.append(d_is.mean() / d_is.std(ddof=1))
            rows.append({"start_utc": h, "length_h": L, "is_sharpe": sr_is, "is_ann_ret": d_is.mean() * 365,
                         "oos_sharpe": sr_oos, "oos_ann_ret": d_oos.mean() * 365, "oos_t_nw": nw_tstat(d_oos),
                         "_d": d})
        tab = pd.DataFrame(rows).sort_values("is_sharpe", ascending=False)
        var_tr = float(np.var(sr_is_all))
        best = tab.iloc[0]
        d_best = best["_d"]
        d_is = d_best[is_m]; d_is = d_is[~np.isnan(d_is)]
        dsr = stats.deflated_sharpe(d_is, n_trials=len(rows), var_sr_trials=var_tr)
        bh_is = sharpe(np.nansum(M[:, :24], axis=1)[is_m], 365); bh_oos = sharpe(np.nansum(M[:, :24], axis=1)[oos_m], 365)
        # pre-registered US window 13-21
        pre = tab[(tab.start_utc == 13) & (tab.length_h == 8)].iloc[0]
        rep.p(f"**{s}, cost {cost_bps:.0f} bps/side.** Buy&hold Sharpe IS {bh_is:.2f} / OOS {bh_oos:.2f}. "
              f"Best IS window {int(best.start_utc):02d}:00-{int(best.start_utc + best.length_h) % 24:02d}:00 UTC: "
              f"IS Sharpe {best.is_sharpe:.2f}, **OOS Sharpe {best.oos_sharpe:.2f}** (t={best.oos_t_nw:.2f}), DSR={dsr:.2f}. "
              f"Pre-registered 13-21 UTC: IS {pre.is_sharpe:.2f} / OOS {pre.oos_sharpe:.2f} (t={pre.oos_t_nw:.2f}).")
        show = tab.head(8).drop(columns="_d").set_index("start_utc")
        rep.table(show, digits=2)
        if cost_bps == 2.0:
            # year-by-year of the best IS window
            d = pd.Series(d_best, index=days).dropna()
            yt = stats.yearly_table(d, 365)[["return", "sharpe"]]
            yt["bh_return"] = stats.yearly_table(pd.Series(np.nansum(M[:, :24], axis=1), index=days), 365)["return"]
            rep.p(f"Year-by-year for the best IS window ({s}, 2 bps):")
            rep.table(yt.T, digits=2)

out = rep.write()
print(out.read_text())
