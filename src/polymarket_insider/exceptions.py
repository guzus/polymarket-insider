"""Custom exceptions for the Polymarket Insider application."""


class PolymarketInsiderError(Exception):
    """Base exception for all Polymarket Insider errors."""
    pass


class ConnectionError(PolymarketInsiderError):
    """Raised when there's an error connecting to external services."""
    pass


class APIError(PolymarketInsiderError):
    """Raised when there's an error with the Polymarket API."""
    pass


class WebSocketError(ConnectionError):
    """Raised when there's an error with WebSocket connections."""
    pass


class TradeProcessingError(PolymarketInsiderError):
    """Raised when there's an error processing trade data."""
    pass


class ConfigurationError(PolymarketInsiderError):
    """Raised when there's a configuration error."""
    pass


class BotError(PolymarketInsiderError):
    """Raised when there's an error with the Telegram bot."""
    pass