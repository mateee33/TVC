"""Study 5 - Liquidation cascades and short-term reversal (BTC, ETH, SOL perps, 5-minute data).

Pre-registered hypothesis: a sharp 1-hour price drop accompanied by a sharp drop in open interest is driven by
forced liquidations (deleveraging), and such drops revert more over the next 1-24h than equally sharp drops
without deleveraging. Mirror case for squeezes (sharp rise + OI drop).
  * event: 1h return z-score <= -3 (vs trailing 30d distribution of 1h returns), OI 1h change <= -3%
  * control: same price z-score but OI 1h change > -1%
  * events are de-clustered: only the first event within any 24h window is kept
  * forward windows: 1h, 4h, 12h, 24h after the event bar; costs 14 bps round trip for the strategy test
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from tvc.backtest.stats import nw_tstat, sharpe
from tvc.research.common import Report, bv, is_oos_mask

SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
rep = Report("05_oi_cascade", "Study 5 - Liquidation cascades (price + open-interest) and reversal")

events_all = []
for s in SYMS:
    k = bv.klines(s, "5m", "um")
    m = bv.metrics(s)
    df = pd.DataFrame({"close": k["close"], "oi": m["sum_open_interest"].reindex(k.index)}).dropna()
    df = df[~df.index.duplicated()]
    r1h = df.close.pct_change(12)
    z = r1h / r1h.rolling(12 * 24 * 30, min_periods=12 * 24 * 5).std()
    doi = df.oi.pct_change(12)
    fwd = {h: df.close.shift(-12 * h) / df.close - 1 for h in (1, 4, 12, 24)}
    ev = pd.DataFrame({"z": z, "doi": doi, "r1h": r1h, **{f"fwd_{h}h": v for h, v in fwd.items()}})
    ev["symbol"] = s
    events_all.append(ev)
    rep.p(f"{s}: {len(df):,} 5-minute bars with OI, {df.index[0]:%Y-%m-%d} to {df.index[-1]:%Y-%m-%d}.")
ev = pd.concat(events_all)


def decluster(idx: pd.DatetimeIndex, hours=24) -> np.ndarray:
    keep, last = [], None
    for t in idx:
        if last is None or (t - last) > pd.Timedelta(hours=hours):
            keep.append(True); last = t
        else:
            keep.append(False)
    return np.array(keep, dtype=bool)


def event_table(mask_name: str, mask: pd.Series) -> pd.DataFrame:
    rows = []
    for s in SYMS + ["ALL"]:
        sub = ev[mask & ((ev.symbol == s) if s != "ALL" else True)].dropna(subset=["fwd_24h"])
        parts = []
        for sym, g in sub.groupby("symbol"):
            g = g.sort_index()
            parts.append(g[decluster(g.index)])
        sub = pd.concat(parts) if parts else sub.iloc[0:0]
        row = {"group": mask_name, "symbol": s, "n": len(sub)}
        for h in (1, 4, 12, 24):
            row[f"fwd_{h}h_bps"] = sub[f"fwd_{h}h"].mean() * 1e4
            row[f"t_{h}h"] = nw_tstat(sub[f"fwd_{h}h"].to_numpy()) if len(sub) > 10 else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


rep.h("Sharp 1h drops (z <= -3): with deleveraging vs without")
tabs = [
    event_table("drop & OI<=-3% (cascade)", (ev.z <= -3) & (ev.doi <= -0.03)),
    event_table("drop & OI>-1% (no deleveraging)", (ev.z <= -3) & (ev.doi > -0.01)),
    event_table("drop, any OI", (ev.z <= -3)),
]
rep.table(pd.concat(tabs).set_index("group"), digits=1, csv="drops")
rep.h("Sharp 1h rises (z >= 3): short squeeze (OI drop) vs fresh longs (OI rise)")
tabs = [
    event_table("rise & OI<=-3% (squeeze)", (ev.z >= 3) & (ev.doi <= -0.03)),
    event_table("rise & OI>=+1% (new longs)", (ev.z >= 3) & (ev.doi >= 0.01)),
    event_table("rise, any OI", (ev.z >= 3)),
]
rep.table(pd.concat(tabs).set_index("group"), digits=1, csv="rises")

rep.h("Milder thresholds (z <= -2, OI <= -2%) and OI-only signal")
tabs = [
    event_table("z<=-2 & OI<=-2%", (ev.z <= -2) & (ev.doi <= -0.02)),
    event_table("z<=-2 & OI>-0.5%", (ev.z <= -2) & (ev.doi > -0.005)),
    event_table("OI<=-5% in 1h, any price", (ev.doi <= -0.05)),
]
rep.table(pd.concat(tabs).set_index("group"), digits=1)

# Strategy: after a cascade event, long for 12h. One position per symbol at a time.
rep.h("Strategy test: long for 12h after a cascade event (z<=-3 & OI<=-3%), 14 bps round trip")
for hold in (4, 12, 24):
    rows = []
    for s in SYMS:
        g = ev[(ev.symbol == s) & (ev.z <= -3) & (ev.doi <= -0.03)].dropna(subset=[f"fwd_{hold}h"]).sort_index()
        g = g[decluster(g.index, hours=hold)]
        pnl = pd.Series(g[f"fwd_{hold}h"].to_numpy() - 14e-4, index=g.index)
        rows.append(pnl.rename(s))
    pnl = pd.concat(rows).sort_index()
    daily = pnl.groupby(pd.Grouper(freq="1D")).sum()
    daily = daily.reindex(pd.date_range(ev.index.min().floor("D"), ev.index.max().floor("D"), freq="1D", tz="UTC")).fillna(0.0)
    is_m, oos_m = is_oos_mask(daily.index)
    rep.p(f"Hold {hold}h: {len(pnl)} trades ({len(pnl) / (len(daily) / 365):.0f}/yr), mean {pnl.mean() * 1e4:.0f} bps net, hit {(pnl > 0).mean():.0%}, "
          f"total {pnl.sum():.1%} per 1x notional; Sharpe (daily P&L, 1x per trade) full {sharpe(daily, 365):.2f}, IS {sharpe(daily[is_m], 365):.2f}, "
          f"OOS {sharpe(daily[oos_m], 365):.2f}, OOS t={nw_tstat(daily[oos_m].to_numpy()):.2f}.")
print(rep.write().read_text())
