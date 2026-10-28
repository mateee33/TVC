"""Time-series momentum with volatility targeting (Study 3 specification)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from tvc.backtest.engine import apply_no_trade_band
from tvc.strategies.base import MarketData, Strategy, realized_vol, vol_target_scale


class TSMom(Strategy):
    name = "tsmom"

    def __init__(self, lookbacks=(20, 60, 90, 180), long_only: bool = True, target_vol: float = 0.20,
                 max_leverage: float = 1.5, vol_window: int = 30, band: float = 0.25, periods_per_year: float = 365.0):
        super().__init__(lookbacks=list(lookbacks), long_only=long_only, target_vol=target_vol, max_leverage=max_leverage,
                         vol_window=vol_window, band=band, periods_per_year=periods_per_year)

    def warmup_bars(self) -> int:
        return max(self.params["lookbacks"]) + self.params["vol_window"] + 2

    def target_positions(self, md: MarketData) -> pd.DataFrame:
        p = self.params
        close = md.close
        sigs = []
        for N in p["lookbacks"]:
            m = close / close.shift(N) - 1
            sigs.append(np.sign(m) if not p["long_only"] else (m > 0).astype(float).where(m.notna()))
        sig = sum(sigs) / len(sigs)
        vol = realized_vol(close, p["vol_window"], p["periods_per_year"])
        scale = vol_target_scale(vol, p["target_vol"], p["max_leverage"])
        valid = sig.notna() & (scale > 0)
        n_valid = valid.sum(axis=1).replace(0, np.nan)
        pos = (sig.fillna(0.0) * scale).div(n_valid, axis=0).where(valid, 0.0)
        return apply_no_trade_band(pos, p["band"]) if p["band"] else pos
