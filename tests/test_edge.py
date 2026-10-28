import numpy as np
import pandas as pd

from tvc.strategies.base import MarketData
from tvc.strategies.edge import EdgeCombo, carry_state, cascade_active, rebound_active


def _idx(n, freq="5min"):
    return pd.date_range("2024-03-01", periods=n, freq=freq, tz="UTC")


def test_rebound_window_starts_at_settlement_bar_and_lasts_one_hour():
    idx = _idx(24 * 12)  # one day of 5m bars
    T = pd.Timestamp("2024-03-01 08:00", tz="UTC")
    f = pd.Series([0.0008, 0.0001], index=[T, T + pd.Timedelta(hours=8)])
    act = rebound_active(f, idx, thr_8h=0.0005)
    on = act[act > 0].index
    assert on[0] == T - pd.Timedelta(minutes=5)      # decided at the close of the bar ending at T
    assert on[-1] == T + pd.Timedelta(minutes=50)    # 12 bars -> the hour after settlement
    assert len(on) == 12
    # 4h-interval symbol: rate is normalised x2 before the threshold
    act4 = rebound_active(pd.Series([0.0003], index=[T]), idx, thr_8h=0.0005, interval_hours=4)
    assert act4.sum() == 12


def test_carry_state_hysteresis():
    idx = _idx(24 * 12 * 20)  # 20 days
    times = pd.date_range("2024-03-01", periods=60, freq="8h", tz="UTC")
    rates = np.full(60, 0.0005)   # 0.05% per 8h ~ 55% annualised
    rates[40:] = -0.0001          # turns negative after ~13 days
    f = pd.Series(rates, index=times)
    on = carry_state(f, idx, enter=0.10, exit_=0.0)
    assert on.iloc[0] == 0 and on.max() == 1
    first_on = on[on > 0].index[0]
    assert first_on > idx[0] + pd.Timedelta(days=3)  # needs enough history
    assert on.iloc[-1] == 0                           # exited once trailing funding fell below 0


def test_cascade_event_requires_both_drop_and_oi_fall():
    idx = _idx(24 * 12 * 10)
    rng = np.random.default_rng(0)
    close = pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.001, len(idx))), index=idx)
    oi = pd.Series(1000.0, index=idx)
    k = 24 * 12 * 7
    close.iloc[k:] *= 0.9           # 10% crash in one bar
    a_no = cascade_active(close, oi, -3, -0.03, 4)
    assert a_no.iloc[k] == 0        # OI unchanged -> not a cascade
    oi.iloc[k:] = 900.0             # OI -10%
    a = cascade_active(close, oi, -3, -0.03, 4)
    assert a.iloc[k] == 1 and a.iloc[k + 4 * 12 - 1] == 1 and a.iloc[k + 4 * 12 + 12] == 0


def test_edge_combo_weights():
    idx = _idx(24 * 12 * 20)
    rng = np.random.default_rng(1)
    px = pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.001, len(idx))), index=idx)
    md = MarketData(close=pd.DataFrame({"S": px, "P": px * 1.001}),
                    funding=pd.DataFrame({"P": 0.0005}, index=pd.date_range("2024-03-01", periods=60, freq="8h", tz="UTC")),
                    open_interest=pd.DataFrame({"P": 1000.0}, index=idx))
    pos = EdgeCombo([["S", "P"]], rebound=False).target_positions(md)
    on = pos[pos["S"] > 0]
    assert len(on) > 0 and np.allclose(on["S"], 1.0) and np.allclose(on["P"], -1.0)   # 1x long spot / 1x short perp
    pos2 = EdgeCombo([[None, "P"]]).target_positions(md)                               # perp-only: no carry, overlays only
    assert (pos2["P"] >= 0).all() and "S" not in pos2
