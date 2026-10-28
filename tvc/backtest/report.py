"""Markdown helpers for research reports."""
from __future__ import annotations

import numpy as np
import pandas as pd


def fmt(v, digits=2):
    if isinstance(v, (float, np.floating)):
        if np.isnan(v):
            return ""
        if abs(v) >= 1000:
            return f"{v:,.0f}"
        return f"{v:.{digits}f}"
    return str(v)


def df_to_md(df: pd.DataFrame, digits: int = 2, index: bool = True) -> str:
    df = df.copy()
    cols = list(df.columns)
    header = ([df.index.name or ""] if index else []) + [str(c) for c in cols]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for idx, row in df.iterrows():
        cells = ([str(idx)] if index else []) + [fmt(row[c], digits) for c in cols]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def summaries_to_md(summaries: list[dict], keys=None, digits=2) -> str:
    keys = keys or ["name", "years", "ann_return", "ann_vol", "sharpe", "max_dd", "t_stat_nw", "psr_0"]
    df = pd.DataFrame(summaries)[[k for k in keys if k in summaries[0]]]
    return df_to_md(df.set_index(keys[0]), digits=digits)
