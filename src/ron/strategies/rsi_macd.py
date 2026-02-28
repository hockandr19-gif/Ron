"""RSI + MACD momentum strategy.

Entry logic
-----------
BUY  when:  RSI crosses up through oversold (default 30) AND MACD histogram
            turns positive AND price is above EMA-50 (trend filter).

SELL when:  RSI crosses above overbought (default 70) OR MACD histogram
            turns negative while in a long position.

Stop-loss  : 1× ATR below entry price.
Take-profit: 2× ATR above entry price (2 : 1 risk/reward).
"""
from __future__ import annotations

import pandas as pd

from ron.indicators.technical import add_all
from ron.strategies.base import BaseStrategy, Side, Signal


class RsiMacdStrategy(BaseStrategy):
    name = "rsi_macd"

    def __init__(self, params: dict | None = None):
        defaults = {
            "rsi_period": 14,
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "atr_period": 14,
            "sl_atr_mult": 1.0,
            "tp_atr_mult": 2.0,
            "trend_ema": 50,
            "min_volume_ratio": 0.8,  # candle volume must be ≥ 80% of 20-bar avg
        }
        merged = {**defaults, **(params or {})}
        super().__init__(merged)

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        df = add_all(df.copy())

        rsi_col = f"rsi_{self.params['rsi_period']}"
        atr_col = f"atr_{self.params['atr_period']}"
        ema_col = f"ema_{self.params['trend_ema']}"

        # Need at least 2 bars to detect crossovers
        if len(df) < 2 or rsi_col not in df.columns:
            return []

        prev = df.iloc[-2]
        curr = df.iloc[-1]

        price = float(curr["close"])
        atr = float(curr[atr_col]) if atr_col in df.columns else 0.0
        ema = float(curr[ema_col]) if ema_col in df.columns else price
        vol_sma = float(curr.get("vol_sma_20", curr["volume"]))
        vol_ratio = float(curr["volume"]) / vol_sma if vol_sma > 0 else 1.0

        rsi_prev = float(prev[rsi_col])
        rsi_curr = float(curr[rsi_col])
        macd_hist_prev = float(prev.get("macd_hist", 0))
        macd_hist_curr = float(curr.get("macd_hist", 0))

        oversold = self.params["rsi_oversold"]
        overbought = self.params["rsi_overbought"]

        # --- BUY signal ---
        rsi_crosses_up = rsi_prev < oversold and rsi_curr >= oversold
        macd_turns_positive = macd_hist_prev <= 0 and macd_hist_curr > 0
        above_trend = price > ema
        enough_volume = vol_ratio >= self.params["min_volume_ratio"]

        if rsi_crosses_up and macd_turns_positive and above_trend and enough_volume:
            sl = price - self.params["sl_atr_mult"] * atr if atr else None
            tp = price + self.params["tp_atr_mult"] * atr if atr else None
            return [
                Signal(
                    side=Side.BUY,
                    symbol=symbol,
                    price=price,
                    size_pct=1.0,
                    stop_loss=sl,
                    take_profit=tp,
                    reason="RSI crossed oversold ↑, MACD hist turned +, above EMA",
                    meta={"rsi": rsi_curr, "macd_hist": macd_hist_curr, "vol_ratio": vol_ratio},
                )
            ]

        # --- SELL signal ---
        rsi_overbought_hit = rsi_curr >= overbought
        macd_turns_negative = macd_hist_prev >= 0 and macd_hist_curr < 0

        if rsi_overbought_hit or macd_turns_negative:
            reason = []
            if rsi_overbought_hit:
                reason.append(f"RSI overbought ({rsi_curr:.1f})")
            if macd_turns_negative:
                reason.append("MACD hist turned −")
            return [
                Signal(
                    side=Side.SELL,
                    symbol=symbol,
                    price=price,
                    size_pct=1.0,
                    reason=", ".join(reason),
                    meta={"rsi": rsi_curr, "macd_hist": macd_hist_curr},
                )
            ]

        return []
