"""Performance statistics with an eye on robustness: HAC t-stats, bootstrap CIs and
multiple-testing-aware Sharpe ratios (Bailey & Lopez de Prado's PSR/DSR)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats as sps

EULER_GAMMA = 0.5772156649015329


def infer_periods_per_year(index: pd.DatetimeIndex) -> float:
    if len(index) < 3:
        return 365.0
    dt = np.median(np.diff(index.values).astype("timedelta64[s]").astype(float))
    return 365.0 * 86400.0 / dt


def _clean(r) -> np.ndarray:
    x = np.asarray(r, dtype=float)
    return x[~np.isnan(x)]


def sharpe(r, periods_per_year: float) -> float:
    x = _clean(r)
    if len(x) < 2 or x.std(ddof=1) == 0:
        return float("nan")
    return float(x.mean() / x.std(ddof=1) * math.sqrt(periods_per_year))


def sortino(r, periods_per_year: float) -> float:
    x = _clean(r)
    dn = x[x < 0]
    if len(x) < 2 or len(dn) == 0:
        return float("nan")
    dd = math.sqrt((dn ** 2).sum() / len(x))
    return float(x.mean() / dd * math.sqrt(periods_per_year)) if dd > 0 else float("nan")


def max_drawdown(returns) -> float:
    x = _clean(returns)
    eq = np.cumprod(1.0 + x)
    peak = np.maximum.accumulate(eq)
    return float(((eq - peak) / peak).min()) if len(eq) else float("nan")


def nw_tstat(r, lags: int | None = None) -> float:
    """Newey-West (Bartlett kernel) t-statistic for H0: mean(r) = 0."""
    x = _clean(r)
    n = len(x)
    if n < 10:
        return float("nan")
    if lags is None:
        lags = int(math.floor(4 * (n / 100.0) ** (2.0 / 9.0)))
    e = x - x.mean()
    s = float(e @ e) / n
    for L in range(1, lags + 1):
        w = 1.0 - L / (lags + 1.0)
        s += 2.0 * w * float(e[L:] @ e[:-L]) / n
    se = math.sqrt(max(s, 1e-30) / n)
    return float(x.mean() / se)


def stationary_bootstrap_sharpe(r, periods_per_year: float, n_boot: int = 2000, mean_block: float | None = None,
                                seed: int = 0, ci: float = 0.95) -> dict:
    """Politis-Romano stationary bootstrap of the annualised Sharpe ratio.
    Returns percentile CI and the one-sided p-value P(Sharpe <= 0)."""
    x = _clean(r)
    n = len(x)
    if n < 20:
        return {"ci_low": float("nan"), "ci_high": float("nan"), "p_value": float("nan")}
    if mean_block is None:
        mean_block = max(2.0, n ** (1.0 / 3.0))
    p = 1.0 / mean_block
    rng = np.random.default_rng(seed)
    # Build indices: start positions and run lengths (geometric) until we have n samples.
    srs = np.empty(n_boot)
    for b in range(n_boot):
        idx = np.empty(n, dtype=np.int64)
        i = 0
        while i < n:
            start = rng.integers(0, n)
            L = rng.geometric(p)
            L = min(L, n - i)
            idx[i:i + L] = (start + np.arange(L)) % n
            i += L
        xs = x[idx]
        sd = xs.std(ddof=1)
        srs[b] = xs.mean() / sd * math.sqrt(periods_per_year) if sd > 0 else 0.0
    a = (1 - ci) / 2
    return {
        "ci_low": float(np.quantile(srs, a)),
        "ci_high": float(np.quantile(srs, 1 - a)),
        "p_value": float((srs <= 0).mean()),
    }


def probabilistic_sharpe(sr_period: float, n: int, skew: float, kurt: float, sr_benchmark: float = 0.0) -> float:
    """PSR: probability that the true (per-period) Sharpe exceeds `sr_benchmark`, given non-normality.
    `kurt` is the (non-excess) kurtosis, 3 for a normal distribution."""
    if n < 3 or not np.isfinite(sr_period):
        return float("nan")
    denom = math.sqrt(max(1.0 - skew * sr_period + (kurt - 1.0) / 4.0 * sr_period ** 2, 1e-12))
    z = (sr_period - sr_benchmark) * math.sqrt(n - 1) / denom
    return float(sps.norm.cdf(z))


def expected_max_sharpe(n_trials: int, var_sr_trials: float) -> float:
    """Expected maximum per-period Sharpe among `n_trials` zero-skill strategies (Bailey & Lopez de Prado 2014)."""
    if n_trials <= 1 or var_sr_trials <= 0:
        return 0.0
    n = n_trials
    return math.sqrt(var_sr_trials) * ((1 - EULER_GAMMA) * sps.norm.ppf(1 - 1.0 / n) + EULER_GAMMA * sps.norm.ppf(1 - 1.0 / (n * math.e)))


def deflated_sharpe(r, n_trials: int, var_sr_trials: float) -> float:
    """DSR: PSR against the Sharpe one would expect from the best of `n_trials` random strategies.
    `var_sr_trials` is the variance of the per-period Sharpe ratios across the trials actually run."""
    x = _clean(r)
    n = len(x)
    if n < 3 or x.std(ddof=1) == 0:
        return float("nan")
    sr = x.mean() / x.std(ddof=1)
    sk = float(sps.skew(x))
    ku = float(sps.kurtosis(x, fisher=False))
    return probabilistic_sharpe(sr, n, sk, ku, expected_max_sharpe(n_trials, var_sr_trials))


def summary(r: pd.Series, periods_per_year: float | None = None, n_boot: int = 0, name: str | None = None) -> dict:
    r = pd.Series(r).dropna()
    ppy = periods_per_year or infer_periods_per_year(r.index)
    x = r.to_numpy(dtype=float)
    n = len(x)
    out = {
        "name": name,
        "n": n,
        "years": n / ppy if ppy else float("nan"),
        "ann_return": float((1 + x).prod() ** (ppy / n) - 1) if n and (1 + x).min() > 0 else float("nan"),
        "ann_vol": float(x.std(ddof=1) * math.sqrt(ppy)) if n > 1 else float("nan"),
        "sharpe": sharpe(x, ppy),
        "sortino": sortino(x, ppy),
        "max_dd": max_drawdown(x),
        "t_stat_nw": nw_tstat(x),
        "hit_rate": float((x > 0).sum() / max((x != 0).sum(), 1)),
        "skew": float(sps.skew(x)) if n > 2 else float("nan"),
        "kurt": float(sps.kurtosis(x, fisher=False)) if n > 3 else float("nan"),
    }
    if n > 3 and x.std(ddof=1) > 0:
        out["psr_0"] = probabilistic_sharpe(x.mean() / x.std(ddof=1), n, out["skew"], out["kurt"], 0.0)
    if n_boot:
        out.update({f"boot_{k}": v for k, v in stationary_bootstrap_sharpe(x, ppy, n_boot=n_boot).items()})
    return out


def yearly_table(r: pd.Series, periods_per_year: float | None = None) -> pd.DataFrame:
    r = pd.Series(r).dropna()
    ppy = periods_per_year or infer_periods_per_year(r.index)
    rows = []
    for y, g in r.groupby(r.index.year):
        rows.append({"year": int(y), "return": float((1 + g).prod() - 1), "sharpe": sharpe(g, ppy),
                     "max_dd": max_drawdown(g), "n": len(g)})
    return pd.DataFrame(rows).set_index("year")


def split(r: pd.Series, oos_start: str) -> tuple[pd.Series, pd.Series]:
    ts = pd.Timestamp(oos_start, tz="UTC")
    return r[r.index < ts], r[r.index >= ts]
