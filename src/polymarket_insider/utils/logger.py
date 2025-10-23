"""Enhanced logging configuration with structured logging support."""

import logging
import logging.handlers
import sys
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, Union
from pathlib import Path

from ..config.settings import settings


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for detailed logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        # Add stack trace if present
        if record.stack_info:
            log_entry['stack_trace'] = record.stack_info

        # Add extra fields from record
        extra_fields = {
            k: v for k, v in record.__dict__.items()
            if k not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created',
                'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'getMessage', 'exc_info',
                'exc_text', 'stack_info', 'message'
            }
        }
        log_entry.update(extra_fields)

        return json.dumps(log_entry, default=str)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']

        # Format the base message
        formatted = super().format(record)

        # Add colors
        return f"{color}{formatted}{reset}"


class TradeLogger:
    """Specialized logger for trade-related events."""

    def __init__(self, logger: logging.Logger):
        """Initialize trade logger."""
        self.logger = logger

    def log_trade_processed(self, trade_hash: str, market: str, size: float,
                          processing_time: float = None) -> None:
        """Log a processed trade with structured data."""
        extra = {
            'trade_hash': trade_hash,
            'market': market,
            'size_usd': size,
            'processing_time_ms': processing_time * 1000 if processing_time else None,
            'event_type': 'trade_processed'
        }
        self.logger.info(f"Processed trade: {trade_hash[:8]}... (${size:,.2f})", extra=extra)

    def log_suspicious_trade(self, alert_data: Dict[str, Any]) -> None:
        """Log a suspicious trade alert with structured data."""
        extra = {
            'event_type': 'suspicious_trade',
            'alert': alert_data
        }
        self.logger.warning(
            f"SUSPICIOUS TRADE: {alert_data.get('transaction_hash', 'unknown')[:8]}... "
            f"(${alert_data.get('trade_size', 0):,.2f}) - {alert_data.get('confidence_score', 0)}% confidence",
            extra=extra
        )

    def log_api_call(self, endpoint: str, method: str, status_code: int,
                     response_time: float) -> None:
        """Log API call with performance metrics."""
        extra = {
            'event_type': 'api_call',
            'endpoint': endpoint,
            'method': method,
            'status_code': status_code,
            'response_time_ms': response_time * 1000
        }
        level = logging.WARNING if status_code >= 400 else logging.DEBUG
        self.logger.log(level, f"API {method} {endpoint} -> {status_code} ({response_time:.3f}s)", extra=extra)

    def log_websocket_event(self, event_type: str, details: Dict[str, Any] = None) -> None:
        """Log WebSocket events."""
        extra = {
            'event_type': 'websocket_event',
            'ws_event': event_type,
            'details': details or {}
        }
        self.logger.info(f"WebSocket {event_type}", extra=extra)


def setup_logger(name: Optional[str] = None,
                structured: bool = False,
                file_logging: bool = True) -> logging.Logger:
    """Set up enhanced logging configuration.

    Args:
        name: Logger name
        structured: Whether to use structured JSON logging
        file_logging: Whether to enable file logging

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name or __name__)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    if structured:
        console_formatter = StructuredFormatter()
    else:
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File logging (if enabled)
    if file_logging:
        try:
            # Create logs directory if it doesn't exist
            log_dir = Path('logs')
            log_dir.mkdir(exist_ok=True)

            # Rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_dir / 'polymarket-insider.log',
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)

            # Always use structured format for files
            file_formatter = StructuredFormatter()
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

            # Error-only file handler
            error_handler = logging.handlers.RotatingFileHandler(
                log_dir / 'errors.log',
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=3
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(file_formatter)
            logger.addHandler(error_handler)

        except Exception as e:
            logger.warning(f"Failed to setup file logging: {e}")

    return logger


def get_trade_logger(name: Optional[str] = None) -> TradeLogger:
    """Get a specialized trade logger.

    Args:
        name: Logger name

    Returns:
        TradeLogger instance
    """
    logger = setup_logger(name or 'trade_monitor')
    return TradeLogger(logger)


def configure_root_logger() -> None:
    """Configure the root logger with default settings."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)  # Reduce noise from third-party libraries

    # Prevent propagation to avoid duplicate logs
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.WARNING)
        formatter = ColoredFormatter('%(levelname)s - %(name)s - %(message)s')
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)