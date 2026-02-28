"""Streamlit dashboard — signals, equity curve, open positions, trade log.

Run with:  streamlit run src/ron/dashboard/app.py
Or via:    ron-dashboard
"""
from __future__ import annotations

import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ron.config import cfg
from ron.data.fetcher import fetch_ohlcv
from ron.indicators.technical import add_all
from ron.strategies.rsi_macd import RsiMacdStrategy
from ron.backtest.engine import run_backtest, print_summary

st.set_page_config(page_title="Ron Trading", page_icon="📈", layout="wide")

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.title("Ron Trading")

symbol = st.sidebar.selectbox("Symbol", cfg.symbols, index=0)
timeframe = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "4h", "1d"], index=3)
candle_limit = st.sidebar.slider("Candles to load", 100, 1000, 500)
auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=False)

st.sidebar.markdown("---")
st.sidebar.subheader("Backtest settings")
bt_capital = st.sidebar.number_input("Initial capital ($)", 10.0, 100000.0, 1000.0, step=10.0)
bt_pos_size = st.sidebar.slider("Position size %", 1, 50, 10) / 100

# ── Load data ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_data(sym: str, tf: str, lim: int) -> pd.DataFrame:
    return fetch_ohlcv(sym, timeframe=tf, limit=lim)


with st.spinner("Fetching data..."):
    df_raw = load_data(symbol, timeframe, candle_limit)
    df = add_all(df_raw.copy())

# ── Price + indicator chart ─────────────────────────────────────────────────────
st.subheader(f"{symbol} — {timeframe} candles")

fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df["open"], high=df["high"],
    low=df["low"],   close=df["close"],
    name="Price",
))

# Bollinger Bands overlay
if "bb_upper" in df.columns:
    fig.add_trace(go.Scatter(x=df.index, y=df["bb_upper"], name="BB Upper",
                             line=dict(color="rgba(100,100,255,0.4)", dash="dot")))
    fig.add_trace(go.Scatter(x=df.index, y=df["bb_lower"], name="BB Lower",
                             line=dict(color="rgba(100,100,255,0.4)", dash="dot"),
                             fill="tonexty", fillcolor="rgba(100,100,255,0.05)"))

# EMA lines
for p, color in [(21, "orange"), (50, "blue")]:
    col = f"ema_{p}"
    if col in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[col], name=f"EMA {p}",
                                 line=dict(color=color, width=1)))

fig.update_layout(xaxis_rangeslider_visible=False, height=500, margin=dict(l=0, r=0, t=20, b=0))
st.plotly_chart(fig, use_container_width=True)

# ── RSI + MACD sub-charts ──────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    if "rsi_14" in df.columns:
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=df.index, y=df["rsi_14"], name="RSI 14",
                                     line=dict(color="purple")))
        fig_rsi.add_hline(y=70, line_dash="dot", line_color="red", annotation_text="Overbought")
        fig_rsi.add_hline(y=30, line_dash="dot", line_color="green", annotation_text="Oversold")
        fig_rsi.update_layout(title="RSI (14)", height=250, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_rsi, use_container_width=True)

with col2:
    if "macd" in df.columns:
        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(x=df.index, y=df["macd"], name="MACD",
                                      line=dict(color="blue")))
        fig_macd.add_trace(go.Scatter(x=df.index, y=df["macd_signal"], name="Signal",
                                      line=dict(color="orange")))
        colors = ["green" if v >= 0 else "red" for v in df["macd_hist"].fillna(0)]
        fig_macd.add_trace(go.Bar(x=df.index, y=df["macd_hist"], name="Histogram",
                                  marker_color=colors))
        fig_macd.update_layout(title="MACD (12, 26, 9)", height=250, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_macd, use_container_width=True)

# ── Latest signal ──────────────────────────────────────────────────────────────
st.subheader("Latest signal")
strategy = RsiMacdStrategy()
signals = strategy.generate_signals(df, symbol)

if signals:
    sig = signals[0]
    color = "🟢" if sig.side.value == "BUY" else "🔴" if sig.side.value == "SELL" else "⚪"
    st.metric("Signal", f"{color} {sig.side.value}", sig.reason)
    if sig.stop_loss:
        st.caption(f"Stop-loss: ${sig.stop_loss:,.4f}  |  Take-profit: ${sig.take_profit:,.4f}")
else:
    st.info("HOLD — no signal on latest bar")

# ── Backtest ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Backtest on loaded data")

if st.button("Run backtest"):
    with st.spinner("Backtesting..."):
        result = run_backtest(
            df_raw,
            strategy=RsiMacdStrategy(),
            symbol=symbol,
            timeframe=timeframe,
            initial_capital=bt_capital,
            position_size_pct=bt_pos_size,
        )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total return", f"{result.total_return_pct:+.2f}%")
    c2.metric("Win rate", f"{result.win_rate:.1f}%")
    c3.metric("Max drawdown", f"{result.max_drawdown_pct:.2f}%")
    c4.metric("Sharpe ratio", f"{result.sharpe_ratio():.2f}")

    if not result.equity_curve.empty:
        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(x=result.equity_curve.index, y=result.equity_curve,
                                    fill="tozeroy", name="Equity", line=dict(color="green")))
        fig_eq.update_layout(title="Equity curve", height=300, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_eq, use_container_width=True)

    if result.closed_trades:
        trade_data = [{
            "Symbol": t.symbol,
            "Entry price": f"${t.entry_price:,.4f}",
            "Exit price": f"${t.exit_price:,.4f}",
            "P&L": f"${t.pnl:+.2f}",
            "P&L %": f"{t.pnl_pct:+.2f}%",
            "Exit reason": t.exit_reason,
        } for t in result.closed_trades]
        st.dataframe(pd.DataFrame(trade_data), use_container_width=True)
    else:
        st.info("No trades generated in this period.")

# ── Auto-refresh ───────────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(30)
    st.cache_data.clear()
    st.rerun()
