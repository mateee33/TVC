"""Central configuration: paths and default cost assumptions."""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("TVC_DATA_DIR", REPO_ROOT / "data"))
REPORTS_DIR = Path(os.environ.get("TVC_REPORTS_DIR", REPO_ROOT / "reports"))
STATE_DIR = Path(os.environ.get("TVC_STATE_DIR", REPO_ROOT / "state"))

# Default trading-cost assumptions (per side, in basis points of notional traded).
# Binance USD-M perps: taker 5 bps / maker 2 bps. We add slippage on top.
PERP_TAKER_FEE_BPS = 5.0
PERP_MAKER_FEE_BPS = 2.0
SPOT_TAKER_FEE_BPS = 10.0
DEFAULT_SLIPPAGE_BPS = 2.0

# Research split: everything before this date is in-sample, after is out-of-sample.
OOS_START = "2024-01-01"

for _d in (DATA_DIR, REPORTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
