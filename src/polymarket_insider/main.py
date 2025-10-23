"""Main entry point for Polymarket Insider."""

import asyncio
import signal
import sys
from typing import Optional

from .container import container
from .health_checker import HealthChecker
from .config.settings import settings
from .utils.logger import setup_logger

logger = setup_logger(__name__)


class PolymarketInsiderApp:
    """Main application class."""

    def __init__(self):
        """Initialize the application."""
        self.health_checker: Optional[HealthChecker] = None
        self.running = False

    async def start(self) -> None:
        """Start the application."""
        logger.info("Starting Polymarket Insider application")

        try:
            # Initialize dependency container
            await container.initialize()

            # Initialize health checker
            self.health_checker = HealthChecker(
                connection_manager=container.get_connection_manager(),
                telegram_bot=container.get_telegram_bot(),
                detector=container.get_detector(),
                check_interval_seconds=settings.health_check_interval_seconds
            )

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

        # Stop health checker
        if self.health_checker:
            await self.health_checker.stop()

        # Clean up container (stops all components)
        await container.cleanup()

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}")
            asyncio.create_task(self.stop())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def _start_monitoring(self) -> None:
        """Start monitoring trades and health checks."""
        logger.info("Starting monitoring")

        telegram_bot = container.get_telegram_bot()

        # Start the Telegram bot in the background
        await telegram_bot.start_polling()

        # Send startup message
        await telegram_bot.send_message(
            "🚀 *Polymarket Insider Enhanced Started*\n\n"
            "🔍 Monitoring for suspicious trading activity with Goldsky subgraph integration...\n"
            f"💰 Alert threshold: ${settings.min_trade_size_usd:,.2f}\n"
            "📊 Real-time insider detection enabled\n"
            "🤖 Advanced pattern analysis active",
        )

        # Start health checker
        await self.health_checker.start()

        # Start enhanced trade monitoring (this will block)
        enhanced_trade_monitor = container.get_enhanced_trade_monitor()
        await enhanced_trade_monitor.start()


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