"""Central configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # Coinbase API
    api_key: str = field(default_factory=lambda: os.getenv("COINBASE_API_KEY", ""))
    api_secret: str = field(default_factory=lambda: os.getenv("COINBASE_API_SECRET", ""))

    # Trading mode
    trading_mode: str = field(default_factory=lambda: os.getenv("TRADING_MODE", "paper"))

    # Risk controls
    max_position_usd: float = field(
        default_factory=lambda: float(os.getenv("MAX_POSITION_USD", "100"))
    )
    max_daily_loss_usd: float = field(
        default_factory=lambda: float(os.getenv("MAX_DAILY_LOSS_USD", "50"))
    )
    risk_per_trade_pct: float = field(
        default_factory=lambda: float(os.getenv("RISK_PER_TRADE_PCT", "0.02"))
    )

    # Symbols
    symbols: list[str] = field(
        default_factory=lambda: os.getenv("SYMBOLS", "BTC/USD,ETH/USD,SOL/USD").split(",")
    )

    # Database
    db_path: Path = field(
        default_factory=lambda: Path(os.getenv("DB_PATH", "data/ron.db"))
    )

    @property
    def is_live(self) -> bool:
        return self.trading_mode == "live"

    @property
    def has_credentials(self) -> bool:
        return bool(self.api_key and self.api_secret)


# Singleton used across the app
cfg = Config()
