"""Health checking and monitoring for the application."""

import asyncio
from typing import Optional

from .bot.telegram_bot import TelegramAlertBot
from .connection_manager import ConnectionManager
from .detector.suspicious_trade_detector import SuspiciousTradeDetector
from .utils.logger import setup_logger

logger = setup_logger(__name__)


class HealthChecker:
    """Manages periodic health checks for the application."""

    def __init__(self, connection_manager: ConnectionManager,
                 telegram_bot: TelegramAlertBot,
                 detector: SuspiciousTradeDetector,
                 check_interval_seconds: int = 3600):
        """Initialize the health checker.

        Args:
            connection_manager: Connection manager instance
            telegram_bot: Telegram bot instance
            detector: Trade detector instance
            check_interval_seconds: Interval between health checks (default: 1 hour)
        """
        self.connection_manager = connection_manager
        self.telegram_bot = telegram_bot
        self.detector = detector
        self.check_interval = check_interval_seconds
        self.running = False
        self._health_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the health checker."""
        logger.info("Starting health checker")
        self.running = True
        self._health_task = asyncio.create_task(self._run_health_checks())

    async def stop(self) -> None:
        """Stop the health checker."""
        logger.info("Stopping health checker")
        self.running = False

        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass

    async def _run_health_checks(self) -> None:
        """Run periodic health checks."""
        while self.running:
            try:
                await self._perform_health_check()
            except Exception as e:
                logger.error(f"Health check failed with exception: {e}")
                # Continue running even if individual health check fails

            # Wait before next health check
            await asyncio.sleep(self.check_interval)

    async def _perform_health_check(self) -> None:
        """Perform a single health check."""
        logger.debug("Performing health check")

        all_healthy = True

        # Test API connectivity
        if await self._check_api_connectivity():
            logger.debug("API connectivity: OK")
        else:
            logger.error("API connectivity: FAILED")
            all_healthy = False

        # Test Telegram bot connectivity
        if await self._check_telegram_connectivity():
            logger.debug("Telegram connectivity: OK")
        else:
            logger.error("Telegram connectivity: FAILED")
            all_healthy = False

        # Clean up old processed trades
        if await self._cleanup_old_trades():
            logger.debug("Trade cleanup: OK")
        else:
            logger.error("Trade cleanup: FAILED")
            all_healthy = False

        if all_healthy:
            logger.info("Health check completed successfully")
            try:
                await self.telegram_bot.send_message("🟢 Health check passed")
            except Exception as e:
                logger.warning(f"Failed to send health check success message: {e}")
        else:
            logger.error("Health check completed with failures")
            try:
                await self.telegram_bot.send_message("🔴 Health check failed")
            except Exception as e:
                logger.error(f"Failed to send health check failure message: {e}")

    async def _check_api_connectivity(self) -> bool:
        """Check if Polymarket API is accessible."""
        try:
            await self.connection_manager.test_connectivity()
            return True
        except Exception as e:
            logger.error(f"API connectivity check failed: {e}")
            return False

    async def _check_telegram_connectivity(self) -> bool:
        """Check if Telegram bot is responsive."""
        try:
            # Check if bot is initialized
            if not self.telegram_bot.is_initialized():
                return False

            # Test connectivity by getting bot info
            await self.telegram_bot.bot.get_me()
            return True
        except Exception as e:
            logger.error(f"Telegram connectivity check failed: {e}")
            return False

    async def _cleanup_old_trades(self) -> bool:
        """Clean up old processed trades to prevent memory leaks."""
        try:
            self.detector.clear_processed_trades()
            return True
        except Exception as e:
            logger.error(f"Trade cleanup failed: {e}")
            return False

    async def run_manual_health_check(self) -> dict:
        """Run a manual health check and return results.

        Returns:
            Dictionary containing health check results
        """
        results = {
            "api_connectivity": False,
            "telegram_connectivity": False,
            "trade_cleanup": False,
            "overall_healthy": False
        }

        try:
            results["api_connectivity"] = await self._check_api_connectivity()
            results["telegram_connectivity"] = await self._check_telegram_connectivity()
            results["trade_cleanup"] = await self._cleanup_old_trades()

            results["overall_healthy"] = all(results.values())

            logger.info(f"Manual health check results: {results}")

        except Exception as e:
            logger.error(f"Manual health check failed: {e}")

        return results