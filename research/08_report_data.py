"""Collect the numbers the HTML report page needs into reports/report_data.json (run after 05/06/07)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from tvc.backtest import stats
from tvc.config import REPORTS_DIR

out = {}
# equity curves (daily) for combo + components, downsampled to weekly for the page
d = pd.read_csv(REPORTS_DIR / "07_edge_combo_daily_returns.csv", index_col=0, parse_dates=True)
eq = (1 + d).cumprod()
wk = eq.resample("W").last().dropna(how="all")
out["equity"] = {"dates": [t.strftime("%Y-%m-%d") for t in wk.index],
                 "series": {c: [round(float(v), 4) for v in wk[c]] for c in ["combo", "carry_only", "cascade_only", "rebound_only"] if c in wk}}
dd = (eq["combo"] / eq["combo"].cummax() - 1).resample("W").min()
out["drawdown"] = [round(float(v), 4) for v in dd.reindex(wk.index).fillna(0)]
out["yearly"] = {c: {int(y): round(float(v), 4) for y, v in stats.yearly_table(d[c], 365)["return"].items()} for c in ["combo", "carry_only", "cascade_only", "rebound_only"] if c in d}
s = stats.summary(d["combo"], 365, n_boot=500)
r_is, r_oos = stats.split(d["combo"], "2024-01-01")
out["combo_stats"] = {"sharpe": s["sharpe"], "ci_low": s["boot_ci_low"], "ci_high": s["boot_ci_high"], "t": s["t_stat_nw"],
                      "ann_return": s["ann_return"], "ann_vol": s["ann_vol"], "max_dd": s["max_dd"], "hit": s["hit_rate"], "skew": s["skew"],
                      "is_sharpe": stats.sharpe(r_is, 365), "oos_sharpe": stats.sharpe(r_oos, 365), "oos_t": stats.nw_tstat(r_oos),
                      "start": d.index[0].strftime("%Y-%m-%d"), "end": d.index[-1].strftime("%Y-%m-%d")}
comp = pd.read_csv(REPORTS_DIR / "07_edge_combo_components.csv", index_col=0)
out["components"] = {i: {k: (None if pd.isna(v) else round(float(v), 4)) for k, v in row.items()} for i, row in comp.iterrows()}
sens = pd.read_csv(REPORTS_DIR / "07_edge_combo_sensitivities.csv", index_col=0)
out["sensitivities"] = {i: {k: (None if pd.isna(v) else round(float(v), 4)) for k, v in row.items()} for i, row in sens.iterrows()}
# event study (study 5)
drops = pd.read_csv(REPORTS_DIR / "05_oi_cascade_drops.csv")
out["event_study"] = [{k: (None if pd.isna(v) else (round(float(v), 2) if isinstance(v, (float, np.floating)) else v)) for k, v in row.items()} for _, row in drops.iterrows()]
# carry per symbol (study 6)
carry = pd.read_csv(REPORTS_DIR / "06_edge_checks_carry_hourly.csv", index_col=0)
out["carry"] = {i: {k: (None if pd.isna(v) else (round(float(v), 4) if isinstance(v, (float, np.floating)) else v)) for k, v in row.items()} for i, row in carry.iterrows()}
# rebound by year (study 6)
reb = pd.read_csv(REPORTS_DIR / "06_edge_checks_rebound_by_year.csv", index_col=0)
out["rebound"] = {str(i): {k: (None if pd.isna(v) else round(float(v), 2)) for k, v in row.items()} for i, row in reb.iterrows()}
(REPORTS_DIR / "report_data.json").write_text(json.dumps(out))
print("wrote", REPORTS_DIR / "report_data.json", len(json.dumps(out)), "bytes")
