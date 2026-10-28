import numpy as np
import pandas as pd

from tvc.live.broker import PaperBroker
from tvc.live.risk import RiskLimits
from tvc.live.bot import Bot
from tvc.strategies.base import MarketData, Strategy


class FakeData:
    """Deterministic stand-in for CcxtData."""
    def __init__(self, prices):
        self.prices = prices
        self.rate = 0.0005
    def fetch_price(self, symbol):
        return self.prices[symbol]
    def amount_to_precision(self, symbol, qty):
        return round(qty, 6)
    def fetch_funding_rate(self, symbol):
        return {"rate": self.rate, "next_time": pd.Timestamp.now(tz="UTC") + pd.Timedelta(hours=1), "interval_hours": 8}
    def fetch_ohlcv(self, symbol, timeframe, limit, drop_incomplete=True):
        idx = pd.date_range(end=pd.Timestamp.now(tz="UTC").floor("h"), periods=limit, freq="h")
        px = np.linspace(self.prices[symbol] * 0.9, self.prices[symbol], limit)
        return pd.DataFrame({"open": px, "high": px, "low": px, "close": px, "volume": 1.0}, index=idx)


class ConstantWeights(Strategy):
    def __init__(self, w):
        super().__init__(w=w)
    def target_positions(self, md):
        return pd.DataFrame([self.params["w"]] * len(md.index), index=md.index)


def test_paper_broker_fill_fee_slippage_and_equity():
    data = FakeData({"BTC/USDT:USDT": 100.0})
    b = PaperBroker(data, cash=1000.0, fee_bps=10, slippage_bps=10)
    fill = b.market_order("BTC/USDT:USDT", 2.0)
    assert fill.price == 100.0 * 1.001 and abs(fill.fee - 2 * 100.1 * 0.001) < 1e-9
    assert abs(b.equity() - (1000 - 2 * 100.1 - fill.fee + 2 * 100.0)) < 1e-9
    b.market_order("BTC/USDT:USDT", -2.0)
    assert b.positions() == {}


def test_paper_funding_charged_once_per_settlement():
    data = FakeData({"BTC/USDT:USDT": 100.0})
    b = PaperBroker(data, cash=1000.0, fee_bps=0, slippage_bps=0)
    b.market_order("BTC/USDT:USDT", 1.0)
    b.last_funding_check["BTC/USDT:USDT"] = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=10)).isoformat()
    paid = b.accrue_funding()
    assert abs(paid - 100.0 * 0.0005) < 1e-12  # long pays positive funding
    assert b.accrue_funding() == 0.0            # not charged twice


def test_bot_rebalances_to_targets_and_respects_limits(tmp_path):
    data = FakeData({"A/USDT:USDT": 10.0, "B/USDT:USDT": 20.0})
    b = PaperBroker(data, cash=10_000.0, fee_bps=0, slippage_bps=0)
    strat = ConstantWeights({"A/USDT:USDT": 2.0, "B/USDT:USDT": -0.2})  # A exceeds per-symbol cap -> clipped to 0.5
    bot = Bot(strat, b, ["A/USDT:USDT", "B/USDT:USDT"], "1h", lookback_bars=50,
              risk=RiskLimits(max_symbol_weight=0.5, max_gross_leverage=1.0), state_path=tmp_path / "s.json")
    out = bot.run_once()
    pos = b.positions()
    assert abs(pos["A/USDT:USDT"] - 0.5 * 10_000 / 10.0) < 1e-6
    assert abs(pos["B/USDT:USDT"] - (-0.2 * 10_000 / 20.0)) < 1e-6
    # second run: no change -> no trades (band)
    out2 = bot.run_once()
    assert out2["fills"] == []
    assert (tmp_path / "s.json").exists()


def test_bot_halts_on_drawdown(tmp_path):
    data = FakeData({"A/USDT:USDT": 10.0})
    b = PaperBroker(data, cash=10_000.0, fee_bps=0, slippage_bps=0)
    bot = Bot(ConstantWeights({"A/USDT:USDT": 1.0}), b, ["A/USDT:USDT"], "1h", lookback_bars=50,
              risk=RiskLimits(max_drawdown=0.2, max_symbol_weight=1.0), state_path=tmp_path / "s.json")
    bot.run_once()
    data.prices["A/USDT:USDT"] = 7.0  # -30%
    out = bot.run_once()
    assert out["halted"] and b.positions() == {} and bot.state.halted
