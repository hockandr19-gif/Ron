"""Paper trading executor.

Simulates order fills at market price with configurable slippage,
tracking positions and P&L without touching real funds.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from rich.console import Console

from ron.strategies.base import Side, Signal

console = Console()


@dataclass
class Position:
    symbol: str
    entry_price: float
    size_usd: float
    entry_time: datetime = field(default_factory=datetime.utcnow)
    stop_loss: float | None = None
    take_profit: float | None = None

    @property
    def quantity(self) -> float:
        return self.size_usd / self.entry_price

    def unrealized_pnl(self, current_price: float) -> float:
        return (current_price - self.entry_price) / self.entry_price * self.size_usd

    def unrealized_pnl_pct(self, current_price: float) -> float:
        return (current_price - self.entry_price) / self.entry_price * 100


class PaperExecutor:
    """Stateful paper trading book."""

    SLIPPAGE = 0.0005  # 0.05% simulated slippage
    COMMISSION = 0.006  # 0.6% Coinbase taker fee

    def __init__(self, initial_capital: float = 1000.0):
        self.capital = initial_capital
        self.initial_capital = initial_capital
        self.positions: dict[str, Position] = {}
        self.trade_log: list[dict] = []
        self.total_pnl: float = 0.0

    def execute(self, signal: Signal, size_usd: float) -> bool:
        """Process a signal. Returns True if an order was placed."""
        if signal.side == Side.BUY:
            return self._open(signal, size_usd)
        elif signal.side == Side.SELL:
            return self._close(signal)
        return False

    def _open(self, signal: Signal, size_usd: float) -> bool:
        if signal.symbol in self.positions:
            console.print(f"[yellow]Already in position for {signal.symbol}, skipping BUY[/yellow]")
            return False
        if size_usd > self.capital:
            console.print(f"[red]Insufficient capital: need ${size_usd:.2f}, have ${self.capital:.2f}[/red]")
            return False

        fill_price = signal.price * (1 + self.SLIPPAGE)
        commission = size_usd * self.COMMISSION
        net_size = size_usd - commission
        self.capital -= size_usd

        pos = Position(
            symbol=signal.symbol,
            entry_price=fill_price,
            size_usd=net_size,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
        )
        self.positions[signal.symbol] = pos

        console.print(
            f"[green][PAPER BUY ][/green] {signal.symbol} @ ${fill_price:,.4f} "
            f"| size ${net_size:.2f} | reason: {signal.reason}"
        )
        return True

    def _close(self, signal: Signal) -> bool:
        pos = self.positions.pop(signal.symbol, None)
        if pos is None:
            return False

        fill_price = signal.price * (1 - self.SLIPPAGE)
        commission = pos.size_usd * self.COMMISSION
        proceeds = pos.quantity * fill_price - commission
        pnl = proceeds - pos.size_usd
        self.capital += proceeds
        self.total_pnl += pnl

        self.trade_log.append({
            "symbol": signal.symbol,
            "entry": pos.entry_price,
            "exit": fill_price,
            "size_usd": pos.size_usd,
            "pnl": pnl,
            "pnl_pct": pnl / pos.size_usd * 100,
            "reason": signal.reason,
        })

        color = "green" if pnl >= 0 else "red"
        console.print(
            f"[{color}][PAPER SELL][/{color}] {signal.symbol} @ ${fill_price:,.4f} "
            f"| P&L ${pnl:+.2f} ({pnl / pos.size_usd * 100:+.2f}%) | reason: {signal.reason}"
        )
        return True

    @property
    def portfolio_value(self) -> float:
        return self.capital  # Positions valued at cost basis for simplicity

    def status_line(self) -> str:
        return (
            f"Capital ${self.capital:.2f} | "
            f"Total P&L ${self.total_pnl:+.2f} | "
            f"Open positions: {list(self.positions.keys()) or 'none'}"
        )
