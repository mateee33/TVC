import numpy as np
import pandas as pd

from tvc.live.datafeed import DataFeed


class FakeEx:
    """Minimal ccxt look-alike with 5m bars, funding history and open interest."""
    has = {"fetchOpenInterestHistory": True, "fetchOpenInterest": True, "fetchFundingRateHistory": True}

    def __init__(self, now_ms):
        self.now = now_ms
        self.calls = 0

    def milliseconds(self):
        return self.now

    def parse_timeframe(self, tf):
        return 300

    def fetch_ohlcv(self, symbol, timeframe, since=None, limit=300):
        self.calls += 1
        tf = 300_000
        start = (since // tf) * tf
        out = []
        t = start
        while t <= self.now and len(out) < limit:
            px = 100 + (t // tf) % 50
            out.append([t, px, px, px, px, 1.0])
            t += tf
        return out

    def fetch_funding_rate_history(self, symbol, since=None, limit=100):
        t0 = (since // 28_800_000 + 1) * 28_800_000
        return [{"timestamp": t, "fundingRate": 0.0001} for t in range(t0, self.now, 28_800_000)][:limit]

    def fetch_open_interest_history(self, symbol, timeframe, since=None, limit=200):
        return [{"timestamp": t, "openInterestAmount": 1000.0} for t in range(since // 300_000 * 300_000, self.now, 300_000)][:limit]

    def fetch_open_interest(self, symbol):
        return {"timestamp": self.now, "openInterestAmount": 1001.0}


class FakeData:
    def __init__(self, ex):
        self.ex = ex


def test_feed_builds_market_data_and_is_incremental(tmp_path):
    now = int(pd.Timestamp("2026-01-10 12:03:20", tz="UTC").value // 1_000_000)
    ex = FakeEx(now)
    feed = DataFeed(FakeData(ex), cache_dir=tmp_path, timeframe="5m", lookback_days=2)
    md = feed.market_data([("BTC/USDT", "BTC/USDT:USDT")])
    assert md.close.index[-1] == pd.Timestamp("2026-01-10 11:55", tz="UTC")  # last fully closed 5m bar
    assert len(md.close) == 2 * 288 - 1 or len(md.close) == 2 * 288
    assert set(md.close.columns) == {"BTC/USDT", "BTC/USDT:USDT"}
    assert md.funding is not None and md.funding["BTC/USDT:USDT"].dropna().iloc[-1] == 0.0001
    assert md.open_interest is not None and md.open_interest["BTC/USDT:USDT"].notna().sum() > 0
    calls = ex.calls
    # 10 minutes later: only the new bars are fetched (one small call per symbol)
    ex.now = now + 600_000
    md2 = feed.market_data([("BTC/USDT", "BTC/USDT:USDT")])
    assert md2.close.index[-1] == pd.Timestamp("2026-01-10 12:05", tz="UTC")
    assert ex.calls - calls <= 2
