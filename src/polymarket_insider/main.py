"""Main entry point for Polymarket Insider."""

import asyncio
import signal
import sys
from typing import Optional

from .trade_tracker import TradeTracker
from .utils.logger import setup_logger

logger = setup_logger(__name__)


class PolymarketInsiderApp:
    """Main application class."""

    def __init__(self):
        """Initialize the application."""
        self.trade_tracker: Optional[TradeTracker] = None
        self.running = False

    async def start(self) -> None:
        """Start the application."""
        logger.info("Starting Polymarket Insider application")

        try:
            # Initialize the trade tracker
            self.trade_tracker = TradeTracker()

            # Set up signal handlers for graceful shutdown
            self._setup_signal_handlers()

            # Start monitoring
            self.running = True
            await self.trade_tracker.start()

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

        if self.trade_tracker:
            await self.trade_tracker.stop()

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}")
            asyncio.create_task(self.stop())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


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