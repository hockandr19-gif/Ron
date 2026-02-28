"""Risk management guard.

All orders must pass through RiskManager before reaching the exchange.
Enforces position size caps, daily loss limits, and other guardrails.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ron.config import cfg
from ron.strategies.base import Signal


@dataclass
class RiskManager:
    max_position_usd: float = field(default_factory=lambda: cfg.max_position_usd)
    max_daily_loss_usd: float = field(default_factory=lambda: cfg.max_daily_loss_usd)
    risk_per_trade_pct: float = field(default_factory=lambda: cfg.risk_per_trade_pct)

    _daily_pnl: float = 0.0
    _day: date = field(default_factory=date.today)

    def record_pnl(self, pnl: float) -> None:
        today = date.today()
        if today != self._day:
            self._daily_pnl = 0.0
            self._day = today
        self._daily_pnl += pnl

    @property
    def trading_halted(self) -> bool:
        """True when daily loss limit has been breached."""
        return self._daily_pnl <= -self.max_daily_loss_usd

    def position_size_usd(self, portfolio_value: float, signal: Signal) -> float:
        """Return the dollar amount to deploy for *signal*, respecting all limits."""
        if self.trading_halted:
            return 0.0
        raw = portfolio_value * self.risk_per_trade_pct * signal.size_pct
        return min(raw, self.max_position_usd)

    def check(self, portfolio_value: float, signal: Signal) -> tuple[bool, str]:
        """Return (approved, reason). Call before placing any order."""
        if self.trading_halted:
            return False, f"Daily loss limit hit (P&L ${self._daily_pnl:.2f})"
        size = self.position_size_usd(portfolio_value, signal)
        if size <= 0:
            return False, "Position size calculated to $0"
        return True, ""
