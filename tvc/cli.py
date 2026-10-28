"""Command-line entry point: `tvc download | backtest | run | status`."""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import pandas as pd

from tvc.config import STATE_DIR

log = logging.getLogger("tvc")

STRATEGIES = {}


def _register():
    from tvc.strategies.tsmom import TSMom
    STRATEGIES["tsmom"] = TSMom
    try:
        from tvc.strategies.edge import FundingRebound, CascadeReversal, EdgeCombo
        STRATEGIES["funding_rebound"] = FundingRebound
        STRATEGIES["cascade"] = CascadeReversal
        STRATEGIES["edge"] = EdgeCombo
    except ImportError:
        pass


def _parse_kv(items: list[str] | None) -> dict:
    out = {}
    for it in items or []:
        k, v = it.split("=", 1)
        try:
            out[k] = json.loads(v)
        except json.JSONDecodeError:
            out[k] = v
    return out


def cmd_download(args):
    import subprocess
    stages = args.stages or "ABCDE"
    subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "research" / "00_download.py"), stages], check=True)


def cmd_research(args):
    """Run the research studies in order (each writes reports/<study>.md)."""
    import subprocess
    root = Path(__file__).resolve().parents[1] / "research"
    scripts = sorted(p for p in root.glob("0[1-9]_*.py"))
    if args.only:
        scripts = [p for p in scripts if any(p.name.startswith(o) for o in args.only)]
    for p in scripts:
        log.info("running %s", p.name)
        subprocess.run([sys.executable, str(p)], check=True, stdout=subprocess.DEVNULL if args.quiet else None)


def cmd_backtest(args):
    from tvc.backtest import Costs, backtest_portfolio, stats
    from tvc.research.common import bv
    from tvc.strategies.base import MarketData
    strat = STRATEGIES[args.strategy](**_parse_kv(args.param))
    syms = args.symbols
    close = bv.load_many(syms, args.timeframe, "um", "close")
    qv = bv.load_many(syms, args.timeframe, "um", "quote_volume")
    funding = bv.funding_many(syms)
    md = MarketData(close=close, quote_volume=qv, funding=funding)
    pos = strat.target_positions(md)
    res = backtest_portfolio(close, pos, Costs(args.fee_bps, args.slippage_bps), funding)
    ppy = stats.infer_periods_per_year(close.index)
    s = res.summary(ppy, n_boot=500)
    print(f"\n{strat}  symbols={syms}  {close.index[0]:%Y-%m-%d} -> {close.index[-1]:%Y-%m-%d}")
    for k in ("sharpe", "ann_return", "ann_vol", "max_dd", "t_stat_nw", "psr_0", "boot_ci_low", "boot_ci_high", "avg_gross_exposure", "avg_turnover_per_year"):
        print(f"  {k:24s} {s[k]:.3f}")
    print(stats.yearly_table(res.returns, ppy).round(3).to_string())


def _make_broker(args):
    from tvc.live.broker import CcxtData, PaperBroker, CcxtBroker, make_exchange
    from tvc.live.state import BotState
    if args.live:
        key = os.environ.get("TVC_API_KEY"); secret = os.environ.get("TVC_API_SECRET")
        password = os.environ.get("TVC_API_PASSWORD"); wallet = os.environ.get("TVC_WALLET")
        if not (key or wallet) or not secret:
            sys.exit("live mode needs TVC_API_KEY/TVC_API_SECRET (or TVC_WALLET/TVC_API_SECRET) in the environment")
        ex = make_exchange(args.exchange, key, secret, password, wallet, sandbox=args.sandbox)
        return CcxtBroker(ex, quote=args.quote)
    data = CcxtData(args.exchange)
    st = BotState.load(STATE_DIR / f"{args.name}.json")
    return PaperBroker(data, cash=args.cash, fee_bps=args.fee_bps, slippage_bps=args.slippage_bps, state=st.broker or None)


def cmd_run(args):
    from tvc.live.bot import Bot
    from tvc.live.risk import RiskLimits
    params = _parse_kv(args.param)
    if args.pair:
        params["pairs"] = [[(a or None), b] for a, b in (pr.split(",", 1) for pr in args.pair)]
    strat = STRATEGIES[args.strategy](**params)
    broker = _make_broker(args)
    risk = RiskLimits(max_gross_leverage=args.max_gross, max_symbol_weight=args.max_weight,
                      max_daily_loss=args.max_daily_loss, max_drawdown=args.max_drawdown)
    bot = Bot(strat, broker, args.symbols, args.timeframe, lookback_bars=args.lookback, risk=risk, name=args.name)
    mode = "LIVE" if args.live else "PAPER"
    log.info("%s mode on %s, strategy %s, symbols %s, timeframe %s", mode, args.exchange, strat, bot.symbols, args.timeframe)
    if args.once:
        out = bot.run_once(dry_run=args.dry_run)
        print(json.dumps(out, indent=1, default=str))
    else:
        bot.run_forever(dry_run=args.dry_run)


def cmd_status(args):
    from tvc.live.state import BotState
    st = BotState.load(STATE_DIR / f"{args.name}.json")
    if not st.equity_curve:
        print("no state yet"); return
    eq = pd.DataFrame(st.equity_curve, columns=["time", "equity"]).set_index("time")
    print(f"last run: {st.last_run}  equity: {eq.equity.iloc[-1]:.2f}  peak: {st.peak_equity:.2f}  halted: {st.halted} {st.halt_reason}")
    print("targets:", {k: round(v, 4) for k, v in st.targets.items() if v})
    print("positions:", st.broker.get("positions"))
    print(f"trades: {len(st.trades)}  fees paid: {st.broker.get('fees_paid', 0):.4f}  funding paid: {st.broker.get('funding_paid', 0):.4f}")
    for t in st.trades[-10:]:
        print("  ", t)


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    _register()
    p = argparse.ArgumentParser(prog="tvc", description="TVC research-driven crypto trading bot")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("download", help="download research data from the Binance public archive")
    d.add_argument("--stages", default="ABCDE", help="subset of ABCDE (A funding, B daily klines all perps, C hourly majors, D spot, E OI/5m)")
    d.set_defaults(fn=cmd_download)

    rs = sub.add_parser("research", help="run the research studies (writes reports/*.md)")
    rs.add_argument("--only", nargs="*", help="study number prefixes, e.g. 02 07")
    rs.add_argument("--quiet", action="store_true")
    rs.set_defaults(fn=cmd_research)

    b = sub.add_parser("backtest", help="backtest a strategy on cached archive data")
    b.add_argument("--strategy", required=True, choices=sorted(STRATEGIES))
    b.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT", "SOLUSDT"])
    b.add_argument("--timeframe", default="1d")
    b.add_argument("--fee-bps", type=float, default=5.0)
    b.add_argument("--slippage-bps", type=float, default=2.0)
    b.add_argument("--param", "-p", action="append", help="strategy param key=value (JSON values)")
    b.set_defaults(fn=cmd_backtest)

    r = sub.add_parser("run", help="run the bot (paper by default)")
    r.add_argument("--strategy", required=True, choices=sorted(STRATEGIES))
    r.add_argument("--exchange", default="okx", help="ccxt exchange id (okx, hyperliquid, bybit, binanceusdm, krakenfutures, ...)")
    r.add_argument("--symbols", nargs="+", default=["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"])
    r.add_argument("--pair", action="append", help="SPOT,PERP pair for the edge/carry strategies, e.g. BTC/USDT,BTC/USDT:USDT "
                   "(leave SPOT empty for a perp-only account: ,BTC/USDT:USDT). Repeat per pair.")
    r.add_argument("--timeframe", default="1h")
    r.add_argument("--lookback", type=int, default=400)
    r.add_argument("--param", "-p", action="append")
    r.add_argument("--name", default="bot", help="state file name")
    r.add_argument("--cash", type=float, default=10_000.0, help="paper starting cash")
    r.add_argument("--fee-bps", type=float, default=5.0)
    r.add_argument("--slippage-bps", type=float, default=2.0)
    r.add_argument("--quote", default="USDT")
    r.add_argument("--max-gross", type=float, default=2.5, help="sum of |weights| (carry uses 2x when all pairs are on)")
    r.add_argument("--max-weight", type=float, default=0.6)
    r.add_argument("--max-daily-loss", type=float, default=0.05)
    r.add_argument("--max-drawdown", type=float, default=0.25)
    r.add_argument("--live", action="store_true", help="send real orders (needs TVC_API_KEY/TVC_API_SECRET)")
    r.add_argument("--sandbox", action="store_true", help="use the exchange testnet")
    r.add_argument("--once", action="store_true", help="run a single cycle and exit")
    r.add_argument("--dry-run", action="store_true", help="compute targets and log orders without placing them")
    r.set_defaults(fn=cmd_run)

    s = sub.add_parser("status", help="show bot state")
    s.add_argument("--name", default="bot")
    s.set_defaults(fn=cmd_status)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
