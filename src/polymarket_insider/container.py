"""Dependency injection container for managing application components."""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from .config.settings import settings
from .config.validator import validate_configuration
from .connection_manager import ConnectionManager
from .bot.telegram_bot import TelegramAlertBot
from .detector.suspicious_trade_detector import SuspiciousTradeDetector
from .trade_monitor import TradeMonitor
from .api.goldsky_client import GoldskyClient
from .enhanced_trade_monitor import EnhancedTradeMonitor
from .utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class Container:
    """Dependency injection container."""

    def __init__(self):
        """Initialize the container."""
        self._instances: Dict[str, Any] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all singleton dependencies."""
        if self._initialized:
            return

        logger.info("Initializing dependency container")

        # Validate configuration first
        try:
            validate_configuration()
            logger.info("Configuration validation passed")
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise

        # Initialize core dependencies
        connection_manager = ConnectionManager()
        await connection_manager.initialize()
        self._instances['connection_manager'] = connection_manager

        # Initialize Goldsky client
        goldsky_client = GoldskyClient()
        await goldsky_client.initialize()
        self._instances['goldsky_client'] = goldsky_client

        # Initialize bot
        telegram_bot = TelegramAlertBot()
        await telegram_bot.initialize()
        self._instances['telegram_bot'] = telegram_bot

        # Initialize detectors
        detector = SuspiciousTradeDetector()
        self._instances['detector'] = detector

        # Initialize enhanced trade monitor (uses both traditional and subgraph data)
        enhanced_trade_monitor = EnhancedTradeMonitor(
            connection_manager=connection_manager,
            telegram_bot=telegram_bot,
            goldsky_client=goldsky_client
        )
        self._instances['enhanced_trade_monitor'] = enhanced_trade_monitor

        # Keep traditional monitor for backwards compatibility
        trade_monitor = TradeMonitor(
            connection_manager=connection_manager,
            telegram_bot=telegram_bot,
            detector=detector
        )
        self._instances['trade_monitor'] = trade_monitor

        self._initialized = True
        logger.info("Dependency container initialized")

    async def cleanup(self) -> None:
        """Clean up all dependencies."""
        if not self._initialized:
            return

        logger.info("Cleaning up dependency container")

        # Stop enhanced trade monitor
        enhanced_trade_monitor = self._instances.get('enhanced_trade_monitor')
        if enhanced_trade_monitor:
            await enhanced_trade_monitor.stop()

        # Stop traditional trade monitor
        trade_monitor = self._instances.get('trade_monitor')
        if trade_monitor:
            await trade_monitor.stop()

        # Stop telegram bot
        telegram_bot = self._instances.get('telegram_bot')
        if telegram_bot:
            await telegram_bot.stop()

        # Cleanup Goldsky client
        goldsky_client = self._instances.get('goldsky_client')
        if goldsky_client:
            await goldsky_client.cleanup()

        # Cleanup connection manager
        connection_manager = self._instances.get('connection_manager')
        if connection_manager:
            await connection_manager.cleanup()

        self._instances.clear()
        self._initialized = False
        logger.info("Dependency container cleaned up")

    def get_connection_manager(self) -> ConnectionManager:
        """Get the connection manager instance."""
        return self._get_instance('connection_manager', ConnectionManager)

    def get_telegram_bot(self) -> TelegramAlertBot:
        """Get the telegram bot instance."""
        return self._get_instance('telegram_bot', TelegramAlertBot)

    def get_detector(self) -> SuspiciousTradeDetector:
        """Get the detector instance."""
        return self._get_instance('detector', SuspiciousTradeDetector)

    def get_trade_monitor(self) -> TradeMonitor:
        """Get the trade monitor instance."""
        return self._get_instance('trade_monitor', TradeMonitor)

    def get_enhanced_trade_monitor(self) -> EnhancedTradeMonitor:
        """Get the enhanced trade monitor instance."""
        return self._get_instance('enhanced_trade_monitor', EnhancedTradeMonitor)

    def get_goldsky_client(self) -> GoldskyClient:
        """Get the Goldsky client instance."""
        return self._get_instance('goldsky_client', GoldskyClient)

    def _get_instance(self, name: str, instance_type: type) -> Any:
        """Get an instance from the container."""
        instance = self._instances.get(name)
        if instance is None:
            raise ValueError(f"Instance '{name}' not found in container")
        if not isinstance(instance, instance_type):
            raise ValueError(f"Instance '{name}' is not of type {instance_type}")
        return instance


# Global container instance
container = Container()