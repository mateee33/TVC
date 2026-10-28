"""Inject reports/report_data.json and the study verdicts into the HTML template -> reports/tvc_edge_report.html."""
from __future__ import annotations

import json
from pathlib import Path

from tvc.config import REPORTS_DIR, REPO_ROOT

FAILS = [
    {"study": "01", "hyp": "Intraday and weekly seasonality (BTC/ETH spot, hourly, 2018–2026): US-hours drift, weekend effect.",
     "result": "Hour-of-day means are unstable across years. The best in-sample window collapses out-of-sample (BTC Sharpe 0.37, ETH −0.24); deflated Sharpe 0.05–0.10 after 552 windows searched. The pre-registered 13–21 UTC window loses after costs.",
     "verdict": "no edge", "cls": "no"},
    {"study": "02b", "hyp": "Funding as a next-day directional signal; cross-sectional funding reversal.",
     "result": "No reversal: extreme funding of either sign precedes positive next-day returns (U-shape). A long-low / short-high funding portfolio loses after costs (Sharpe −0.18).",
     "verdict": "no edge", "cls": "no"},
    {"study": "03", "hyp": "Time-series momentum with volatility targeting on 47 major perps, daily.",
     "result": "Sharpe 0.5–1.1 in-sample, 0.3–0.6 out-of-sample with t < 1. Long-only beats long-short because the short book loses. Alpha over vol-scaled long-only beta is 6% a year at t = 1.6; deflated Sharpe 0.55.",
     "verdict": "weak", "cls": "mixed"},
    {"study": "04", "hyp": "Cross-sectional momentum and short-term reversal across all ~900 USDT perps, weekly quintiles.",
     "result": "__STUDY4__",
     "verdict": "__STUDY4_VERDICT__", "cls": "__STUDY4_CLS__"},
    {"study": "06a", "hyp": "Cascade reversal detected on hourly bars instead of 5-minute bars.",
     "result": "Fewer events and a fading effect (pooled out-of-sample Sharpe 0.35). Most of the rebound happens in the first hour, so the bot runs on a 5-minute cadence.",
     "verdict": "design constraint", "cls": "mixed"},
]

tpl = (REPO_ROOT / "research" / "report_template.html").read_text()
data = json.loads((REPORTS_DIR / "report_data.json").read_text())
s4 = json.loads((REPORTS_DIR / "study4_verdict.json").read_text()) if (REPORTS_DIR / "study4_verdict.json").exists() else {"result": "See reports/04_xs_momentum.md.", "verdict": "see report", "cls": "mixed"}
fails = json.dumps(FAILS).replace("__STUDY4_VERDICT__", s4["verdict"]).replace("__STUDY4_CLS__", s4["cls"]).replace("__STUDY4__", s4["result"].replace('"', '\\"'))
html = tpl.replace("__DATA__", json.dumps(data)).replace("__FAILS__", fails)
out = REPORTS_DIR / "tvc_edge_report.html"
out.write_text(html)
print("wrote", out, len(html), "bytes")
