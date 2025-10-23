"""Configuration validation utilities."""

import re
from typing import List, Optional
from pydantic import ValidationError

from .settings import settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class ConfigurationError(Exception):
    """Configuration validation error."""


class ConfigurationValidator:
    """Validates application configuration."""

    def __init__(self):
        """Initialize the validator."""
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_all(self) -> None:
        """Validate all configuration settings."""
        self.errors.clear()
        self.warnings.clear()

        logger.info("Validating application configuration")

        # Validate required settings
        self._validate_required_settings()

        # Validate API settings
        self._validate_api_settings()

        # Validate Telegram settings
        self._validate_telegram_settings()

        # Validate trade detection settings
        self._validate_trade_detection_settings()

        # Validate logging settings
        self._validate_logging_settings()

  
        # Validate timing settings
        self._validate_timing_settings()

        # Report results
        self._report_validation_results()

        if self.errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in self.errors)
            raise ConfigurationError(error_msg)

        if self.warnings:
            logger.warning("Configuration warnings:\n" + "\n".join(f"  - {warning}" for warning in self.warnings))

        logger.info("Configuration validation completed successfully")

    def _validate_required_settings(self) -> None:
        """Validate required configuration settings."""
        # Telegram Bot Token
        if not settings.telegram_bot_token:
            self.errors.append("TELEGRAM_BOT_TOKEN is required")
        elif not self._is_valid_telegram_token(settings.telegram_bot_token):
            self.errors.append("TELEGRAM_BOT_TOKEN format is invalid (should be like '123456789:ABCdefGHIjklMNOpqrsTUVwxyz')")

        # Telegram Chat ID
        if not settings.telegram_chat_id:
            self.errors.append("TELEGRAM_CHAT_ID is required")
        elif not self._is_valid_telegram_chat_id(settings.telegram_chat_id):
            self.errors.append("TELEGRAM_CHAT_ID format is invalid")

    def _validate_api_settings(self) -> None:
        """Validate API-related settings."""
        # Goldsky Orderbook URL
        if not settings.goldsky_orderbook_url:
            self.errors.append("GOLDSKY_ORDERBOOK_URL is required")
        elif not self._is_valid_url(settings.goldsky_orderbook_url):
            self.errors.append("GOLDSKY_ORDERBOOK_URL format is invalid")

        # HTTP timeout
        if settings.http_timeout <= 0:
            self.errors.append("HTTP_TIMEOUT must be positive")
        elif settings.http_timeout < 10:
            self.warnings.append("HTTP_TIMEOUT is very low, may cause connection failures")
        elif settings.http_timeout > 300:
            self.warnings.append("HTTP_TIMEOUT is very high, may cause slow error detection")

    def _validate_telegram_settings(self) -> None:
        """Validate Telegram bot settings."""
        # Additional validation can be added here for Telegram-specific settings
        pass

    def _validate_trade_detection_settings(self) -> None:
        """Validate trade detection settings."""
        # Minimum trade size
        if settings.min_trade_size_usd <= 0:
            self.errors.append("MIN_TRADE_SIZE_USD must be positive")
        elif settings.min_trade_size_usd < 100:
            self.warnings.append("MIN_TRADE_SIZE_USD is very low, may generate many false positives")
        elif settings.min_trade_size_usd > 100000:
            self.warnings.append("MIN_TRADE_SIZE_USD is very high, may miss suspicious trades")

    def _validate_logging_settings(self) -> None:
        """Validate logging settings."""
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if settings.log_level not in valid_log_levels:
            self.errors.append(f"LOG_LEVEL must be one of: {', '.join(valid_log_levels)}")

  
    def _validate_timing_settings(self) -> None:
        """Validate timing-related settings."""
        # Polling interval
        if settings.polling_interval_seconds <= 0:
            self.errors.append("POLLING_INTERVAL_SECONDS must be positive")
        elif settings.polling_interval_seconds < 10:
            self.warnings.append("POLLING_INTERVAL_SECONDS is very low, may cause API rate limiting")
        elif settings.polling_interval_seconds > 300:
            self.warnings.append("POLLING_INTERVAL_SECONDS is very high, may cause delays in detection")

    def _is_valid_telegram_token(self, token: str) -> bool:
        """Validate Telegram bot token format."""
        # Telegram bot tokens are like: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
        pattern = r'^\d+:[A-Za-z0-9_-]{35}$'
        return bool(re.match(pattern, token))

    def _is_valid_telegram_chat_id(self, chat_id: str) -> bool:
        """Validate Telegram chat ID format."""
        # Chat IDs can be numeric (positive or negative) or start with @ for usernames
        if chat_id.startswith('@'):
            return len(chat_id) > 1 and chat_id[1:].isalnum()
        else:
            return chat_id.lstrip('-').isdigit()

    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format."""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return url_pattern.match(url) is not None

    def _report_validation_results(self) -> None:
        """Report validation results to logger."""
        if self.errors:
            logger.error(f"Found {len(self.errors)} configuration error(s)")
            for error in self.errors:
                logger.error(f"  Configuration error: {error}")

        if self.warnings:
            logger.warning(f"Found {len(self.warnings)} configuration warning(s)")
            for warning in self.warnings:
                logger.warning(f"  Configuration warning: {warning}")

        if not self.errors and not self.warnings:
            logger.info("All configuration settings are valid")


def validate_configuration() -> None:
    """Validate application configuration and raise exception if invalid."""
    validator = ConfigurationValidator()
    validator.validate_all()


# Global validator instance
config_validator = ConfigurationValidator()