"""Strategy interface shared by the backtester and the live bot.

A strategy is a pure function from market data to target positions (fractions of equity per symbol).
The same `target_positions` runs in research (full history) and live (rolling window; last row used),
so there is one implementation to validate and no backtest/live drift.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class MarketData:
    close: pd.DataFrame                       # time x symbol
    open: pd.DataFrame | None = None
    high: pd.DataFrame | None = None
    low: pd.DataFrame | None = None
    volume: pd.DataFrame | None = None        # base volume
    quote_volume: pd.DataFrame | None = None  # quote (USD) volume
    funding: pd.DataFrame | None = None       # funding-rate events (time x symbol); NaN = no event
    open_interest: pd.DataFrame | None = None # open interest known at each bar's close (time x symbol)

    @property
    def symbols(self) -> list[str]:
        return list(self.close.columns)

    @property
    def index(self) -> pd.DatetimeIndex:
        return self.close.index

    def tail(self, n: int) -> "MarketData":
        def t(df):
            return None if df is None else df.iloc[-n:]
        return MarketData(t(self.close), t(self.open), t(self.high), t(self.low), t(self.volume), t(self.quote_volume),
                          None if self.funding is None else self.funding[self.funding.index >= self.close.index[-n]],
                          t(self.open_interest))


class Strategy(ABC):
    name: str = "strategy"
    params: dict = field(default_factory=dict)

    def __init__(self, **params):
        self.params = params

    @abstractmethod
    def target_positions(self, md: MarketData) -> pd.DataFrame:
        """Return time x symbol target positions (fraction of equity, +long/-short)."""

    def warmup_bars(self) -> int:
        """Minimum history (bars) required before positions are meaningful."""
        return 1

    def __repr__(self) -> str:
        p = ", ".join(f"{k}={v}" for k, v in self.params.items())
        return f"{self.__class__.__name__}({p})"


# --------------------------------------------------------------------------- shared indicators
def log_returns(close: pd.DataFrame) -> pd.DataFrame:
    return np.log(close).diff()


def realized_vol(close: pd.DataFrame, window: int, periods_per_year: float) -> pd.DataFrame:
    """Annualised rolling standard deviation of log returns."""
    return log_returns(close).rolling(window, min_periods=max(2, window // 2)).std() * np.sqrt(periods_per_year)


def ewm_vol(close: pd.DataFrame, halflife: int, periods_per_year: float) -> pd.DataFrame:
    r = log_returns(close)
    return r.ewm(halflife=halflife, min_periods=max(2, halflife)).std() * np.sqrt(periods_per_year)


def vol_target_scale(vol: pd.DataFrame, target_vol: float, max_leverage: float) -> pd.DataFrame:
    """Position scale that targets `target_vol` annualised, capped at `max_leverage`."""
    return (target_vol / vol.replace(0, np.nan)).clip(upper=max_leverage).fillna(0.0)
