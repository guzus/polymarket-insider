"""Configuration settings for the Polymarket Insider."""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Goldsky Orderbook Subgraph Configuration
    goldsky_orderbook_url: str = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn"
    http_timeout: int = 30

    # Telegram Bot Configuration
    telegram_bot_token: str = Field(
        description="Telegram bot token"
    )
    telegram_chat_id: str = Field(
        description="Telegram chat ID for notifications"
    )

    # Trade Detection Configuration
    min_trade_size_usd: float = 100000.0

    # Monitoring Configuration
    polling_interval_seconds: int = 60

    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
