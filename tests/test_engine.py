import numpy as np
import pandas as pd
import pytest

from tvc.backtest import Costs, backtest, backtest_portfolio, align_funding


def _close(n=100, seed=0):
    idx = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    rng = np.random.default_rng(seed)
    return pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.01, n)), index=idx)


def test_constant_long_equals_buy_and_hold_without_costs():
    c = _close()
    pos = pd.Series(1.0, index=c.index)
    res = backtest(c, pos, Costs(0, 0))
    # first bar pays nothing (no position held yet), afterwards identical to price changes
    assert res.returns.iloc[0] == 0
    np.testing.assert_allclose(res.returns.iloc[1:].to_numpy(), c.pct_change().iloc[1:].to_numpy())
    np.testing.assert_allclose(res.equity.iloc[-1], c.iloc[-1] / c.iloc[0])


def test_costs_charged_on_turnover_only():
    c = _close()
    pos = pd.Series(0.0, index=c.index)
    pos.iloc[10:20] = 1.0  # enter at bar 10, exit at bar 20 -> turnover 2
    res = backtest(c, pos, Costs(fee_bps=5, slippage_bps=5))
    assert pytest.approx(res.costs.sum(), rel=1e-12) == 2 * 10 / 1e4
    assert res.costs.iloc[10] > 0 and res.costs.iloc[20] > 0 and res.costs.iloc[15] == 0


def test_short_position_sign():
    c = _close()
    pos = pd.Series(-1.0, index=c.index)
    res = backtest(c, pos, Costs(0, 0))
    np.testing.assert_allclose(res.gross.iloc[1:].to_numpy(), -c.pct_change().iloc[1:].to_numpy())


def test_funding_alignment_and_sign():
    c = _close(n=48)
    # bars are indexed by open time; row 7 covers wall-clock (index[7], index[8]] so an event exactly at index[8]
    # is paid by the position in place during that interval (pos[6]) and booked in row 7
    f = pd.Series([0.001], index=[c.index[8]])
    fr = align_funding(f, c.index)
    assert fr.iloc[7] == 0.001 and fr.drop(c.index[7]).abs().sum() == 0
    # an event 1 minute after index[8] falls in row 8 (interval (index[8], index[9]])
    f2 = pd.Series([0.001], index=[c.index[8] + pd.Timedelta(minutes=1)])
    assert align_funding(f2, c.index).iloc[8] == 0.001
    pos = pd.Series(1.0, index=c.index)
    res = backtest(c, pos, Costs(0, 0), funding=f)
    assert pytest.approx(res.funding.iloc[7]) == -0.001  # long pays positive funding
    res_s = backtest(c, -pos, Costs(0, 0), funding=f)
    assert pytest.approx(res_s.funding.iloc[7]) == 0.001
    # a position opened exactly at the settlement does not pay it
    pos2 = pd.Series(0.0, index=c.index); pos2.iloc[7:] = 1.0   # decided at close of bar 7 = wall-clock index[8]
    assert backtest(c, pos2, Costs(0, 0), funding=f).funding.abs().sum() == 0


def test_portfolio_matches_sum_of_singles():
    c1, c2 = _close(seed=1), _close(seed=2)
    close = pd.DataFrame({"A": c1, "B": c2})
    pos = pd.DataFrame({"A": 0.5, "B": -0.5}, index=close.index)
    pos.iloc[:5] = 0
    costs = Costs(3, 1)
    res = backtest_portfolio(close, pos, costs)
    r1 = backtest(c1, pos["A"], costs).returns
    r2 = backtest(c2, pos["B"], costs).returns
    np.testing.assert_allclose(res.returns.to_numpy(), (r1 + r2).to_numpy())


def test_position_zeroed_when_price_missing():
    c = _close()
    c.iloc[50:] = np.nan  # delisted
    pos = pd.Series(1.0, index=c.index)
    res = backtest(c, pos, Costs(0, 0))
    assert (res.positions.iloc[50:] == 0).all()
    assert np.isfinite(res.returns).all()


def test_lag_two_bars():
    c = _close()
    pos = pd.Series(0.0, index=c.index)
    pos.iloc[10] = 1.0
    pos.iloc[11:] = 1.0
    res = backtest(c, pos, Costs(0, 0), lag=2)
    assert res.gross.iloc[11] == 0 and res.gross.iloc[12] != 0


def test_no_trade_band_relative():
    from tvc.backtest import apply_no_trade_band
    idx = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
    tgt = pd.DataFrame({"A": [0.010, 0.011, 0.015, 0.0, 0.02]}, index=idx)
    out = apply_no_trade_band(tgt, 0.25)
    assert out["A"].tolist() == [0.010, 0.010, 0.015, 0.0, 0.02]  # 10% drift ignored, 50% drift traded, exit honoured


def test_portfolio_per_symbol_costs():
    c1, c2 = _close(seed=1), _close(seed=2)
    close = pd.DataFrame({"A": c1, "B": c2})
    pos = pd.DataFrame({"A": 1.0, "B": 1.0}, index=close.index)
    res = backtest_portfolio(close, pos, {"A": Costs(10, 0), "B": Costs(0, 0)})
    assert pytest.approx(res.costs.sum()) == 10 / 1e4  # only A charged, once on entry
