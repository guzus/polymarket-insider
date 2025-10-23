"""Dependency injection container for managing application components."""

from typing import Dict, Any
from dataclasses import dataclass

from .config.settings import settings
from .config.validator import validate_configuration
from .bot.telegram_bot import TelegramAlertBot
from .api.goldsky_client import GoldskyClient
from .api.gamma_client import GammaClient
from .api.data_api_client import DataAPIClient
from .large_trade_monitor import LargeTradeMonitor
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

        # Initialize Goldsky client
        goldsky_client = GoldskyClient()
        await goldsky_client.initialize()
        self._instances['goldsky_client'] = goldsky_client

        # Initialize Gamma client
        gamma_client = GammaClient()
        self._instances['gamma_client'] = gamma_client

        # Initialize Data API client
        data_api_client = DataAPIClient()
        self._instances['data_api_client'] = data_api_client

        # Initialize Telegram bot
        telegram_bot = TelegramAlertBot()
        await telegram_bot.initialize()
        self._instances['telegram_bot'] = telegram_bot

        # Initialize large trade monitor
        large_trade_monitor = LargeTradeMonitor(
            goldsky_client=goldsky_client,
            gamma_client=gamma_client,
            data_api_client=data_api_client,
            telegram_bot=telegram_bot
        )
        self._instances['large_trade_monitor'] = large_trade_monitor

        self._initialized = True
        logger.info("Dependency container initialized")

    async def cleanup(self) -> None:
        """Clean up all dependencies."""
        if not self._initialized:
            return

        logger.info("Cleaning up dependency container")

        # Stop large trade monitor
        large_trade_monitor = self._instances.get('large_trade_monitor')
        if large_trade_monitor:
            await large_trade_monitor.stop()

        # Stop telegram bot
        telegram_bot = self._instances.get('telegram_bot')
        if telegram_bot:
            await telegram_bot.stop()

        # Cleanup Goldsky client
        goldsky_client = self._instances.get('goldsky_client')
        if goldsky_client:
            await goldsky_client.cleanup()

        self._instances.clear()
        self._initialized = False
        logger.info("Dependency container cleaned up")

    def get_telegram_bot(self) -> TelegramAlertBot:
        """Get the telegram bot instance."""
        return self._get_instance('telegram_bot', TelegramAlertBot)

    def get_goldsky_client(self) -> GoldskyClient:
        """Get the Goldsky client instance."""
        return self._get_instance('goldsky_client', GoldskyClient)

    def get_gamma_client(self) -> GammaClient:
        """Get the Gamma client instance."""
        return self._get_instance('gamma_client', GammaClient)

    def get_data_api_client(self) -> DataAPIClient:
        """Get the Data API client instance."""
        return self._get_instance('data_api_client', DataAPIClient)

    def get_large_trade_monitor(self) -> LargeTradeMonitor:
        """Get the large trade monitor instance."""
        return self._get_instance('large_trade_monitor', LargeTradeMonitor)

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
