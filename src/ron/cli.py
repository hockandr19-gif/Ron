"""Command-line entry points for Ron."""
from __future__ import annotations

import click
from rich.console import Console

console = Console()


@click.command()
@click.option("--symbol", "-s", default=None, help="Symbol to backtest, e.g. BTC/USD")
@click.option("--timeframe", "-t", default="1h", show_default=True,
              type=click.Choice(["1m", "5m", "15m", "1h", "4h", "1d"]))
@click.option("--candles", "-n", default=500, show_default=True, help="Number of candles to fetch")
@click.option("--capital", "-c", default=1000.0, show_default=True, help="Initial capital in USD")
@click.option("--pos-size", default=0.10, show_default=True,
              help="Position size as fraction of capital (0–1)")
def backtest(symbol, timeframe, candles, capital, pos_size):
    """Backtest the default RSI/MACD strategy on historical data."""
    from ron.config import cfg
    from ron.data.fetcher import fetch_ohlcv
    from ron.strategies.rsi_macd import RsiMacdStrategy
    from ron.backtest.engine import run_backtest, print_summary

    symbols = [symbol] if symbol else cfg.symbols

    for sym in symbols:
        console.print(f"\nFetching {candles} {timeframe} candles for [bold]{sym}[/bold]...")
        df = fetch_ohlcv(sym, timeframe=timeframe, limit=candles)
        result = run_backtest(
            df,
            strategy=RsiMacdStrategy(),
            symbol=sym,
            timeframe=timeframe,
            initial_capital=capital,
            position_size_pct=pos_size,
        )
        print_summary(result)


@click.command()
@click.option("--symbol", "-s", default=None, multiple=True, help="Symbols to trade")
@click.option("--timeframe", "-t", default="1h", show_default=True,
              type=click.Choice(["1m", "5m", "15m", "1h", "4h", "1d"]))
@click.option("--capital", "-c", default=10.0, show_default=True,
              help="Starting capital in USD (default $10)")
@click.option("--live", is_flag=True, default=False,
              help="Use real money (requires TRADING_MODE=live in .env)")
def trade(symbol, timeframe, capital, live):
    """Run the trading bot (paper by default, --live for real orders)."""
    from ron.config import cfg
    from ron.execution.bot import run_bot
    from ron.strategies.rsi_macd import RsiMacdStrategy

    symbols = list(symbol) if symbol else cfg.symbols
    dry_run = not live

    if live:
        click.confirm(
            f"[WARNING] You are about to trade with REAL MONEY on {symbols}. Continue?",
            abort=True,
        )

    run_bot(
        strategy=RsiMacdStrategy(),
        timeframe=timeframe,
        symbols=symbols,
        initial_capital=capital,
        dry_run=dry_run,
    )


@click.command()
def dashboard():
    """Launch the Streamlit signals dashboard."""
    import subprocess
    import sys
    from pathlib import Path

    app_path = Path(__file__).parent / "dashboard" / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)], check=True)
