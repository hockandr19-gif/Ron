"""Main trading bot loop.

Polls the exchange on each candle close, generates signals, applies risk
checks, and routes orders to either the paper or live executor.
"""
from __future__ import annotations

import time
from datetime import datetime

from rich.console import Console

from ron.config import cfg
from ron.data.fetcher import fetch_ohlcv, Timeframe
from ron.execution.paper import PaperExecutor
from ron.execution.live import LiveExecutor
from ron.execution.risk import RiskManager
from ron.strategies.base import BaseStrategy, Side
from ron.strategies.rsi_macd import RsiMacdStrategy

console = Console()

# Timeframe → seconds per candle
_TF_SECONDS: dict[str, int] = {
    "1m": 60, "5m": 300, "15m": 900,
    "1h": 3600, "4h": 14400, "1d": 86400,
}


def run_bot(
    strategy: BaseStrategy | None = None,
    timeframe: Timeframe = "1h",
    symbols: list[str] | None = None,
    initial_capital: float = 10.0,
    dry_run: bool = False,
) -> None:
    """Start the trading bot.

    Args:
        strategy: Strategy to use. Defaults to RsiMacdStrategy.
        timeframe: Candle interval to trade on.
        symbols: List of symbols. Defaults to cfg.symbols.
        initial_capital: Starting capital in USD. Defaults to $10.
        dry_run: If True, force paper mode regardless of .env setting.
    """
    strategy = strategy or RsiMacdStrategy()
    symbols = symbols or cfg.symbols
    risk = RiskManager()

    # Select executor
    if dry_run or not cfg.is_live:
        executor = PaperExecutor(initial_capital=initial_capital)
        mode_label = "[yellow]PAPER[/yellow]"
    else:
        executor = LiveExecutor()
        mode_label = "[bold red]LIVE[/bold red]"

    console.rule(f"Ron Trading Bot — {mode_label} mode")
    console.print(f"Strategy  : {strategy}")
    console.print(f"Symbols   : {symbols}")
    console.print(f"Timeframe : {timeframe}")
    console.print(f"Capital   : ${initial_capital:.2f}")
    console.print("Press Ctrl+C to stop.\n")

    poll_interval = _TF_SECONDS.get(timeframe, 3600)

    try:
        while True:
            tick_start = time.time()
            console.print(f"[dim]{datetime.utcnow().isoformat()} UTC — polling signals...[/dim]")

            for symbol in symbols:
                try:
                    df = fetch_ohlcv(symbol, timeframe=timeframe, limit=300)
                    signals = strategy.generate_signals(df, symbol)

                    for sig in signals:
                        if not sig.is_actionable:
                            continue

                        portfolio_val = (
                            executor.portfolio_value
                            if hasattr(executor, "portfolio_value") and not callable(executor.portfolio_value)
                            else executor.portfolio_value()
                            if callable(getattr(executor, "portfolio_value", None))
                            else initial_capital
                        )

                        approved, reason = risk.check(portfolio_val, sig)
                        if not approved:
                            console.print(f"[yellow]Risk block ({symbol}): {reason}[/yellow]")
                            continue

                        size_usd = risk.position_size_usd(portfolio_val, sig)
                        placed = executor.execute(sig, size_usd)

                        if placed and sig.side == Side.SELL:
                            # Record approximate P&L for daily limit tracking
                            # (paper executor tracks this internally)
                            pass

                except Exception as exc:
                    console.print(f"[red]Error processing {symbol}: {exc}[/red]")

            if hasattr(executor, "status_line"):
                console.print(executor.status_line())

            elapsed = time.time() - tick_start
            sleep_for = max(0, poll_interval - elapsed)
            console.print(f"[dim]Next poll in {sleep_for:.0f}s[/dim]\n")
            time.sleep(sleep_for)

    except KeyboardInterrupt:
        console.print("\n[bold]Bot stopped.[/bold]")
        if hasattr(executor, "status_line"):
            console.print(executor.status_line())
