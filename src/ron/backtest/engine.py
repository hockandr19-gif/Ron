"""Event-driven backtesting engine.

Simulates bar-by-bar strategy execution on historical OHLCV data and
produces a detailed trade log plus equity curve.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from rich.console import Console
from rich.table import Table

from ron.strategies.base import BaseStrategy, Side, Signal

console = Console()


@dataclass
class Trade:
    symbol: str
    entry_bar: int
    entry_price: float
    entry_signal: Signal
    exit_bar: int = -1
    exit_price: float = 0.0
    exit_reason: str = ""
    size_usd: float = 0.0

    @property
    def pnl(self) -> float:
        if self.exit_price == 0:
            return 0.0
        return (self.exit_price - self.entry_price) / self.entry_price * self.size_usd

    @property
    def pnl_pct(self) -> float:
        if self.exit_price == 0 or self.entry_price == 0:
            return 0.0
        return (self.exit_price - self.entry_price) / self.entry_price * 100

    @property
    def is_open(self) -> bool:
        return self.exit_bar == -1


@dataclass
class BacktestResult:
    symbol: str
    timeframe: str
    strategy_name: str
    initial_capital: float
    trades: list[Trade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=pd.Series)

    @property
    def closed_trades(self) -> list[Trade]:
        return [t for t in self.trades if not t.is_open]

    @property
    def total_pnl(self) -> float:
        return sum(t.pnl for t in self.closed_trades)

    @property
    def final_equity(self) -> float:
        return self.initial_capital + self.total_pnl

    @property
    def total_return_pct(self) -> float:
        return (self.final_equity / self.initial_capital - 1) * 100

    @property
    def win_rate(self) -> float:
        wins = [t for t in self.closed_trades if t.pnl > 0]
        if not self.closed_trades:
            return 0.0
        return len(wins) / len(self.closed_trades) * 100

    @property
    def max_drawdown_pct(self) -> float:
        if self.equity_curve.empty:
            return 0.0
        roll_max = self.equity_curve.cummax()
        dd = (self.equity_curve - roll_max) / roll_max * 100
        return float(dd.min())

    @property
    def profit_factor(self) -> float:
        gross_profit = sum(t.pnl for t in self.closed_trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in self.closed_trades if t.pnl < 0))
        return gross_profit / gross_loss if gross_loss > 0 else float("inf")

    def sharpe_ratio(self, risk_free_rate: float = 0.0) -> float:
        if self.equity_curve.empty or len(self.equity_curve) < 2:
            return 0.0
        returns = self.equity_curve.pct_change().dropna()
        excess = returns - risk_free_rate / 252
        if excess.std() == 0:
            return 0.0
        return float(excess.mean() / excess.std() * (252**0.5))


def run_backtest(
    df: pd.DataFrame,
    strategy: BaseStrategy,
    symbol: str,
    timeframe: str,
    initial_capital: float = 1000.0,
    position_size_pct: float = 0.10,
    commission_pct: float = 0.006,  # Coinbase taker fee ~0.6%
) -> BacktestResult:
    """Run a full backtest of *strategy* on *df*.

    Args:
        df: OHLCV DataFrame (must have enough bars for indicator warmup).
        strategy: Instantiated strategy to test.
        symbol: Trading pair symbol, e.g. "BTC/USD".
        timeframe: Candle timeframe string.
        initial_capital: Starting capital in USD.
        position_size_pct: Fraction of capital to deploy per trade (0–1).
        commission_pct: Round-trip commission rate.
    """
    result = BacktestResult(
        symbol=symbol,
        timeframe=timeframe,
        strategy_name=strategy.name,
        initial_capital=initial_capital,
    )

    capital = initial_capital
    equity_history: list[float] = []
    open_trade: Trade | None = None

    # Need at least 200 bars for indicator warmup
    warmup = 200
    if len(df) < warmup + 2:
        console.print(f"[yellow]Warning: only {len(df)} bars — need >{warmup} for reliable signals[/yellow]")

    for i in range(warmup, len(df)):
        window = df.iloc[: i + 1]
        curr_bar = df.iloc[i]
        curr_price = float(curr_bar["close"])

        # Check stop-loss / take-profit on open trade
        if open_trade is not None:
            sig = open_trade.entry_signal
            if sig.stop_loss and curr_price <= sig.stop_loss:
                _close_trade(open_trade, i, curr_price, "stop_loss", commission_pct)
                capital += open_trade.pnl
                result.trades.append(open_trade)
                open_trade = None
            elif sig.take_profit and curr_price >= sig.take_profit:
                _close_trade(open_trade, i, curr_price, "take_profit", commission_pct)
                capital += open_trade.pnl
                result.trades.append(open_trade)
                open_trade = None

        signals = strategy.generate_signals(window, symbol)

        for sig in signals:
            if sig.side == Side.BUY and open_trade is None:
                size_usd = capital * position_size_pct * sig.size_pct
                commission = size_usd * commission_pct
                open_trade = Trade(
                    symbol=symbol,
                    entry_bar=i,
                    entry_price=curr_price,
                    entry_signal=sig,
                    size_usd=size_usd - commission,
                )
            elif sig.side == Side.SELL and open_trade is not None:
                _close_trade(open_trade, i, curr_price, sig.reason, commission_pct)
                capital += open_trade.pnl
                result.trades.append(open_trade)
                open_trade = None

        current_equity = capital
        if open_trade is not None:
            unrealized = (curr_price - open_trade.entry_price) / open_trade.entry_price * open_trade.size_usd
            current_equity += unrealized

        equity_history.append(current_equity)

    # Close any remaining open trade at last price
    if open_trade is not None:
        last_price = float(df.iloc[-1]["close"])
        _close_trade(open_trade, len(df) - 1, last_price, "end_of_data", commission_pct)
        capital += open_trade.pnl
        result.trades.append(open_trade)

    result.equity_curve = pd.Series(equity_history, index=df.index[warmup:], name="equity")
    return result


def _close_trade(
    trade: Trade, bar: int, price: float, reason: str, commission_pct: float
) -> None:
    commission = trade.size_usd * commission_pct
    trade.exit_bar = bar
    trade.exit_price = price
    trade.exit_reason = reason
    trade.size_usd -= commission  # deduct exit commission


def print_summary(result: BacktestResult) -> None:
    """Pretty-print backtest results to the terminal."""
    t = Table(title=f"Backtest: {result.strategy_name} | {result.symbol} {result.timeframe}")
    t.add_column("Metric", style="cyan")
    t.add_column("Value", justify="right")

    t.add_row("Initial capital", f"${result.initial_capital:,.2f}")
    t.add_row("Final equity", f"${result.final_equity:,.2f}")
    t.add_row("Total return", f"{result.total_return_pct:+.2f}%")
    t.add_row("Total trades", str(len(result.closed_trades)))
    t.add_row("Win rate", f"{result.win_rate:.1f}%")
    t.add_row("Profit factor", f"{result.profit_factor:.2f}")
    t.add_row("Max drawdown", f"{result.max_drawdown_pct:.2f}%")
    t.add_row("Sharpe ratio", f"{result.sharpe_ratio():.2f}")

    console.print(t)
