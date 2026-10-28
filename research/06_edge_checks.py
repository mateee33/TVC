"""Study 6 - Re-check the three candidate edges at the hourly resolution the live bot runs on.

  6a cascade reversal detected on 1h bars (not 5m): z(1h ret) <= -3 and 1h open-interest change <= -3%
  6b funding-filtered carry on hourly spot/perp data for BTC/ETH/SOL (time in market, turnover, P&L split)
  6c post-settlement rebound with funding normalised to an 8h-equivalent rate (4h-interval symbols)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from tvc.backtest import align_funding
from tvc.backtest.stats import nw_tstat, sharpe
from tvc.research.common import MAJORS, Report, bv, is_oos_mask

rep = Report("06_edge_checks", "Study 6 - Edge checks at hourly resolution (what the bot sees)")
SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

# ---------------------------------------------------------------- 6a
rep.h("6a - Cascade reversal detected on hourly bars")
rows = []
pnl_all = []
for s in SYMS:
    k = bv.klines(s, "1h", "um")["close"]
    oi = bv.metrics(s)["sum_open_interest"]
    oi_h = oi.resample("1h").last().reindex(k.index)  # OI at the hour close (bar open_time t -> OI at t+1h)
    # careful alignment: bar t covers [t, t+1h); use OI observed at t+1h (the bar close)
    oi_close = oi.reindex(k.index + pd.Timedelta(hours=1), method="ffill", tolerance=pd.Timedelta(minutes=10))
    oi_close.index = k.index
    df = pd.DataFrame({"close": k, "oi": oi_close}).dropna()
    r = df.close.pct_change()
    z = r / r.rolling(24 * 30, min_periods=24 * 5).std()
    doi = df.oi.pct_change()
    for h in (4, 12, 24):
        df[f"fwd_{h}"] = df.close.shift(-h) / df.close - 1
    df["z"], df["doi"] = z, doi
    for label, m in (("z<=-3 & dOI<=-3%", (z <= -3) & (doi <= -0.03)), ("z<=-3 & dOI>-1%", (z <= -3) & (doi > -0.01)),
                     ("z<=-2.5 & dOI<=-2%", (z <= -2.5) & (doi <= -0.02)), ("z<=-2.5 & dOI>-0.5%", (z <= -2.5) & (doi > -0.005))):
        sub = df[m].dropna(subset=["fwd_24"])
        # de-cluster: 24h
        keep, last = [], None
        for t in sub.index:
            ok = last is None or (t - last) > pd.Timedelta(hours=24)
            keep.append(ok)
            if ok: last = t
        sub = sub[np.array(keep, dtype=bool)] if len(sub) else sub
        row = {"symbol": s, "event": label, "n": len(sub), "span": f"{df.index[0]:%Y-%m}..{df.index[-1]:%Y-%m}"}
        for h in (4, 12, 24):
            row[f"fwd_{h}h_bps"] = sub[f"fwd_{h}"].mean() * 1e4
            row[f"t_{h}h"] = nw_tstat(sub[f"fwd_{h}"].to_numpy()) if len(sub) > 10 else np.nan
        rows.append(row)
        if label == "z<=-3 & dOI<=-3%":
            pnl_all.append(pd.Series(sub["fwd_24"].to_numpy() - 14e-4, index=sub.index).rename(s))
tab = pd.DataFrame(rows).set_index("symbol")
rep.table(tab, digits=1, csv="cascade_hourly")
pnl = pd.concat(pnl_all).sort_index()
daily = pnl.groupby(pd.Grouper(freq="1D")).sum().reindex(pd.date_range(pnl.index.min().floor("D"), pnl.index.max().floor("D"), freq="1D", tz="UTC")).fillna(0.0)
is_m, oos_m = is_oos_mask(daily.index)
rep.p(f"Pooled BTC+ETH+SOL, z<=-3 & dOI<=-3%, 24h hold, 14 bps round trip, 1x per trade: {len(pnl)} trades, mean {pnl.mean() * 1e4:.0f} bps, "
      f"hit {(pnl > 0).mean():.0%}, Sharpe full {sharpe(daily, 365):.2f} / IS {sharpe(daily[is_m], 365):.2f} / OOS {sharpe(daily[oos_m], 365):.2f} (OOS t={nw_tstat(daily[oos_m].to_numpy()):.2f}).")
by_year = pnl.groupby(pnl.index.year).agg(["mean", "count", "sum"])
by_year["mean"] *= 1e4
rep.table(by_year.T, digits=2)

# ---------------------------------------------------------------- 6b
rep.h("6b - Funding-filtered carry on hourly data (BTC, ETH, SOL)")
rows = []
for s in SYMS:
    perp = bv.klines(s, "1h", "um")["close"]
    spot = bv.klines(s, "1h", "spot")["close"].reindex(perp.index)
    f = bv.funding(s)
    fr = align_funding(f["funding_rate"], perp.index)          # funding received per hour bar by a 1x perp short
    ann7 = fr.rolling(24 * 7).sum() * 365 / 7                   # trailing 7d annualised
    on = np.zeros(len(ann7)); state = False
    a = ann7.to_numpy()
    for i in range(len(a)):
        if not np.isnan(a[i]):
            if not state and a[i] > 0.10: state = True
            elif state and a[i] < 0.0: state = False
        on[i] = state
    pos = pd.Series(on, index=perp.index).shift(1).fillna(0.0)
    pair = (spot.pct_change(fill_method=None) - perp.pct_change(fill_method=None)).fillna(0.0)
    gross = pos * (pair + fr)
    cost = pos.diff().abs().fillna(0.0) * 10 / 1e4
    net = gross - cost
    netd = net.resample("1D").sum()
    is_m, oos_m = is_oos_mask(netd.index)
    rows.append({"symbol": s, "time_in_market": pos.mean(), "round_trips_per_year": pos.diff().abs().sum() / 2 / (len(pos) / 8760),
                 "funding_ann_when_on": (pos * fr).sum() / max(pos.sum(), 1) * 8760, "basis_pnl_ann_when_on": (pos * pair).sum() / max(pos.sum(), 1) * 8760,
                 "net_ann_ret": net.mean() * 8760, "sharpe": sharpe(netd, 365), "is_sharpe": sharpe(netd[is_m], 365), "oos_sharpe": sharpe(netd[oos_m], 365),
                 "max_dd": float(((1 + netd).cumprod() / (1 + netd).cumprod().cummax() - 1).min()), "span": f"{perp.index[0]:%Y-%m}..{perp.index[-1]:%Y-%m}"})
rep.p("Enter when trailing-7d annualised funding > 10%, exit when < 0; 10 bps per side on the pair. Returns on 1x notional.")
rep.table(pd.DataFrame(rows).set_index("symbol"), digits=3, csv="carry_hourly")

# ---------------------------------------------------------------- 6c
rep.h("6c - Post-settlement rebound with 8h-normalised funding, by year (all majors)")
evs = []
for c in MAJORS:
    try:
        k = bv.klines(c, "1h", "um")["close"]; f = bv.funding(c)
    except Exception:
        continue
    if len(k) < 24 * 200:
        continue
    f = f[f.index.minute == 0]
    norm = f["funding_rate"] * 8.0 / f["interval_hours"].fillna(8.0)
    r = k.pct_change()
    ev = pd.DataFrame({"f8": norm.to_numpy(), "after": r.reindex(f.index).to_numpy(), "interval": f["interval_hours"].to_numpy()}, index=f.index).dropna()
    ev["symbol"] = c
    evs.append(ev)
ev = pd.concat(evs)
ev["year"] = ev.index.year
rows = []
for thr in (0.0003, 0.0005, 0.001):
    sub = ev[ev.f8 > thr]
    g = sub.groupby("year").after
    row = {"threshold_8h_bps": thr * 1e4}
    for y, v in g:
        row[f"{y}_bps"] = v.mean() * 1e4
        row[f"{y}_n"] = len(v)
    row["all_bps"] = sub.after.mean() * 1e4; row["all_t"] = nw_tstat(sub.after.to_numpy()); row["all_n"] = len(sub)
    rows.append(row)
rep.table(pd.DataFrame(rows).set_index("threshold_8h_bps"), digits=1, csv="rebound_by_year")
rep.p(f"Share of events with a 4h interval: {(ev.interval == 4).mean():.1%} overall, {(ev[ev.year >= 2025].interval == 4).mean():.1%} since 2025.")
# events with 4h interval: does the effect hold?
sub4 = ev[(ev.interval == 4) & (ev.f8 > 0.0005)]
sub8 = ev[(ev.interval == 8) & (ev.f8 > 0.0005) & (ev.year >= 2024)]
rep.p(f"4h-interval symbols, f8>5bps: n={len(sub4)}, after={sub4.after.mean() * 1e4:.1f} bps (t={nw_tstat(sub4.after.to_numpy()):.1f}); "
      f"8h-interval 2024+: n={len(sub8)}, after={sub8.after.mean() * 1e4:.1f} bps (t={nw_tstat(sub8.after.to_numpy()):.1f}).")
print(rep.write().read_text())
