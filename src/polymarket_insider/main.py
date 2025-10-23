"""Main entry point for Polymarket Insider."""

import asyncio
import signal
import sys
from typing import Optional

from .bot.telegram_bot import TelegramAlertBot
from .connection_manager import ConnectionManager
from .detector.suspicious_trade_detector import SuspiciousTradeDetector
from .health_checker import HealthChecker
from .trade_monitor import TradeMonitor
from .config.settings import settings
from .utils.logger import setup_logger

logger = setup_logger(__name__)


class PolymarketInsiderApp:
    """Main application class."""

    def __init__(self):
        """Initialize the application."""
        self.connection_manager: Optional[ConnectionManager] = None
        self.telegram_bot: Optional[TelegramAlertBot] = None
        self.detector: Optional[SuspiciousTradeDetector] = None
        self.trade_monitor: Optional[TradeMonitor] = None
        self.health_checker: Optional[HealthChecker] = None
        self.running = False

    async def start(self) -> None:
        """Start the application."""
        logger.info("Starting Polymarket Insider application")

        try:
            # Initialize components
            await self._initialize_components()

            # Set up signal handlers for graceful shutdown
            self._setup_signal_handlers()

            # Start monitoring
            self.running = True
            await self._start_monitoring()

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Application error: {e}")
            raise
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the application."""
        if not self.running:
            return

        logger.info("Stopping Polymarket Insider application")
        self.running = False

        # Stop components in reverse order
        if self.trade_monitor:
            await self.trade_monitor.stop()

        if self.health_checker:
            await self.health_checker.stop()

        if self.telegram_bot:
            await self.telegram_bot.stop()

        if self.connection_manager:
            await self.connection_manager.cleanup()

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}")
            asyncio.create_task(self.stop())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def _initialize_components(self) -> None:
        """Initialize application components."""
        logger.info("Initializing application components")

        # Initialize connection manager first
        self.connection_manager = ConnectionManager()
        await self.connection_manager.initialize()

        # Initialize Telegram bot
        self.telegram_bot = TelegramAlertBot()
        await self.telegram_bot.initialize()

        # Initialize detector
        self.detector = SuspiciousTradeDetector()

        # Initialize trade monitor
        self.trade_monitor = TradeMonitor(
            connection_manager=self.connection_manager,
            telegram_bot=self.telegram_bot,
            detector=self.detector
        )

        # Initialize health checker
        self.health_checker = HealthChecker(
            connection_manager=self.connection_manager,
            telegram_bot=self.telegram_bot,
            detector=self.detector,
            check_interval_seconds=settings.health_check_interval_seconds
        )

        logger.info("All components initialized successfully")

    async def _start_monitoring(self) -> None:
        """Start monitoring trades and health checks."""
        logger.info("Starting monitoring")

        # Start the Telegram bot in the background
        await self.telegram_bot.start_polling()

        # Send startup message
        await self.telegram_bot.send_message(
            "🚀 *Polymarket Insider Started*\n\n"
            "Monitoring for suspicious trading activity...\n"
            f"Alert threshold: ${settings.min_trade_size_usd:,.2f}",
        )

        # Start health checker
        await self.health_checker.start()

        # Start trade monitoring (this will block)
        await self.trade_monitor.start()


async def main() -> None:
    """Main async function."""
    app = PolymarketInsiderApp()
    await app.start()


def cli_main() -> None:
    """CLI entry point."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()