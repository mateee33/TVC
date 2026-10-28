import numpy as np
import pandas as pd

from tvc.backtest import stats


def test_sharpe_scaling():
    r = np.array([0.01, -0.005, 0.02, 0.0, 0.01])
    s_daily = stats.sharpe(r, 1)
    assert np.isclose(stats.sharpe(r, 365), s_daily * np.sqrt(365))


def test_nw_tstat_detects_strong_signal():
    rng = np.random.default_rng(0)
    x = rng.normal(0.002, 0.01, 5000)
    assert stats.nw_tstat(x) > 5
    assert abs(stats.nw_tstat(rng.normal(0, 0.01, 5000))) < 3


def test_max_drawdown():
    r = np.array([0.1, -0.5, 0.2])
    assert np.isclose(stats.max_drawdown(r), -0.5)


def test_psr_monotone_and_bounded():
    a = stats.probabilistic_sharpe(0.05, 1000, 0.0, 3.0)
    b = stats.probabilistic_sharpe(0.10, 1000, 0.0, 3.0)
    assert 0 < a < b < 1


def test_expected_max_sharpe_grows_with_trials():
    e1 = stats.expected_max_sharpe(10, 0.01)
    e2 = stats.expected_max_sharpe(1000, 0.01)
    assert 0 < e1 < e2


def test_deflated_sharpe_below_psr_when_many_trials():
    rng = np.random.default_rng(1)
    r = rng.normal(0.001, 0.01, 2000)
    psr = stats.probabilistic_sharpe(r.mean() / r.std(ddof=1), len(r), 0, 3)
    dsr = stats.deflated_sharpe(r, n_trials=200, var_sr_trials=0.001)
    assert dsr < psr


def test_bootstrap_ci_contains_point_estimate():
    rng = np.random.default_rng(2)
    idx = pd.date_range("2020-01-01", periods=1500, freq="D", tz="UTC")
    r = pd.Series(rng.normal(0.001, 0.02, 1500), index=idx)
    sr = stats.sharpe(r, 365)
    bs = stats.stationary_bootstrap_sharpe(r, 365, n_boot=300)
    assert bs["ci_low"] < sr < bs["ci_high"]


def test_summary_and_yearly():
    rng = np.random.default_rng(3)
    idx = pd.date_range("2021-01-01", periods=800, freq="D", tz="UTC")
    r = pd.Series(rng.normal(0.0005, 0.02, 800), index=idx)
    s = stats.summary(r, name="x", n_boot=100)
    assert s["n"] == 800 and "boot_p_value" in s and np.isfinite(s["sharpe"])
    yt = stats.yearly_table(r)
    assert set(yt.index) == {2021, 2022, 2023}
