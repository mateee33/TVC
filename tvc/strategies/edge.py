"""The edges validated in research/ (see reports/): one market-neutral core and two long overlays.

Core  - FundingCarry: long spot / short perp while trailing-7d annualised funding is high (hysteresis filter).
        Earns the funding stream; basis risk only. Research: Sharpe 4-6, ~8-12%/yr on notional, 2% max drawdown.
Overlay - CascadeReversal: after a sharp 1h drop (z <= -3 vs trailing 30d) with open interest down >= 3% in the
        same hour (forced deleveraging), go long the perp for a few hours. Research: +40-80 bps per event net.
Overlay - FundingRebound: for the hour after a settlement whose (8h-normalised) rate exceeded 5 bps, go long the
        perp. Research: +22 bps per event (t=11) but regime-dependent; dormant in calm markets.

Everything is a pure function of MarketData, shared by backtest and live. Symbols come as (spot, perp) pairs;
spot may be None (perp-only account: overlays only, no carry).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from tvc.backtest.engine import align_funding
from tvc.strategies.base import MarketData, Strategy


def _bars_per(td: pd.Timedelta, index: pd.DatetimeIndex) -> int:
    step = pd.Timedelta(np.median(np.diff(index.values)))
    return max(1, int(round(td / step)))


def _hysteresis(x: np.ndarray, enter: float, exit_: float) -> np.ndarray:
    on, state = np.zeros(len(x)), False
    for i in range(len(x)):
        v = x[i]
        if not np.isnan(v):
            if not state and v > enter:
                state = True
            elif state and v < exit_:
                state = False
        on[i] = 1.0 if state else 0.0
    return on


def carry_state(funding_events: pd.Series, index: pd.DatetimeIndex, enter: float, exit_: float, window_days: int = 7) -> pd.Series:
    """1.0 while the carry trade is on. Trailing funding is annualised from the events settled in the last `window_days`."""
    fr = align_funding(funding_events, index)                   # funding booked to the bar in which it settles
    bars_7d = _bars_per(pd.Timedelta(days=window_days), index)
    ann = fr.rolling(bars_7d, min_periods=bars_7d // 2).sum() * (365.0 / window_days)
    return pd.Series(_hysteresis(ann.to_numpy(), enter, exit_), index=index)


def cascade_active(close: pd.Series, oi: pd.Series, z_thr: float, oi_thr: float, hold_hours: int,
                   vol_days: int = 30) -> pd.Series:
    """1.0 for `hold_hours` after a cascade event (sharp drop + deleveraging), detected at the bar close."""
    idx = close.index
    b1h = _bars_per(pd.Timedelta(hours=1), idx)
    r1h = close.pct_change(b1h)
    sd = r1h.rolling(_bars_per(pd.Timedelta(days=vol_days), idx), min_periods=_bars_per(pd.Timedelta(days=5), idx)).std()
    z = r1h / sd
    doi = oi.reindex(idx).pct_change(b1h)
    event = ((z <= z_thr) & (doi <= oi_thr)).astype(float)
    return event.rolling(hold_hours * b1h, min_periods=1).max().fillna(0.0)


def rebound_active(funding_events: pd.Series, index: pd.DatetimeIndex, thr_8h: float, interval_hours: float = 8.0,
                   hold_hours: int = 1) -> pd.Series:
    """1.0 for the hour after a settlement whose 8h-equivalent rate exceeded `thr_8h`.
    The position is taken at the settlement itself (decided at the close of the bar ending at T)."""
    f = funding_events.dropna() * (8.0 / interval_hours)
    out = pd.Series(0.0, index=index)
    if len(f) == 0:
        return out
    f = f[f > thr_8h]
    if len(f) == 0:
        return out
    loc = index.searchsorted(f.index, side="left") - 1  # bar whose close is the settlement time T
    loc = loc[loc >= 0]
    out.iloc[loc] = 1.0
    b1h = _bars_per(pd.Timedelta(hours=1), index)
    return out.rolling(hold_hours * b1h, min_periods=1).max().fillna(0.0)


class EdgeCombo(Strategy):
    """Carry core + cascade and rebound overlays. Weights are fractions of equity.

    pairs:        [[spot_symbol or None, perp_symbol], ...]
    carry_weight: notional per leg per pair (default 1/n_pairs -> gross 2x when all pairs are on)
    overlay_weight: long perp exposure per overlay event (default = carry_weight / 2: the overlays buy crashes, and
                    sizing them at half the carry leg halved the 2022 FTX-day drawdown in research while keeping
                    most of the Sharpe)
    """
    name = "edge"
    needs_funding = True
    needs_open_interest = True

    def __init__(self, pairs, carry: bool = True, cascade: bool = True, rebound: bool = True,
                 carry_enter: float = 0.10, carry_exit: float = 0.0, carry_window_days: int = 7,
                 cascade_z: float = -3.0, cascade_oi: float = -0.03, cascade_hold_hours: int = 4,
                 rebound_thr_8h: float = 0.0005, funding_interval_hours: float = 8.0,
                 carry_weight: float | None = None, overlay_weight: float | None = None):
        pairs = [tuple(p) for p in pairs]
        super().__init__(pairs=pairs, carry=carry, cascade=cascade, rebound=rebound, carry_enter=carry_enter,
                         carry_exit=carry_exit, carry_window_days=carry_window_days, cascade_z=cascade_z,
                         cascade_oi=cascade_oi, cascade_hold_hours=cascade_hold_hours, rebound_thr_8h=rebound_thr_8h,
                         funding_interval_hours=funding_interval_hours,
                         carry_weight=carry_weight if carry_weight is not None else 1.0 / len(pairs),
                         overlay_weight=overlay_weight)

    def warmup_bars(self) -> int:
        return 1  # depends on bar size; the bot sizes the lookback from `lookback_days`

    lookback_days = 31

    def target_positions(self, md: MarketData) -> pd.DataFrame:
        p = self.params
        idx = md.close.index
        w = p["carry_weight"]
        wo = p["overlay_weight"] if p["overlay_weight"] is not None else 0.5 * w
        cols = {}
        for spot, perp in p["pairs"]:
            perp_w = pd.Series(0.0, index=idx)
            fund = md.funding[perp].dropna() if (md.funding is not None and perp in md.funding.columns) else pd.Series(dtype=float)
            if p["carry"] and spot is not None and spot in md.close.columns and len(fund):
                on = carry_state(fund, idx, p["carry_enter"], p["carry_exit"], p["carry_window_days"])
                cols[spot] = w * on
                perp_w = perp_w - w * on
            elif spot is not None and spot in md.close.columns:
                cols[spot] = pd.Series(0.0, index=idx)
            overlay = pd.Series(0.0, index=idx)
            if p["cascade"] and md.open_interest is not None and perp in md.open_interest.columns:
                overlay = np.maximum(overlay, cascade_active(md.close[perp], md.open_interest[perp], p["cascade_z"], p["cascade_oi"], p["cascade_hold_hours"]))
            if p["rebound"] and len(fund):
                overlay = np.maximum(overlay, rebound_active(fund, idx, p["rebound_thr_8h"], p["funding_interval_hours"]))
            cols[perp] = perp_w + wo * overlay
        return pd.DataFrame(cols, index=idx).fillna(0.0)


class FundingCarry(EdgeCombo):
    name = "carry"
    def __init__(self, pairs, **kw):
        kw.update(cascade=False, rebound=False)
        super().__init__(pairs, **kw)


class CascadeReversal(EdgeCombo):
    name = "cascade"
    def __init__(self, pairs, **kw):
        kw.update(carry=False, rebound=False)
        super().__init__(pairs, **kw)


class FundingRebound(EdgeCombo):
    name = "funding_rebound"
    def __init__(self, pairs, **kw):
        kw.update(carry=False, cascade=False)
        super().__init__(pairs, **kw)
