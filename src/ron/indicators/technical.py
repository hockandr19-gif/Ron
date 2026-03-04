"""Technical indicator calculations on top of pandas DataFrames.

Uses the `ta` library (https://technical-analysis-library-in-python.readthedocs.io).

All functions accept a DataFrame with [open, high, low, close, volume] columns
and return the same DataFrame with indicator columns appended.
Column naming convention: {indicator}_{period} e.g. rsi_14, ema_50, atr_14.
"""
from __future__ import annotations

import pandas as pd
import ta.momentum as ta_mom
import ta.trend as ta_trend
import ta.volatility as ta_vol


def add_all(df: pd.DataFrame) -> pd.DataFrame:
    """Add the full standard indicator set used by built-in strategies."""
    df = add_rsi(df)
    df = add_macd(df)
    df = add_bollinger(df)
    df = add_ema(df)
    df = add_atr(df)
    df = add_volume_sma(df)
    return df


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    df[f"rsi_{period}"] = ta_mom.RSIIndicator(df["close"], window=period).rsi()
    return df


def add_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    macd = ta_trend.MACD(df["close"], window_fast=fast, window_slow=slow, window_sign=signal)
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_hist"] = macd.macd_diff()
    return df


def add_bollinger(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> pd.DataFrame:
    bb = ta_vol.BollingerBands(df["close"], window=period, window_dev=std)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_mid"] = bb.bollinger_mavg()
    df["bb_lower"] = bb.bollinger_lband()
    df["bb_width"] = bb.bollinger_wband()
    return df


def add_ema(df: pd.DataFrame, periods: list[int] | None = None) -> pd.DataFrame:
    for p in (periods or [9, 21, 50, 200]):
        df[f"ema_{p}"] = ta_trend.EMAIndicator(df["close"], window=p).ema_indicator()
    return df


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    df[f"atr_{period}"] = ta_vol.AverageTrueRange(
        df["high"], df["low"], df["close"], window=period
    ).average_true_range()
    return df


def add_volume_sma(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    df[f"vol_sma_{period}"] = df["volume"].rolling(period).mean()
    return df
