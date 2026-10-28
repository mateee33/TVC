"""Bulk-download everything the research studies need. Safe to re-run (cached)."""
from __future__ import annotations

import logging
import sys
import time

from tvc.data import BinanceVision, list_um_symbols

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("download")

MAJORS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT",
    "LINKUSDT", "DOTUSDT", "MATICUSDT", "POLUSDT", "LTCUSDT", "BCHUSDT", "UNIUSDT", "ATOMUSDT",
    "NEARUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "SUIUSDT", "TRXUSDT", "FILUSDT", "ETCUSDT",
    "XLMUSDT", "INJUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "1000PEPEUSDT", "WIFUSDT", "TONUSDT",
    "ICPUSDT", "HBARUSDT", "RENDERUSDT", "FETUSDT", "ORDIUSDT", "1000SHIBUSDT", "ENAUSDT",
    "WLDUSDT", "JUPUSDT", "TAOUSDT", "ALGOUSDT", "SANDUSDT", "AXSUSDT", "EOSUSDT", "GALAUSDT",
]
OI_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

def stage(name):
    def deco(fn):
        def wrapper(*a, **k):
            t = time.time()
            log.info("=== stage %s start", name)
            fn(*a, **k)
            log.info("=== stage %s done in %.0fs", name, time.time() - t)
        return wrapper
    return deco

bv = BinanceVision(workers=16)

@stage("A funding all perps")
def stage_a(symbols):
    bv.prefetch(symbols, "fundingRate", "um")
    for i, s in enumerate(symbols):
        bv.funding(s)
        if i % 100 == 0: log.info("assembled funding %d/%d", i, len(symbols))

@stage("B daily klines all perps")
def stage_b(symbols):
    bv.prefetch(symbols, "klines", "um", "1d")
    for i, s in enumerate(symbols):
        bv.klines(s, "1d", "um")
        if i % 100 == 0: log.info("assembled 1d %d/%d", i, len(symbols))

@stage("C hourly klines majors")
def stage_c():
    bv.prefetch(MAJORS, "klines", "um", "1h")
    for s in MAJORS: bv.klines(s, "1h", "um")

@stage("D spot hourly BTC/ETH + spot daily majors")
def stage_d():
    for s in ["BTCUSDT", "ETHUSDT"]:
        bv.klines(s, "1h", "spot")
    bv.prefetch(MAJORS, "klines", "spot", "1d")
    for s in MAJORS: bv.klines(s, "1d", "spot")

@stage("E premium index + open-interest metrics + 5m klines (perp and spot) for the edge symbols")
def stage_e():
    for s in ["BTCUSDT", "ETHUSDT"]:
        bv.premium_index(s, "1h")
    for s in OI_SYMBOLS:
        bv.klines(s, "5m", "um")
        bv.klines(s, "5m", "spot")
        bv.metrics(s)

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ABCDE"
    syms = list_um_symbols("USDT")
    log.info("%d USDT perp symbols", len(syms))
    if "A" in which: stage_a(syms)
    if "B" in which: stage_b(syms)
    if "C" in which: stage_c()
    if "D" in which: stage_d()
    if "E" in which: stage_e()
    log.info("ALL DONE")
