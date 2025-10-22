"""Configuration settings for the Polymarket Insider."""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Polymarket API Configuration
    polymarket_api_url: str = Field(
        default="https://clob.polymarket.com",
        description="Polymarket API base URL"
    )
    polymarket_ws_url: str = Field(
        default="wss://ws_clob.polymarket.com",
        description="Polymarket WebSocket URL"
    )

    # Telegram Bot Configuration
    telegram_bot_token: str = Field(
        description="Telegram bot token"
    )
    telegram_chat_id: str = Field(
        description="Telegram chat ID for notifications"
    )

    # Trade Detection Configuration
    min_trade_size_usd: float = Field(
        default=10000.0,
        description="Minimum trade size in USD to trigger alert"
    )
    funding_lookback_hours: int = Field(
        default=24,
        description="Hours to look back for wallet funding"
    )
    trade_history_check_days: int = Field(
        default=30,
        description="Days to check for trade history"
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()