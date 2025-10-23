"""Main entry point for Polymarket Insider."""

import asyncio
import signal
import sys

from .container import container
from .config.settings import settings
from .utils.logger import setup_logger

logger = setup_logger(__name__)


class PolymarketInsiderApp:
    """Main application class."""

    def __init__(self):
        """Initialize the application."""
        self.running = False

    async def start(self) -> None:
        """Start the application."""
        logger.info("Starting Polymarket Insider application")

        try:
            # Initialize dependency container
            await container.initialize()

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
        """Start monitoring large trades."""
        logger.info("Starting monitoring")

        telegram_bot = container.get_telegram_bot()

        # Start the Telegram bot in the background
        await telegram_bot.start_polling()

        # Send startup message
        await telegram_bot.send_message(
            "🚀 *Polymarket Insider Bot Started*\n\n"
            "🔍 Monitoring for large trades...\n"
            f"💰 Alert threshold: ${settings.min_trade_size_usd:,.2f}\n"
            "📊 Using Goldsky Orderbook Subgraph\n"
            "🤖 Automated alerts enabled",
        )

        # Start large trade monitor
        large_trade_monitor = container.get_large_trade_monitor()
        await large_trade_monitor.start()


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
