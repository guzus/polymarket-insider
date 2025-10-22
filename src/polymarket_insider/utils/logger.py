"""Logging configuration and utilities."""

import logging
import sys
from typing import Optional

from ..config.settings import settings


def setup_logger(name: Optional[str] = None) -> logging.Logger:
    """Set up logging configuration."""
    logger = logging.getLogger(name or __name__)

    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

    return logger