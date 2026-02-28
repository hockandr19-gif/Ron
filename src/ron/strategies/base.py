"""Base class for all trading strategies.

A strategy receives a DataFrame of candles with indicators already applied
and emits Signal objects (BUY / SELL / HOLD).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class Signal:
    side: Side
    symbol: str
    price: float
    # Suggested position size as a fraction of available capital (0–1)
    size_pct: float = 0.0
    # Optional stop-loss and take-profit prices
    stop_loss: float | None = None
    take_profit: float | None = None
    reason: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def is_actionable(self) -> bool:
        return self.side != Side.HOLD


class BaseStrategy(ABC):
    """Subclass this and implement ``generate_signals``."""

    name: str = "base"

    def __init__(self, params: dict[str, Any] | None = None):
        self.params: dict[str, Any] = params or {}

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        """Given a candle DataFrame with indicators, return signals for the latest bar."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(params={self.params})"
