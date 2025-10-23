"""Configuration settings for the Polymarket Insider."""

import os
from typing import Optional
from pydantic import Field, validator
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
    http_timeout: int = Field(
        default=30,
        description="HTTP request timeout in seconds"
    )
    websocket_ping_interval: int = Field(
        default=20,
        description="WebSocket ping interval in seconds"
    )
    websocket_ping_timeout: int = Field(
        default=10,
        description="WebSocket ping timeout in seconds"
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

    # Monitoring Configuration
    polling_interval_seconds: int = Field(
        default=30,
        description="Polling interval in seconds when WebSocket fails"
    )
    reconnect_delay_seconds: int = Field(
        default=30,
        description="Delay before attempting to reconnect"
    )
    health_check_interval_seconds: int = Field(
        default=3600,
        description="Health check interval in seconds (default: 1 hour)"
    )

    # Trade Processing Configuration
    usd_conversion_multiplier: float = Field(
        default=1000.0,
        description="Multiplier for converting trade size to USD"
    )
    max_processed_trades: int = Field(
        default=10000,
        description="Maximum number of processed trades to keep in memory"
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )

    @validator('min_trade_size_usd')
    def validate_min_trade_size(cls, v):
        if v <= 0:
            raise ValueError('min_trade_size_usd must be greater than 0')
        return v

    @validator('funding_lookback_hours')
    def validate_funding_lookback(cls, v):
        if v <= 0:
            raise ValueError('funding_lookback_hours must be greater than 0')
        if v > 168:  # 1 week
            raise ValueError('funding_lookback_hours must not exceed 168 hours (1 week)')
        return v

    @validator('trade_history_check_days')
    def validate_trade_history_days(cls, v):
        if v <= 0:
            raise ValueError('trade_history_check_days must be greater than 0')
        if v > 365:
            raise ValueError('trade_history_check_days must not exceed 365 days')
        return v

    @validator('polling_interval_seconds')
    def validate_polling_interval(cls, v):
        if v < 5:
            raise ValueError('polling_interval_seconds must be at least 5 seconds')
        return v

    @validator('reconnect_delay_seconds')
    def validate_reconnect_delay(cls, v):
        if v < 1:
            raise ValueError('reconnect_delay_seconds must be at least 1 second')
        return v

    @validator('health_check_interval_seconds')
    def validate_health_check_interval(cls, v):
        if v < 60:  # 1 minute minimum
            raise ValueError('health_check_interval_seconds must be at least 60 seconds')
        return v

    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'log_level must be one of: {", ".join(valid_levels)}')
        return v.upper()

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()