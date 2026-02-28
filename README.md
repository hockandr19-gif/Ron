# Ron

Crypto day trading system built in Python. Trades on Coinbase via the Advanced Trade API.

## Features

- **Backtester** — test strategies on historical OHLCV data with P&L, win rate, Sharpe, and drawdown metrics
- **Signals dashboard** — live Streamlit UI with candlestick chart, RSI, MACD, Bollinger Bands, and one-click backtest
- **Trading bot** — paper trade (default) or live trade on Coinbase with built-in risk controls
- **RSI + MACD strategy** — momentum entry/exit with ATR-based stop-loss and take-profit

## Quick start

```bash
# 1. Install
pip install -e ".[dev]"

# 2. Configure
cp .env.example .env
# Edit .env — add Coinbase API keys to go live

# 3. Backtest (no API key needed — uses public data)
ron-backtest --symbol BTC/USD --timeframe 1h --candles 500

# 4. Run dashboard
ron-dashboard

# 5. Paper trade (simulated, safe)
ron-trade --capital 10

# 6. Live trade ($10 real money)
# First set TRADING_MODE=live in .env, then:
ron-trade --capital 10 --live
```

## Risk defaults (`.env`)

| Setting | Default | Description |
|---|---|---|
| `MAX_POSITION_USD` | 10 | Max dollars per single trade |
| `MAX_DAILY_LOSS_USD` | 5 | Bot stops for the day if this is lost |
| `RISK_PER_TRADE_PCT` | 0.02 | 2% of portfolio per trade |
| `TRADING_MODE` | paper | `paper` or `live` |

**Always backtest before trading live.** Past performance does not guarantee future results.
