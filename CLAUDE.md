# CLAUDE.md

Guidance for AI assistants working on the **Ron** crypto trading system.

## Project overview

Ron is a Python crypto day-trading system targeting Coinbase. It has three layers:

| Layer | Entry point | Purpose |
|---|---|---|
| Backtester | `ron-backtest` | Test strategies on historical data |
| Dashboard | `ron-dashboard` | Streamlit signals + charts UI |
| Trading bot | `ron-trade` | Paper or live orders via Coinbase API |

Exchange: **Coinbase Advanced Trade API** via `ccxt`.
Language: **Python 3.11+**.

## Repository structure

```
Ron/
├── pyproject.toml              # Build config, dependencies, CLI entry points
├── .env.example                # Environment variable template (copy → .env)
├── .gitignore
├── README.md
├── CLAUDE.md                   # This file
├── src/ron/
│   ├── config.py               # Singleton cfg — all settings from .env
│   ├── cli.py                  # Click entry points: backtest / trade / dashboard
│   ├── data/
│   │   └── fetcher.py          # OHLCV fetch (ccxt + SQLite cache)
│   ├── indicators/
│   │   └── technical.py        # RSI, MACD, BB, EMA, ATR via pandas-ta
│   ├── strategies/
│   │   ├── base.py             # BaseStrategy, Signal, Side
│   │   └── rsi_macd.py         # RSI+MACD momentum strategy
│   ├── backtest/
│   │   └── engine.py           # Bar-by-bar backtest, BacktestResult
│   ├── execution/
│   │   ├── risk.py             # RiskManager — position sizing, daily loss limit
│   │   ├── paper.py            # PaperExecutor — simulated fills
│   │   ├── live.py             # LiveExecutor — real Coinbase orders
│   │   └── bot.py              # Main polling loop (paper or live)
│   └── dashboard/
│       └── app.py              # Streamlit app
├── tests/
└── data/                       # SQLite cache (gitignored)
```

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env            # fill in API keys for live trading
```

## Commands

```bash
ron-backtest                    # backtest default strategy on all configured symbols
ron-backtest -s BTC/USD -t 4h   # specific symbol and timeframe
ron-dashboard                   # open Streamlit dashboard
ron-trade                       # paper trade (safe default, $10 capital)
ron-trade --live                # real money (requires TRADING_MODE=live in .env)
```

## Architecture decisions

- **ccxt** is used for exchange connectivity — it abstracts Coinbase's API and makes adding other exchanges trivial later.
- **SQLite** cache (via `data/ron.db`) avoids hammering the API during backtesting iterations.
- **pandas-ta** handles all indicator math — no manual formula implementations.
- **RiskManager** is a mandatory gate between signal generation and order execution. Never bypass it.
- The bot defaults to **paper mode** and requires an explicit `--live` flag plus `TRADING_MODE=live` in `.env` to place real orders. This double confirmation is intentional.

## Adding a new strategy

1. Create `src/ron/strategies/my_strategy.py`
2. Subclass `BaseStrategy` and implement `generate_signals(df, symbol) -> list[Signal]`
3. Return `Signal(side=Side.BUY/SELL/HOLD, symbol=..., price=..., size_pct=...)`
4. Pass your strategy to `run_backtest()` or `run_bot()` to test/run it

## Key conventions

- All money values are **USD floats** unless a variable name says otherwise.
- DataFrames always have a UTC `DatetimeIndex` named `ts` with columns `[open, high, low, close, volume]`.
- Indicator columns follow the pattern `{indicator}_{period}` (e.g. `rsi_14`, `ema_50`, `atr_14`).
- `cfg` is a module-level singleton in `ron.config` — import and use it, don't instantiate `Config()` again.
- Never commit `.env` or `data/ron.db` — both are gitignored.

## Risk controls (never remove or weaken these)

- `RiskManager.trading_halted` — stops all trading when daily loss limit is hit.
- `RiskManager.position_size_usd` — caps each trade at `MAX_POSITION_USD`.
- `LiveExecutor.__init__` — raises if `TRADING_MODE != live` or credentials are missing.
- Bot requires explicit `--live` CLI flag AND `TRADING_MODE=live` to place real orders.

## Testing

```bash
pytest tests/
```

Tests go in `tests/`. Use `pytest-asyncio` for async tests.

## Git workflow

- **Main branch**: `master`
- **Claude branches**: must start with `claude/` and end with the session ID suffix
- Push: `git push -u origin <branch-name>`
- Commit messages: imperative mood, describe the *why* not just the *what*

## Updating this file

Update CLAUDE.md whenever: new strategies are added, dependencies change, the directory structure changes, or new CLI commands are added.
