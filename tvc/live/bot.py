"""The trading loop: data -> strategy -> targets -> risk -> orders -> state.

The strategy is the same object used in the backtests; the bot feeds it a rolling window of bars and takes the
last row of target weights. Runs once per bar close (plus a small delay for the exchange to finalise the candle).
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd

from tvc.config import STATE_DIR
from tvc.live.broker import Broker
from tvc.live.risk import RiskLimits
from tvc.live.state import BotState
from tvc.strategies.base import MarketData, Strategy

log = logging.getLogger(__name__)


class Bot:
    def __init__(self, strategy: Strategy, broker: Broker, symbols: list[str] | None = None, timeframe: str = "1h",
                 lookback_bars: int = 400, risk: RiskLimits | None = None, state_path: Path | None = None,
                 name: str = "bot", feed=None):
        self.strategy, self.broker, self.timeframe = strategy, broker, timeframe
        self.pairs = [tuple(p) for p in strategy.params.get("pairs", [])] or None
        if self.pairs:
            symbols = list(dict.fromkeys([s for pair in self.pairs for s in pair if s]))
        self.symbols = symbols or []
        self.lookback = max(lookback_bars, strategy.warmup_bars() + 5)
        self.risk = risk or RiskLimits()
        self.state_path = Path(state_path or STATE_DIR / f"{name}.json")
        self.state = BotState.load(self.state_path)
        self.name = name
        self.feed = feed
        if self.pairs and self.feed is None:
            from tvc.live.datafeed import DataFeed
            self.feed = DataFeed(broker.data, timeframe=timeframe, lookback_days=getattr(strategy, "lookback_days", 31))

    # ------------------------------------------------------------------ data
    def build_market_data(self) -> MarketData:
        if self.feed is not None and self.pairs:
            return self.feed.market_data(self.pairs)
        frames = {}
        for s in self.symbols:
            try:
                frames[s] = self.broker.data.fetch_ohlcv(s, self.timeframe, self.lookback)
            except Exception as e:
                log.warning("ohlcv failed for %s: %s", s, e)
        if not frames:
            raise RuntimeError("no market data")
        close = pd.DataFrame({s: f["close"] for s, f in frames.items()}).sort_index()
        md = MarketData(
            close=close,
            open=pd.DataFrame({s: f["open"] for s, f in frames.items()}).reindex(close.index),
            high=pd.DataFrame({s: f["high"] for s, f in frames.items()}).reindex(close.index),
            low=pd.DataFrame({s: f["low"] for s, f in frames.items()}).reindex(close.index),
            volume=pd.DataFrame({s: f["volume"] for s, f in frames.items()}).reindex(close.index),
            quote_volume=pd.DataFrame({s: (f["volume"] * f["close"]) for s, f in frames.items()}).reindex(close.index),
        )
        if getattr(self.strategy, "needs_funding", False):
            fund = {}
            for s in self.symbols:
                try:
                    fr = self.broker.data.fetch_funding_rate(s)
                    fund[s] = fr["rate"]
                except Exception as e:
                    log.warning("funding failed for %s: %s", s, e)
            md.funding = pd.DataFrame([fund], index=[close.index[-1]])
        return md

    # ------------------------------------------------------------------ one cycle
    def run_once(self, dry_run: bool = False) -> dict:
        st = self.state
        if st.halted:
            log.warning("bot halted: %s", st.halt_reason)
            return {"halted": True, "reason": st.halt_reason}
        self.broker.accrue_funding()
        equity = self.broker.equity()
        st.record_equity(equity)
        reason = self.risk.breach(equity, st.peak_equity, st.day_start_equity)
        if reason:
            log.error("RISK HALT: %s -> flattening", reason)
            self._flatten(dry_run)
            st.halted, st.halt_reason = True, reason
            st.save(self.state_path)
            return {"halted": True, "reason": reason}

        md = self.build_market_data()
        targets = self.strategy.target_positions(md).iloc[-1]
        targets = self.risk.clip_targets(targets.reindex(self.symbols).fillna(0.0))
        st.targets = {k: float(v) for k, v in targets.items()}
        current = self.broker.positions()
        fills = []
        for s in self.symbols:
            px = float(md.close[s].dropna().iloc[-1]) if s in md.close and md.close[s].notna().any() else None
            if not px:
                continue
            target_qty = targets[s] * equity / px
            cur_qty = current.get(s, 0.0)
            delta = target_qty - cur_qty
            if abs(delta * px) < self.risk.min_trade_notional:
                continue
            if target_qty != 0 and abs(delta) < self.risk.rebalance_band * abs(target_qty):
                continue
            note = f"target_w={targets[s]:+.4f} eq={equity:.2f}"
            if dry_run:
                log.info("DRY RUN order %s qty=%.6f (%s)", s, delta, note)
                continue
            fill = self.broker.market_order(s, delta, note)
            if fill:
                fills.append(fill.to_dict())
        st.trades += fills
        st.trades = st.trades[-5000:]
        st.broker = self.broker.snapshot()
        st.save(self.state_path)
        log.info("cycle done: equity=%.2f gross=%.2f targets=%s fills=%d", equity, targets.abs().sum(),
                 {k: round(v, 3) for k, v in st.targets.items() if v != 0}, len(fills))
        return {"equity": equity, "targets": st.targets, "fills": fills}

    def _flatten(self, dry_run: bool) -> None:
        for s, q in self.broker.positions().items():
            if q != 0 and not dry_run:
                self.broker.market_order(s, -q, "risk flatten")

    # ------------------------------------------------------------------ loop
    def seconds_to_next_bar(self, delay: int = 20) -> float:
        tf = pd.Timedelta(self.timeframe.replace("m", "min") if self.timeframe.endswith("m") else self.timeframe)
        now = pd.Timestamp.now(tz="UTC")
        nxt = (now.floor(tf) + tf) + pd.Timedelta(seconds=delay)
        return max(1.0, (nxt - now).total_seconds())

    def run_forever(self, dry_run: bool = False, run_immediately: bool = True) -> None:
        if run_immediately:
            self._safe_cycle(dry_run)
        while True:
            wait = self.seconds_to_next_bar()
            log.info("sleeping %.0fs until next %s bar", wait, self.timeframe)
            time.sleep(wait)
            self._safe_cycle(dry_run)

    def _safe_cycle(self, dry_run: bool) -> None:
        try:
            self.run_once(dry_run)
        except Exception as e:  # keep the loop alive on transient errors
            log.exception("cycle failed: %s", e)
