"""Execution and market-data adapters.

* `CcxtData`    - public market data from any ccxt exchange (no API keys).
* `PaperBroker` - simulated fills, fees, slippage and funding on top of live market data.
* `CcxtBroker`  - real orders through ccxt (needs API keys). Same interface, so the bot code is identical.
Symbols are ccxt unified symbols, e.g. 'BTC/USDT:USDT' for a USDT-margined perpetual.
"""
from __future__ import annotations

import logging
import math
import os
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass

import pandas as pd

log = logging.getLogger(__name__)

OHLCV_COLS = ["open", "high", "low", "close", "volume"]


@dataclass
class Fill:
    symbol: str
    qty: float            # signed: + buy, - sell
    price: float
    fee: float
    ts: str
    order_id: str = ""
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _ccxt_options() -> dict:
    """Pick up a corporate / sandbox proxy and CA bundle from the environment if present (ccxt needs them explicitly)."""
    opts = {}
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        opts["httpsProxy"] = proxy
    ca = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
    if ca:
        opts["verify"] = ca
    return opts


def make_exchange(exchange_id: str, api_key: str | None = None, secret: str | None = None, password: str | None = None,
                  wallet: str | None = None, sandbox: bool = False, options: dict | None = None):
    import ccxt
    cfg = {"enableRateLimit": True, "timeout": 30000, **_ccxt_options(), **(options or {})}
    if api_key:
        cfg["apiKey"] = api_key
    if secret:
        cfg["secret"] = secret
    if password:
        cfg["password"] = password
    if wallet:  # e.g. hyperliquid uses walletAddress + privateKey(secret)
        cfg["walletAddress"] = wallet
    ex = getattr(ccxt, exchange_id)(cfg)
    if sandbox:
        ex.set_sandbox_mode(True)
    ex.load_markets()
    return ex


class CcxtData:
    """Public market data via ccxt. Handles pagination so `limit` can exceed the exchange page size."""

    def __init__(self, exchange_id: str = "okx", exchange=None, options: dict | None = None):
        self.ex = exchange or make_exchange(exchange_id, options=options)

    def fetch_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 500, drop_incomplete: bool = True) -> pd.DataFrame:
        tf_ms = self.ex.parse_timeframe(timeframe) * 1000
        now = self.ex.milliseconds()
        since = now - (limit + 1) * tf_ms
        rows: list = []
        page = 300
        while since < now:
            batch = self.ex.fetch_ohlcv(symbol, timeframe, since=since, limit=page)
            if not batch:
                break
            rows += batch
            nxt = batch[-1][0] + tf_ms
            if nxt <= since or len(batch) < 2:
                break
            since = nxt
        if not rows:
            return pd.DataFrame(columns=OHLCV_COLS)
        df = pd.DataFrame(rows, columns=["time"] + OHLCV_COLS).drop_duplicates("time").sort_values("time")
        df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True)
        df = df.set_index("time").astype(float)
        if drop_incomplete:
            last_closed_open = pd.Timestamp((now // tf_ms) * tf_ms - tf_ms, unit="ms", tz="UTC")
            df = df[df.index <= last_closed_open]
        return df.iloc[-limit:]

    def fetch_funding_rate(self, symbol: str) -> dict:
        if not self.ex.has.get("fetchFundingRate"):
            return {"rate": 0.0, "next_time": None, "interval_hours": 8}
        fr = self.ex.fetch_funding_rate(symbol)
        interval = fr.get("interval") or "8h"
        hours = int(str(interval).rstrip("h")) if str(interval).endswith("h") else 8
        nxt = fr.get("fundingTimestamp")
        return {"rate": float(fr.get("fundingRate") or 0.0),
                "next_time": pd.Timestamp(nxt, unit="ms", tz="UTC") if nxt else None, "interval_hours": hours}

    def fetch_price(self, symbol: str) -> float:
        t = self.ex.fetch_ticker(symbol)
        return float(t.get("last") or t.get("close") or t["info"].get("last"))

    def market(self, symbol: str) -> dict:
        return self.ex.market(symbol)

    def contract_size(self, symbol: str) -> float:
        try:
            return float(self.ex.market(symbol).get("contractSize") or 1.0)
        except Exception:
            return 1.0

    def to_contracts(self, symbol: str, qty_base: float) -> float:
        """Base-currency quantity -> exchange order amount (contracts), rounded to the market's precision."""
        cs = self.contract_size(symbol)
        try:
            amt = float(self.ex.amount_to_precision(symbol, abs(qty_base) / cs))
        except Exception:
            amt = abs(qty_base) / cs
        return amt if qty_base >= 0 else -amt

    def amount_to_precision(self, symbol: str, qty: float) -> float:
        """Round a base-currency quantity to what the exchange can actually fill."""
        return self.to_contracts(symbol, qty) * self.contract_size(symbol)


class Broker(ABC):
    data: CcxtData

    @abstractmethod
    def equity(self) -> float: ...

    @abstractmethod
    def positions(self) -> dict[str, float]:
        """symbol -> signed quantity in base units."""

    @abstractmethod
    def market_order(self, symbol: str, qty: float, note: str = "") -> Fill | None: ...

    def accrue_funding(self) -> float:
        return 0.0

    def snapshot(self) -> dict:
        return {}


class PaperBroker(Broker):
    """Simulated account. Fills at the live last price +/- slippage; fees in bps of notional; funding accrued at
    settlement times from the exchange's current funding rate (longs pay when positive)."""

    def __init__(self, data: CcxtData, cash: float = 10_000.0, fee_bps: float = 5.0, slippage_bps: float = 2.0,
                 state: dict | None = None):
        self.data = data
        self.fee_bps, self.slippage_bps = fee_bps, slippage_bps
        st = state or {}
        self.cash = float(st.get("cash", cash))
        self.pos: dict[str, float] = {k: float(v) for k, v in st.get("positions", {}).items()}
        self.realized = float(st.get("realized", 0.0))
        self.fees_paid = float(st.get("fees_paid", 0.0))
        self.funding_paid = float(st.get("funding_paid", 0.0))
        self.last_funding_check: dict[str, str] = st.get("last_funding_check", {})
        self._prices: dict[str, float] = {}

    def price(self, symbol: str) -> float:
        p = self.data.fetch_price(symbol)
        self._prices[symbol] = p
        return p

    def equity(self) -> float:
        return self.cash + sum(q * self.price(s) for s, q in self.pos.items() if q != 0)

    def positions(self) -> dict[str, float]:
        return {s: q for s, q in self.pos.items() if q != 0}

    def market_order(self, symbol: str, qty: float, note: str = "") -> Fill | None:
        if qty == 0:
            return None
        qty = self.data.amount_to_precision(symbol, qty)
        if qty == 0:
            return None
        mid = self.price(symbol)
        px = mid * (1 + math.copysign(self.slippage_bps / 1e4, qty))
        fee = abs(qty) * px * self.fee_bps / 1e4
        self.cash -= qty * px + fee
        self.fees_paid += fee
        self.pos[symbol] = self.pos.get(symbol, 0.0) + qty
        if abs(self.pos[symbol]) < 1e-12:
            self.pos[symbol] = 0.0
        fill = Fill(symbol, qty, px, fee, pd.Timestamp.now(tz="UTC").isoformat(), f"paper-{int(time.time() * 1000)}", note)
        log.info("PAPER FILL %s qty=%.6f px=%.4f fee=%.4f %s", symbol, qty, px, fee, note)
        return fill

    def accrue_funding(self) -> float:
        """Charge funding for every settlement that passed since the last check. Returns total paid (negative = received)."""
        total = 0.0
        now = pd.Timestamp.now(tz="UTC")
        for symbol, q in list(self.pos.items()):
            if q == 0 or ":" not in symbol:  # spot positions do not pay funding
                continue
            fr = self.data.fetch_funding_rate(symbol)
            if fr["next_time"] is None:
                continue
            interval = pd.Timedelta(hours=fr["interval_hours"])
            last_settle = fr["next_time"] - interval  # most recent settlement time
            prev = self.last_funding_check.get(symbol)
            prev_ts = pd.Timestamp(prev) if prev else now
            if prev and last_settle > prev_ts and last_settle <= now:
                paid = q * self.price(symbol) * fr["rate"]  # long pays positive funding
                self.cash -= paid
                self.funding_paid += paid
                total += paid
                log.info("PAPER FUNDING %s qty=%.6f rate=%.6f paid=%.4f", symbol, q, fr["rate"], paid)
            self.last_funding_check[symbol] = now.isoformat()
        return total

    def snapshot(self) -> dict:
        return {"cash": self.cash, "positions": self.pos, "realized": self.realized, "fees_paid": self.fees_paid,
                "funding_paid": self.funding_paid, "last_funding_check": self.last_funding_check}


class CcxtBroker(Broker):
    """Live execution through ccxt. Market orders only; positions read back from the exchange every cycle so the
    bot never relies on its own bookkeeping. `quote` is the settlement currency for the equity figure."""

    def __init__(self, exchange, quote: str = "USDT"):
        self.ex = exchange
        self.data = CcxtData(exchange=exchange)
        self.quote = quote

    def equity(self) -> float:
        bal = self.ex.fetch_balance()
        total = bal.get("total", {})
        if self.quote in total and total[self.quote] is not None:
            eq = float(total[self.quote])
        else:  # some exchanges report account equity in info
            eq = float(bal.get("info", {}).get("marginSummary", {}).get("accountValue", 0.0))
        return eq

    def positions(self) -> dict[str, float]:
        out = {}
        for p in self.ex.fetch_positions():
            qty = float(p.get("contracts") or 0.0) * float(p.get("contractSize") or 1.0)
            if qty == 0:
                continue
            side = p.get("side")
            out[p["symbol"]] = qty if side == "long" else -qty
        return out

    def market_order(self, symbol: str, qty: float, note: str = "") -> Fill | None:
        if qty == 0:
            return None
        contracts = abs(self.data.to_contracts(symbol, qty))  # exchanges size perp orders in contracts
        if contracts == 0:
            return None
        side = "buy" if qty > 0 else "sell"
        order = self.ex.create_order(symbol, "market", side, contracts)
        px = float(order.get("average") or order.get("price") or self.data.fetch_price(symbol))
        fee = float((order.get("fee") or {}).get("cost") or 0.0)
        filled_base = float(order.get("filled") or contracts) * self.data.contract_size(symbol)
        fill = Fill(symbol, math.copysign(filled_base, qty), px, fee, pd.Timestamp.now(tz="UTC").isoformat(), str(order.get("id")), note)
        log.info("LIVE FILL %s", fill)
        return fill
