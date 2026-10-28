"""Vectorised backtester for target-position strategies.

Conventions
-----------
* `pos[t]` is the target position (fraction of equity, +long / -short, may exceed 1 for leverage)
  decided at the close of bar `t` using information available at `t`; it is held over (t, t+1].
* The return booked at bar `t` is therefore `pos[t-1] * (close[t]/close[t-1] - 1)`.
* Trading happens at the close of `t` at a cost of `|pos[t]-pos[t-1]| * (fee + slippage)`.
* Funding events (perpetual swaps) with timestamp in (t-1, t] are charged to `pos[t-1]`:
  longs pay when the rate is positive.
Everything is in simple returns per bar; equity compounds.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from tvc.config import DEFAULT_SLIPPAGE_BPS, PERP_TAKER_FEE_BPS


@dataclass(frozen=True)
class Costs:
    fee_bps: float = PERP_TAKER_FEE_BPS
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS

    @property
    def per_unit(self) -> float:
        """Cost as a fraction of notional traded, per side."""
        return (self.fee_bps + self.slippage_bps) / 1e4


def align_funding(funding: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    """Sum funding-rate events into the bar in which they settle.

    Bars are indexed by open time. Row `i` of a backtest covers wall-clock (index[i], index[i+1]] and is earned by
    `pos[i-1]` (decided at the close of bar i-1, i.e. at wall-clock index[i]). A funding event at time T therefore
    belongs to row `i` with `index[i] < T <= index[i+1]`: the position in place when the settlement happens pays it,
    and a position opened exactly at T does not. Returns a series on `index` (0 where no event).
    """
    out = pd.Series(0.0, index=index)
    if funding is None or len(funding) == 0:
        return out
    f = funding.dropna()
    fidx = pd.DatetimeIndex(f.index)
    fidx = fidx.tz_localize("UTC") if fidx.tz is None else fidx.tz_convert("UTC")
    idx = index.tz_localize("UTC") if index.tz is None else index.tz_convert("UTC")
    f = pd.Series(f.to_numpy(), index=fidx)
    if len(idx) > 1:
        f = f[(f.index > idx[0]) & (f.index <= idx[-1] + (idx[-1] - idx[-2]))]
    if len(f) == 0:
        return out
    loc = idx.searchsorted(f.index, side="left") - 1  # last bar open time strictly before T
    keep = loc >= 0
    if not keep.any():
        return out
    out = out.add(pd.Series(f.values[keep], index=index[loc[keep]]).groupby(level=0).sum(), fill_value=0.0)
    return out.reindex(index).fillna(0.0)


@dataclass
class BacktestResult:
    returns: pd.Series            # net simple return per bar
    gross: pd.Series
    costs: pd.Series
    funding: pd.Series            # funding P&L (positive = received)
    positions: pd.Series | pd.DataFrame
    turnover: pd.Series           # sum |delta pos| per bar
    meta: dict = field(default_factory=dict)

    @property
    def equity(self) -> pd.Series:
        return (1.0 + self.returns.fillna(0.0)).cumprod()

    def summary(self, periods_per_year: float | None = None, **kw) -> dict:
        from .stats import summary
        s = summary(self.returns, periods_per_year=periods_per_year, **kw)
        s["avg_turnover_per_year"] = float(self.turnover.mean() * (periods_per_year or _infer_ppy(self.returns.index)))
        s["avg_gross_exposure"] = float(np.abs(self.positions).sum(axis=1).mean()) if isinstance(self.positions, pd.DataFrame) else float(np.abs(self.positions).mean())
        return s


def _infer_ppy(index: pd.DatetimeIndex) -> float:
    if len(index) < 3:
        return 365.0
    dt = np.median(np.diff(index.values).astype("timedelta64[s]").astype(float))
    return 365.0 * 86400.0 / dt


def backtest(close: pd.Series, pos: pd.Series, costs: Costs = Costs(), funding: pd.Series | None = None,
             lag: int = 1) -> BacktestResult:
    """Single-asset backtest. `pos` is aligned to `close`'s index; `lag` bars of execution delay (default 1)."""
    close = close.astype(float)
    pos = pos.reindex(close.index).astype(float).ffill().fillna(0.0)
    pos = pos.where(close.notna(), 0.0)
    ret = close.pct_change(fill_method=None).fillna(0.0)
    held = pos.shift(lag).fillna(0.0)
    gross = held * ret
    turnover = pos.diff().abs().fillna(pos.abs())
    cost = turnover * costs.per_unit
    if funding is not None and len(funding):
        fr = align_funding(funding, close.index)
        fund = -held * fr
    else:
        fund = pd.Series(0.0, index=close.index)
    net = gross - cost + fund
    return BacktestResult(net, gross, cost, fund, pos, turnover, {"costs": costs})


def backtest_portfolio(close: pd.DataFrame, pos: pd.DataFrame, costs: Costs | dict = Costs(),
                       funding: pd.DataFrame | None = None, lag: int = 1) -> BacktestResult:
    """Multi-asset backtest: `pos` columns are fractions of total equity per symbol.
    `costs` may be a single Costs or a {symbol: Costs} dict (e.g. spot taker vs perp taker fees)."""
    close = close.astype(float)
    pos = pos.reindex(index=close.index, columns=close.columns).astype(float).ffill().fillna(0.0)
    pos = pos.where(close.notna(), 0.0)
    ret = close.pct_change(fill_method=None).fillna(0.0)
    held = pos.shift(lag).fillna(0.0)
    gross = (held * ret).sum(axis=1)
    turnover_by_symbol = pos.diff().abs().fillna(pos.abs())
    turnover = turnover_by_symbol.sum(axis=1)
    if isinstance(costs, dict):
        per_unit = pd.Series({c: (costs.get(c) or Costs()).per_unit for c in close.columns})
        cost = (turnover_by_symbol * per_unit).sum(axis=1)
    else:
        cost = turnover * costs.per_unit
    fund = pd.Series(0.0, index=close.index)
    if funding is not None and len(funding):
        fr = pd.DataFrame({c: align_funding(funding[c], close.index) for c in close.columns if c in funding.columns})
        fund = -(held.reindex(columns=fr.columns) * fr).sum(axis=1)
    net = gross - cost + fund
    return BacktestResult(net, gross, cost, fund, pos, turnover, {"costs": costs})


def apply_no_trade_band(target: pd.DataFrame, band: float) -> pd.DataFrame:
    """Hold the current position unless the target differs by more than `band` x |target| (relative band,
    e.g. 0.25 = rebalance only when 25% away from target). Exits to exactly zero are always honoured.
    Cuts turnover caused by vol-scaling noise without changing the strategy's economic exposure."""
    T = target.to_numpy(dtype=float)
    out = np.empty_like(T)
    cur = np.zeros(T.shape[1])
    for i in range(T.shape[0]):
        t = T[i]
        t_f = np.where(np.isnan(t), 0.0, t)
        move = (np.abs(t_f - cur) > band * np.abs(t_f)) | ((t_f == 0.0) & (cur != 0.0))
        cur = np.where(move, t_f, cur)
        out[i] = cur
    return pd.DataFrame(out, index=target.index, columns=target.columns)
