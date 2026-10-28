"""Persistent bot state (JSON): equity curve, trades, risk flags and the paper account."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

import pandas as pd


@dataclass
class BotState:
    equity_curve: list = field(default_factory=list)      # [[iso_ts, equity], ...]
    trades: list = field(default_factory=list)            # Fill dicts
    targets: dict = field(default_factory=dict)           # last target weights
    peak_equity: float = 0.0
    day: str = ""
    day_start_equity: float = 0.0
    halted: bool = False
    halt_reason: str = ""
    broker: dict = field(default_factory=dict)            # PaperBroker snapshot
    last_run: str = ""

    @classmethod
    def load(cls, path: Path) -> "BotState":
        if Path(path).exists():
            return cls(**json.loads(Path(path).read_text()))
        return cls()

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=1, default=str))
        tmp.replace(path)

    def record_equity(self, equity: float) -> None:
        now = pd.Timestamp.now(tz="UTC")
        self.equity_curve.append([now.isoformat(), float(equity)])
        self.equity_curve = self.equity_curve[-20000:]
        self.peak_equity = max(self.peak_equity, float(equity))
        today = now.strftime("%Y-%m-%d")
        if self.day != today:
            self.day, self.day_start_equity = today, float(equity)
        self.last_run = now.isoformat()
