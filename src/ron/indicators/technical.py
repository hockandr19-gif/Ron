"""Technical indicator calculations on top of pandas DataFrames.

All functions accept a DataFrame with [open, high, low, close, volume] columns
and return the same DataFrame with indicator columns appended.
"""
from __future__ import annotations

import pandas as pd
import pandas_ta as ta


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
    df[f"rsi_{period}"] = ta.rsi(df["close"], length=period)
    return df


def add_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    macd = ta.macd(df["close"], fast=fast, slow=slow, signal=signal)
    if macd is not None:
        df["macd"] = macd[f"MACD_{fast}_{slow}_{signal}"]
        df["macd_signal"] = macd[f"MACDs_{fast}_{slow}_{signal}"]
        df["macd_hist"] = macd[f"MACDh_{fast}_{slow}_{signal}"]
    return df


def add_bollinger(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> pd.DataFrame:
    bb = ta.bbands(df["close"], length=period, std=std)
    if bb is not None:
        df["bb_upper"] = bb[f"BBU_{period}_{std}"]
        df["bb_mid"] = bb[f"BBM_{period}_{std}"]
        df["bb_lower"] = bb[f"BBL_{period}_{std}"]
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]
    return df


def add_ema(df: pd.DataFrame, periods: list[int] | None = None) -> pd.DataFrame:
    for p in (periods or [9, 21, 50, 200]):
        df[f"ema_{p}"] = ta.ema(df["close"], length=p)
    return df


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    df[f"atr_{period}"] = ta.atr(df["high"], df["low"], df["close"], length=period)
    return df


def add_volume_sma(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    df[f"vol_sma_{period}"] = df["volume"].rolling(period).mean()
    return df
