"""Configuration settings for the Polymarket Insider."""

import os
from typing import Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Polymarket API Configuration (hardcoded)
    polymarket_api_url: str = "https://clob.polymarket.com"
    polymarket_data_api_url: str = "https://data-api.polymarket.com"
    polymarket_ws_url: str = "wss://ws_clob.polymarket.com"

    # Goldsky Subgraph Configuration (hardcoded)
    goldsky_api_url: str = "https://api.goldsky.com/api/public/project_clqj02d9h3t099wqv50zr5w7f/subgraphs/poly-market/gn"
    goldsky_orders_url: str = "https://api.goldsky.com/api/public/project_clqj02d9h3t099wqv50zr5w7f/subgraphs/poly-market-orders/gn"
    goldsky_positions_url: str = "https://api.goldsky.com/api/public/project_clqj02d9h3t099wqv50zr5w7f/subgraphs/poly-market-positions/gn"
    goldsky_activity_url: str = "https://api.goldsky.com/api/public/project_clqj02d9h3t099wqv50zr5w7f/subgraphs/poly-market-activity/gn"
    http_timeout: int = 30
    websocket_ping_interval: int = 20
    websocket_ping_timeout: int = 10

    # Telegram Bot Configuration
    telegram_bot_token: str = Field(
        description="Telegram bot token"
    )
    telegram_chat_id: str = Field(
        description="Telegram chat ID for notifications"
    )

    # Trade Detection Configuration (hardcoded)
    min_trade_size_usd: float = 10000.0
    min_user_trades_threshold: int = 5
    funding_lookback_hours: int = 24
    trade_history_check_days: int = 30

    # Monitoring Configuration (hardcoded)
    polling_interval_seconds: int = 60
    reconnect_delay_seconds: int = 30
    health_check_interval_seconds: int = 3600

    # Trade Processing Configuration (hardcoded)
    usd_conversion_multiplier: float = 1000.0
    max_processed_trades: int = 10000

    # Logging Configuration (hardcoded)
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()