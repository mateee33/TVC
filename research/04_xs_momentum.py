"""Study 4 - Cross-sectional momentum / reversal across ALL USD-M perps (survivorship-bias free).

Pre-registered design:
  * universe each week: USDT perps with >= 30 days of history, trailing-30d average quote volume >= $10M,
    excluding stablecoin pairs and index products; the 100 most liquid are eligible
  * signals: trailing return over 7, 14, 28 days (no skip) and 90 days skipping the last 7 (classic momentum);
    each tested with sign +1 (momentum) and -1 (reversal) -> 8 trials
  * portfolio: long top quintile / short bottom quintile, equal weight, dollar neutral, gross 1x
  * weekly rebalance (Monday 00:00 UTC); costs 5 + 2 bps per side; funding paid/received
  * primary spec (declared a priori): 28-day momentum, weekly
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from tvc.backtest import Costs, backtest_portfolio, stats
from tvc.config import OOS_START
from tvc.data import list_um_symbols
import logging, sys
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
from tvc.research.common import Report, bv, summarize_variants

PPY = 365
COSTS = Costs(5, 2)
STABLES = {"USDC", "BUSD", "TUSD", "USDP", "FDUSD", "DAI", "EUR", "USDE", "USD1", "AEUR", "FDUSD"}
rep = Report("04_xs_momentum", "Study 4 - Cross-sectional momentum / reversal, all USDT perps, weekly")

syms = [s for s in list_um_symbols("USDT") if s[:-4] not in STABLES and not re.search(r"(DOM|DEFI)USDT$", s)]
close = bv.load_many(syms, "1d", "um", "close")
qv = bv.load_many(syms, "1d", "um", "quote_volume")
funding = bv.funding_many(list(close.columns))
close = close[close.index >= "2020-01-01"]
qv = qv.reindex(close.index)
rep.p(f"{close.shape[1]} symbols ever listed, {close.index[0]:%Y-%m-%d} to {close.index[-1]:%Y-%m-%d}.")

adv = qv.rolling(30, min_periods=20).mean()
hist = close.notna().rolling(30).sum()
eligible = (adv >= 10e6) & (hist >= 30) & close.notna()
# keep the 100 most liquid eligible names each day
rank_liq = adv.where(eligible).rank(axis=1, ascending=False)
eligible = eligible & (rank_liq <= 100)
rep.p(f"Eligible names per day: median {int(eligible.sum(axis=1).median())}, min {int(eligible.sum(axis=1)[eligible.sum(axis=1) > 0].min())}, max {int(eligible.sum(axis=1).max())}.")

rebal_days = close.index[close.index.dayofweek == 0]  # Mondays


def quintile_portfolio(score: pd.DataFrame, sign: float, rebal: pd.DatetimeIndex, top_frac=0.2) -> pd.DataFrame:
    sc = (sign * score).where(eligible)
    rk = sc.rank(axis=1, pct=True)
    n = sc.notna().sum(axis=1)
    pos = pd.DataFrame(0.0, index=sc.index, columns=sc.columns)
    pos[rk > 1 - top_frac] = 1.0
    pos[rk <= top_frac] = -1.0
    pos = pos.where(n >= 20, 0.0)
    longs = pos.clip(lower=0); shorts = pos.clip(upper=0)
    pos = 0.5 * longs.div(longs.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0) + 0.5 * shorts.div(shorts.abs().sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    # hold between rebalances
    pos = pos[pos.index.isin(rebal)].reindex(pos.index).ffill().fillna(0.0)
    return pos


signals = {
    "ret_7d": close / close.shift(7) - 1,
    "ret_14d": close / close.shift(14) - 1,
    "ret_28d": close / close.shift(28) - 1,
    "ret_90d_skip7": close.shift(7) / close.shift(90) - 1,
}
results, trials = {}, []
for name, sc in signals.items():
    for sign, label in ((1.0, "mom"), (-1.0, "rev")):
        pos = quintile_portfolio(sc, sign, rebal_days)
        res = backtest_portfolio(close, pos, COSTS, funding)
        results[f"{label}_{name}"] = res.returns
        trials.append(res.returns)
rep.h("Weekly quintile long-short portfolios (gross 1x, dollar neutral)")
tab = summarize_variants(results, PPY, OOS_START)
rep.table(tab, digits=2, csv="variants")

primary_pos = quintile_portfolio(signals["ret_28d"], 1.0, rebal_days)
primary = backtest_portfolio(close, primary_pos, COSTS, funding)
r = primary.returns
s = primary.summary(PPY, n_boot=1000)
var_tr = float(np.var([stats.sharpe(t, 1) for t in trials]))
dsr = stats.deflated_sharpe(r, len(trials), var_tr)
rep.h("Primary: 28d momentum, weekly")
rep.p(f"Sharpe {s['sharpe']:.2f} (bootstrap 95% CI {s['boot_ci_low']:.2f} to {s['boot_ci_high']:.2f}), NW t={s['t_stat_nw']:.2f}, "
      f"**DSR over {len(trials)} trials = {dsr:.3f}**. Ann. return {s['ann_return']:.1%}, vol {s['ann_vol']:.1%}, max DD {s['max_dd']:.1%}, "
      f"turnover {s['avg_turnover_per_year']:.0f}x/yr, cost drag {primary.costs.mean() * PPY:.2%}/yr, funding P&L {primary.funding.mean() * PPY:+.2%}/yr.")
yt = stats.yearly_table(r, PPY)[["return", "sharpe", "max_dd"]]
rep.table(yt.T, digits=2, csv="primary_yearly")
longs = backtest_portfolio(close, primary_pos.clip(lower=0), COSTS, funding).returns
shorts = backtest_portfolio(close, primary_pos.clip(upper=0), COSTS, funding).returns
rep.p("Long and short books separately (each 0.5x gross):")
rep.table(summarize_variants({"long_book": longs, "short_book": shorts}, PPY, OOS_START), digits=2)

# Best-looking variant OOS robustness: daily rebalance of the 7d signal (both signs) to see if short-term effects exist
rep.h("Daily rebalance check for the 7-day signal (higher turnover)")
daily = {}
for sign, label in ((1.0, "mom"), (-1.0, "rev")):
    pos = quintile_portfolio(signals["ret_7d"], sign, close.index)
    for c in (Costs(0, 0), COSTS):
        daily[f"{label}_7d_daily_cost{c.fee_bps + c.slippage_bps:.0f}"] = backtest_portfolio(close, pos, c, funding).returns
rep.table(summarize_variants(daily, PPY, OOS_START), digits=2)

print(rep.write().read_text())
