"""Portfolio-level risk limits. Pure functions on numbers -> easy to unit test."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class RiskLimits:
    max_gross_leverage: float = 1.5     # sum |weights|
    max_symbol_weight: float = 0.5      # |weight| per symbol
    max_daily_loss: float = 0.05        # fraction of day-start equity -> halt for the day
    max_drawdown: float = 0.25          # fraction from peak equity -> halt and flatten
    min_trade_notional: float = 10.0    # skip dust trades (quote currency)
    rebalance_band: float = 0.25        # skip trades smaller than this fraction of the target position

    def clip_targets(self, targets: pd.Series) -> pd.Series:
        t = targets.fillna(0.0).clip(-self.max_symbol_weight, self.max_symbol_weight)
        gross = t.abs().sum()
        if gross > self.max_gross_leverage and gross > 0:
            t = t * (self.max_gross_leverage / gross)
        return t

    def breach(self, equity: float, peak_equity: float, day_start_equity: float) -> str | None:
        if peak_equity > 0 and equity < peak_equity * (1 - self.max_drawdown):
            return f"max drawdown breached: equity {equity:.2f} < {1 - self.max_drawdown:.0%} of peak {peak_equity:.2f}"
        if day_start_equity > 0 and equity < day_start_equity * (1 - self.max_daily_loss):
            return f"daily loss limit breached: equity {equity:.2f} vs day start {day_start_equity:.2f}"
        return None
