"""End-to-end smoke tests using synthetic OHLCV data (no internet required)."""
import numpy as np
import pandas as pd
import pytest

from ron.indicators.technical import add_all, add_rsi, add_macd, add_atr
from ron.strategies.base import Side
from ron.strategies.rsi_macd import RsiMacdStrategy
from ron.backtest.engine import run_backtest
from ron.execution.paper import PaperExecutor
from ron.execution.risk import RiskManager


def make_fake_ohlcv(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic OHLCV data that walks up and down realistically."""
    rng = np.random.default_rng(seed)
    close = 50_000.0
    closes = []
    for _ in range(n):
        close *= 1 + rng.normal(0, 0.02)  # ±2% random walk
        close = max(close, 100.0)
        closes.append(close)

    closes = np.array(closes)
    noise = rng.uniform(0.98, 1.02, size=n)
    highs = closes * rng.uniform(1.001, 1.03, size=n)
    lows = closes * rng.uniform(0.97, 0.999, size=n)
    opens = closes * noise
    volumes = rng.uniform(1, 100, size=n)

    index = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    index.name = "ts"
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes},
        index=index,
    )


# ── Indicator tests ────────────────────────────────────────────────────────────

def test_add_rsi():
    df = make_fake_ohlcv()
    df = add_rsi(df, period=14)
    assert "rsi_14" in df.columns
    rsi = df["rsi_14"].dropna()
    assert (rsi >= 0).all() and (rsi <= 100).all(), "RSI must be 0-100"


def test_add_macd():
    df = make_fake_ohlcv()
    df = add_macd(df)
    for col in ("macd", "macd_signal", "macd_hist"):
        assert col in df.columns


def test_add_all():
    df = make_fake_ohlcv()
    df = add_all(df)
    expected = ["rsi_14", "macd", "macd_hist", "bb_upper", "bb_lower", "ema_50", "atr_14"]
    for col in expected:
        assert col in df.columns, f"Missing column: {col}"


# ── Strategy tests ─────────────────────────────────────────────────────────────

def test_strategy_returns_list():
    df = make_fake_ohlcv()
    strategy = RsiMacdStrategy()
    signals = strategy.generate_signals(df, "BTC/USD")
    assert isinstance(signals, list)


def test_strategy_signal_has_valid_side():
    df = make_fake_ohlcv()
    strategy = RsiMacdStrategy()
    signals = strategy.generate_signals(df, "BTC/USD")
    for sig in signals:
        assert sig.side in (Side.BUY, Side.SELL, Side.HOLD)
        assert sig.price > 0
        assert sig.symbol == "BTC/USD"


# ── Backtest tests ─────────────────────────────────────────────────────────────

def test_backtest_runs():
    df = make_fake_ohlcv(n=500)
    result = run_backtest(df, RsiMacdStrategy(), "BTC/USD", "1h", initial_capital=1000.0)
    assert result.initial_capital == 1000.0
    assert result.symbol == "BTC/USD"
    assert not result.equity_curve.empty


def test_backtest_equity_curve_length():
    df = make_fake_ohlcv(n=400)
    result = run_backtest(df, RsiMacdStrategy(), "BTC/USD", "1h", initial_capital=1000.0)
    # Equity curve covers bars after warmup period (200 bars)
    assert len(result.equity_curve) == len(df) - 200


def test_backtest_final_equity_is_positive():
    df = make_fake_ohlcv(n=500)
    result = run_backtest(df, RsiMacdStrategy(), "BTC/USD", "1h", initial_capital=1000.0)
    assert result.final_equity > 0


def test_backtest_win_rate_range():
    df = make_fake_ohlcv(n=500)
    result = run_backtest(df, RsiMacdStrategy(), "BTC/USD", "1h", initial_capital=1000.0)
    assert 0.0 <= result.win_rate <= 100.0


# ── Paper executor tests ───────────────────────────────────────────────────────

def test_paper_executor_buy_and_sell():
    from ron.strategies.base import Signal
    executor = PaperExecutor(initial_capital=1000.0)

    buy_sig = Signal(side=Side.BUY, symbol="BTC/USD", price=50000.0, size_pct=1.0)
    sell_sig = Signal(side=Side.SELL, symbol="BTC/USD", price=52000.0, size_pct=1.0)

    placed = executor.execute(buy_sig, size_usd=100.0)
    assert placed
    assert "BTC/USD" in executor.positions

    placed = executor.execute(sell_sig, size_usd=0)
    assert placed
    assert "BTC/USD" not in executor.positions
    assert len(executor.trade_log) == 1
    assert executor.trade_log[0]["pnl"] > 0  # price went up, should profit


def test_paper_executor_no_double_buy():
    from ron.strategies.base import Signal
    executor = PaperExecutor(initial_capital=1000.0)
    sig = Signal(side=Side.BUY, symbol="BTC/USD", price=50000.0, size_pct=1.0)
    executor.execute(sig, size_usd=100.0)
    result = executor.execute(sig, size_usd=100.0)  # second buy should be skipped
    assert not result


# ── Risk manager tests ─────────────────────────────────────────────────────────

def test_risk_manager_position_size():
    from ron.strategies.base import Signal
    rm = RiskManager(max_position_usd=50.0, risk_per_trade_pct=0.02)
    sig = Signal(side=Side.BUY, symbol="BTC/USD", price=50000.0, size_pct=1.0)
    size = rm.position_size_usd(portfolio_value=1000.0, signal=sig)
    assert size == min(1000.0 * 0.02, 50.0)


def test_risk_manager_daily_loss_halt():
    from ron.strategies.base import Signal
    rm = RiskManager(max_daily_loss_usd=10.0)
    rm.record_pnl(-15.0)  # exceed the limit
    assert rm.trading_halted

    sig = Signal(side=Side.BUY, symbol="BTC/USD", price=50000.0, size_pct=1.0)
    approved, reason = rm.check(1000.0, sig)
    assert not approved
    assert "limit" in reason.lower()
