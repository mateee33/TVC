"""Shared helpers for the research scripts."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

from tvc.backtest.report import df_to_md  # noqa: F401
from tvc.config import OOS_START, REPORTS_DIR
from tvc.data import BinanceVision

bv = BinanceVision(workers=12)


class Report:
    """Accumulates markdown sections and writes `reports/<name>.md` (+ companion CSVs)."""

    def __init__(self, name: str, title: str):
        self.name, self.title = name, title
        self.parts: list[str] = [f"# {title}\n", f"_Generated {dt.datetime.now(dt.UTC):%Y-%m-%d %H:%M} UTC. In-sample < {OOS_START} <= out-of-sample._\n"]

    def h(self, text: str, level: int = 2):
        self.parts.append(f"\n{'#' * level} {text}\n")

    def p(self, text: str):
        self.parts.append(text + "\n")

    def table(self, df: pd.DataFrame, digits: int = 2, index: bool = True, csv: str | None = None):
        self.parts.append(df_to_md(df, digits=digits, index=index) + "\n")
        if csv:
            df.to_csv(REPORTS_DIR / f"{self.name}_{csv}.csv")

    def write(self) -> Path:
        out = REPORTS_DIR / f"{self.name}.md"
        out.write_text("\n".join(self.parts))
        return out


def pct(x, digits=2):
    return f"{100 * x:.{digits}f}%"


def bps(x, digits=1):
    return f"{1e4 * x:.{digits}f}"


def is_oos_mask(index: pd.DatetimeIndex, oos_start: str = OOS_START):
    ts = pd.Timestamp(oos_start, tz="UTC")
    return index < ts, index >= ts


MAJORS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT",
    "LINKUSDT", "DOTUSDT", "MATICUSDT", "POLUSDT", "LTCUSDT", "BCHUSDT", "UNIUSDT", "ATOMUSDT",
    "NEARUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "SUIUSDT", "TRXUSDT", "FILUSDT", "ETCUSDT",
    "XLMUSDT", "INJUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "1000PEPEUSDT", "WIFUSDT", "TONUSDT",
    "ICPUSDT", "HBARUSDT", "RENDERUSDT", "FETUSDT", "ORDIUSDT", "1000SHIBUSDT", "ENAUSDT",
    "WLDUSDT", "JUPUSDT", "TAOUSDT", "ALGOUSDT", "SANDUSDT", "AXSUSDT", "EOSUSDT", "GALAUSDT",
]


def load_majors_daily(min_days: int = 365, market: str = "um"):
    """Wide close/quote-volume frames for the majors with enough history, plus funding."""
    close = bv.load_many(MAJORS, "1d", market, "close")
    qv = bv.load_many(MAJORS, "1d", market, "quote_volume")
    keep = [c for c in close.columns if close[c].notna().sum() >= min_days]
    close, qv = close[keep], qv[keep]
    funding = bv.funding_many(keep) if market == "um" else None
    return close, qv, funding


def summarize_variants(results: dict, ppy: float, oos_start: str):
    """results: name -> net return series. Returns a DataFrame of full / IS / OOS stats."""
    from tvc.backtest import stats
    rows = []
    for name, r in results.items():
        r_is, r_oos = stats.split(r, oos_start)
        rows.append({
            "variant": name,
            "sharpe": stats.sharpe(r, ppy), "ann_ret": stats.summary(r, ppy)["ann_return"],
            "max_dd": stats.max_drawdown(r), "t_nw": stats.nw_tstat(r),
            "is_sharpe": stats.sharpe(r_is, ppy), "oos_sharpe": stats.sharpe(r_oos, ppy),
            "oos_t_nw": stats.nw_tstat(r_oos), "oos_ann_ret": stats.summary(r_oos, ppy)["ann_return"] if len(r_oos) > 10 else float("nan"),
        })
    return pd.DataFrame(rows).set_index("variant")
