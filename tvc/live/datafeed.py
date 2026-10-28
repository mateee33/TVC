"""Incremental local cache of what the edge strategy needs live: 5-minute bars (spot + perp), funding-rate
history and 5-minute open-interest snapshots. Each refresh fetches only what is new, so a cycle costs a handful
of API calls even with a 31-day lookback. Files are parquet under STATE_DIR/feed/."""
from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd

from tvc.config import STATE_DIR
from tvc.live.broker import CcxtData, OHLCV_COLS
from tvc.strategies.base import MarketData

log = logging.getLogger(__name__)


def _safe(symbol: str) -> str:
    return symbol.replace("/", "_").replace(":", "_")


class DataFeed:
    def __init__(self, data: CcxtData, cache_dir: Path | None = None, timeframe: str = "5m", lookback_days: int = 31):
        self.data = data
        self.cache_dir = Path(cache_dir or STATE_DIR / "feed")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeframe = timeframe
        self.lookback_days = lookback_days

    # ------------------------------------------------------------------ helpers
    def _path(self, kind: str, symbol: str) -> Path:
        return self.cache_dir / f"{kind}_{self.timeframe}_{_safe(symbol)}.parquet"

    def _load(self, kind: str, symbol: str) -> pd.DataFrame | None:
        p = self._path(kind, symbol)
        if p.exists():
            try:
                return pd.read_parquet(p)
            except Exception as e:  # corrupt cache -> rebuild
                log.warning("cache %s unreadable (%s); rebuilding", p, e)
        return None

    def _save(self, kind: str, symbol: str, df: pd.DataFrame) -> None:
        p = self._path(kind, symbol)
        tmp = p.with_suffix(".tmp")
        df.to_parquet(tmp)
        tmp.replace(p)

    @property
    def tf_ms(self) -> int:
        return self.data.ex.parse_timeframe(self.timeframe) * 1000

    def _lookback_start_ms(self, now_ms: int) -> int:
        return now_ms - self.lookback_days * 86_400_000

    # ------------------------------------------------------------------ bars
    def ohlcv(self, symbol: str) -> pd.DataFrame:
        cached = self._load("ohlcv", symbol)
        now = self.data.ex.milliseconds()
        tf = self.tf_ms
        since = int(cached.index[-1].value // 1_000_000) + tf if cached is not None and len(cached) else self._lookback_start_ms(now)
        rows: list = []
        while since < now:
            batch = self.data.ex.fetch_ohlcv(symbol, self.timeframe, since=since, limit=300)
            if not batch:
                break
            rows += batch
            nxt = batch[-1][0] + tf
            if nxt <= since:
                break
            since = nxt
            if len(batch) < 2:
                break
        new = pd.DataFrame(rows, columns=["time"] + OHLCV_COLS) if rows else pd.DataFrame(columns=["time"] + OHLCV_COLS)
        if len(new):
            new["time"] = pd.to_datetime(new["time"], unit="ms", utc=True)
            new = new.set_index("time").astype(float)
        df = pd.concat([cached, new]) if cached is not None else new
        df = df[~df.index.duplicated(keep="last")].sort_index()
        last_closed_open = pd.Timestamp((now // tf) * tf - tf, unit="ms", tz="UTC")
        df = df[df.index <= last_closed_open]
        df = df[df.index >= pd.Timestamp(self._lookback_start_ms(now), unit="ms", tz="UTC")]
        self._save("ohlcv", symbol, df)
        return df

    # ------------------------------------------------------------------ funding
    def funding_history(self, symbol: str) -> pd.Series:
        cached = self._load("funding", symbol)
        now = self.data.ex.milliseconds()
        since = int(cached.index[-1].value // 1_000_000) + 1 if cached is not None and len(cached) else self._lookback_start_ms(now)
        rows: list = []
        for _ in range(20):
            batch = self.data.ex.fetch_funding_rate_history(symbol, since=since, limit=100)
            if not batch:
                break
            rows += [(b["timestamp"], float(b["fundingRate"])) for b in batch if b.get("fundingRate") is not None]
            last = batch[-1]["timestamp"]
            if last <= since or len(batch) < 100:
                break
            since = last + 1
        new = pd.DataFrame(rows, columns=["time", "rate"])
        if len(new):
            new["time"] = pd.to_datetime(new["time"], unit="ms", utc=True)
            new = new.set_index("time")
        df = pd.concat([cached, new]) if cached is not None else new
        df = df[~df.index.duplicated(keep="last")].sort_index()
        df = df[df.index >= pd.Timestamp(self._lookback_start_ms(now), unit="ms", tz="UTC")]
        self._save("funding", symbol, df)
        return df["rate"] if len(df) else pd.Series(dtype=float)

    # ------------------------------------------------------------------ open interest
    def open_interest(self, symbol: str) -> pd.Series:
        cached = self._load("oi", symbol)
        now = self.data.ex.milliseconds()
        rows: list = []
        if self.data.ex.has.get("fetchOpenInterestHistory"):
            since = int(cached.index[-1].value // 1_000_000) + 1 if cached is not None and len(cached) else now - 86_400_000
            try:
                hist = self.data.ex.fetch_open_interest_history(symbol, self.timeframe, since=since, limit=200)
                rows += [(h["timestamp"], float(h.get("openInterestAmount") or h.get("openInterestValue") or 0.0)) for h in hist if h.get("timestamp")]
            except Exception as e:
                log.warning("open interest history failed for %s: %s", symbol, e)
        if self.data.ex.has.get("fetchOpenInterest"):
            try:
                cur = self.data.ex.fetch_open_interest(symbol)
                ts = cur.get("timestamp") or now
                rows.append((int(ts // self.tf_ms * self.tf_ms), float(cur.get("openInterestAmount") or cur.get("openInterestValue") or 0.0)))
            except Exception as e:
                log.warning("open interest failed for %s: %s", symbol, e)
        new = pd.DataFrame(rows, columns=["time", "oi"])
        if len(new):
            new["time"] = pd.to_datetime(new["time"], unit="ms", utc=True)
            new = new[new.oi > 0].set_index("time")
        df = pd.concat([cached, new]) if cached is not None else new
        df = df[~df.index.duplicated(keep="last")].sort_index()
        df = df[df.index >= pd.Timestamp(self._lookback_start_ms(now), unit="ms", tz="UTC")]
        self._save("oi", symbol, df)
        return df["oi"] if len(df) else pd.Series(dtype=float)

    # ------------------------------------------------------------------ assemble
    def market_data(self, pairs: list[tuple[str | None, str]]) -> MarketData:
        perps = [p for _, p in pairs]
        spots = [s for s, _ in pairs if s]
        frames = {sym: self.ohlcv(sym) for sym in perps + spots}
        index = frames[perps[0]].index
        for p in perps[1:]:
            index = index.union(frames[p].index)
        close = pd.DataFrame({sym: f["close"].reindex(index) for sym, f in frames.items()})
        volume = pd.DataFrame({sym: f["volume"].reindex(index) for sym, f in frames.items()})
        fund = {}
        oi = {}
        step = pd.Timedelta(milliseconds=self.tf_ms)
        for p in perps:
            try:
                fund[p] = self.funding_history(p)
            except Exception as e:
                log.warning("funding history failed for %s: %s", p, e)
            try:
                s = self.open_interest(p)
                # value known at each bar's close (= next open time); fall back to the latest available
                aligned = s.reindex(index + step, method="nearest", tolerance=step).to_numpy()
                oi[p] = pd.Series(aligned, index=index).ffill(limit=12)
            except Exception as e:
                log.warning("open interest failed for %s: %s", p, e)
        funding = pd.DataFrame(fund) if fund else None
        if funding is not None:
            funding = funding.sort_index()
        return MarketData(close=close, volume=volume, quote_volume=volume * close, funding=funding,
                          open_interest=pd.DataFrame(oi) if oi else None)
