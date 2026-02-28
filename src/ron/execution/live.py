"""Live trading executor via Coinbase Advanced Trade API (ccxt).

WARNING: This places real orders with real money.
         Only activated when TRADING_MODE=live in .env.
         Defaults are intentionally conservative ($10 max per trade).
"""
from __future__ import annotations

import ccxt
from rich.console import Console

from ron.config import cfg
from ron.strategies.base import Side, Signal

console = Console()


class LiveExecutor:
    """Thin wrapper around ccxt.coinbase for order execution."""

    def __init__(self):
        if not cfg.has_credentials:
            raise RuntimeError(
                "COINBASE_API_KEY and COINBASE_API_SECRET must be set in .env for live trading"
            )
        if not cfg.is_live:
            raise RuntimeError(
                "TRADING_MODE must be set to 'live' in .env to use LiveExecutor. "
                "Use PaperExecutor for simulated trading."
            )

        self._ex = ccxt.coinbase({
            "apiKey": cfg.api_key,
            "secret": cfg.api_secret,
            "enableRateLimit": True,
        })
        console.print("[bold red]LIVE TRADING ACTIVE — real money will be used[/bold red]")

    def execute(self, signal: Signal, size_usd: float) -> bool:
        """Place a market order for *signal* worth *size_usd* USD.

        Returns True if the order was successfully submitted.
        """
        if signal.side == Side.HOLD:
            return False

        try:
            balance = self._ex.fetch_balance()
            usd_free = float(balance.get("USD", {}).get("free", 0))

            if signal.side == Side.BUY:
                return self._buy(signal, size_usd, usd_free)
            elif signal.side == Side.SELL:
                return self._sell(signal)

        except ccxt.BaseError as exc:
            console.print(f"[red]Order failed: {exc}[/red]")
            return False

        return False

    def _buy(self, signal: Signal, size_usd: float, available_usd: float) -> bool:
        if size_usd > available_usd:
            console.print(
                f"[yellow]Insufficient USD: need ${size_usd:.2f}, have ${available_usd:.2f}[/yellow]"
            )
            size_usd = available_usd * 0.99  # use up to 99% of available

        if size_usd < 1.0:
            console.print("[yellow]Order too small (< $1), skipping[/yellow]")
            return False

        order = self._ex.create_market_buy_order(
            symbol=signal.symbol,
            amount=None,
            params={"funds": str(round(size_usd, 2))},  # quote-currency amount
        )
        console.print(
            f"[green][LIVE BUY ][/green] {signal.symbol} ~${size_usd:.2f} "
            f"| order id: {order.get('id')} | reason: {signal.reason}"
        )
        return True

    def _sell(self, signal: Signal) -> bool:
        # Determine how much of the asset we hold
        base = signal.symbol.split("/")[0]
        balance = self._ex.fetch_balance()
        qty = float(balance.get(base, {}).get("free", 0))

        if qty <= 0:
            console.print(f"[yellow]No {base} to sell[/yellow]")
            return False

        order = self._ex.create_market_sell_order(signal.symbol, qty)
        console.print(
            f"[red][LIVE SELL][/red] {signal.symbol} qty {qty:.6f} "
            f"| order id: {order.get('id')} | reason: {signal.reason}"
        )
        return True

    def portfolio_value(self) -> float:
        """Return total USD value of the portfolio (cash + positions)."""
        balance = self._ex.fetch_balance()
        total_usd = float(balance.get("USD", {}).get("total", 0))

        for symbol in cfg.symbols:
            base = symbol.split("/")[0]
            qty = float(balance.get(base, {}).get("total", 0))
            if qty > 0:
                ticker = self._ex.fetch_ticker(symbol)
                total_usd += qty * float(ticker["last"])

        return total_usd
