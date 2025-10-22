"""Main trade tracking logic."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional

from ..api.client import PolymarketClient
from ..bot.telegram_bot import TelegramAlertBot
from ..detector.suspicious_trade_detector import SuspiciousTradeDetector
from ..config.settings import settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class TradeTracker:
    """Main trade tracker that orchestrates monitoring and alerts."""

    def __init__(self):
        """Initialize the trade tracker."""
        self.polymarket_client = PolymarketClient()
        self.telegram_bot = TelegramAlertBot()
        self.detector = SuspiciousTradeDetector()
        self.running = False
        self.websocket: Optional[any] = None

    async def start(self) -> None:
        """Start the trade tracker."""
        logger.info("Starting Polymarket trade tracker")

        # Initialize the Telegram bot
        await self.telegram_bot.initialize()

        # Start the Telegram bot in the background
        asyncio.create_task(self.telegram_bot.start_polling())

        # Send startup message
        await self.telegram_bot.send_message(
            "🚀 *Polymarket Insider Started*\n\n"
            "Monitoring for suspicious trading activity...\n"
            f"Alert threshold: ${settings.min_trade_size_usd:,.2f}",
        )

        # Start monitoring
        await self._start_monitoring()

    async def stop(self) -> None:
        """Stop the trade tracker."""
        logger.info("Stopping Polymarket trade tracker")
        self.running = False

        if self.websocket:
            await self.websocket.close()

        await self.telegram_bot.stop()

    async def _start_monitoring(self) -> None:
        """Start monitoring trades."""
        self.running = True

        while self.running:
            try:
                # Attempt to connect to WebSocket for real-time updates
                await self._monitor_websocket()
            except Exception as e:
                logger.error(f"WebSocket monitoring failed: {e}")
                logger.info("Falling back to polling mode")

                # Fallback to polling
                await self._monitor_polling()

            # If we get here, we need to reconnect
            if self.running:
                logger.info("Reconnecting in 30 seconds...")
                await asyncio.sleep(30)

    async def _monitor_websocket(self) -> None:
        """Monitor trades via WebSocket connection."""
        try:
            self.websocket = await self.polymarket_client.connect_websocket(
                callback=self._handle_websocket_message
            )

            logger.info("Connected to WebSocket, monitoring trades")

            async for message in self.websocket:
                if not self.running:
                    break

                try:
                    data = json.loads(message)
                    if data.get("type") == "trade":
                        await self._process_trade_data(data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {message}")
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}")

        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            raise

    async def _monitor_polling(self) -> None:
        """Monitor trades via polling (fallback method)."""
        logger.info("Starting polling mode")

        last_check_time = datetime.now() - timedelta(minutes=5)

        while self.running:
            try:
                # Fetch recent trades
                trades = await self.polymarket_client.get_recent_trades(limit=50)

                # Filter trades newer than our last check
                new_trades = [
                    trade for trade in trades
                    if trade.timestamp > last_check_time
                ]

                if new_trades:
                    logger.info(f"Found {len(new_trades)} new trades via polling")
                    for trade in new_trades:
                        await self._analyze_trade(trade)

                last_check_time = datetime.now()

                # Wait before next poll
                await asyncio.sleep(30)  # Poll every 30 seconds

            except Exception as e:
                logger.error(f"Error during polling: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def _handle_websocket_message(self, message: str) -> None:
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            if data.get("type") == "trade":
                await self._process_trade_data(data)
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")

    async def _process_trade_data(self, trade_data: dict) -> None:
        """Process raw trade data from WebSocket/API."""
        try:
            # Convert to Trade model (this would need proper parsing)
            # For now, this is a placeholder
            logger.debug(f"Processing trade data: {trade_data}")

        except Exception as e:
            logger.error(f"Error processing trade data: {e}")

    async def _analyze_trade(self, trade) -> None:
        """Analyze a trade for suspicious activity."""
        try:
            logger.debug(f"Analyzing trade: {trade.transaction_hash}")

            # Get the wallet address to analyze
            wallet_address = trade.maker if trade.side == "BUY" else trade.taker

            # Fetch wallet funding history
            funding_history = await self.polymarket_client.get_wallet_funding_history(
                wallet_address,
                hours=settings.funding_lookback_hours
            )

            # Fetch wallet trade history
            trade_history = await self.polymarket_client.get_wallet_trade_history(
                wallet_address,
                days=settings.trade_history_check_days
            )

            # Analyze for suspicious patterns
            alert = await self.detector.analyze_trade(trade, funding_history, trade_history)

            if alert:
                logger.info(f"Suspicious trade detected: {alert.reason}")
                await self.telegram_bot.send_alert(alert)

        except Exception as e:
            logger.error(f"Error analyzing trade {getattr(trade, 'transaction_hash', 'unknown')}: {e}")

    async def run_health_check(self) -> None:
        """Run periodic health checks."""
        while self.running:
            try:
                # Test API connectivity
                await self.polymarket_client.get_markets()

                # Test Telegram connectivity
                await self.telegram_bot.send_message("🟢 Health check passed")

                # Clean up old processed trades
                self.detector.clear_processed_trades()

                logger.info("Health check completed")

            except Exception as e:
                logger.error(f"Health check failed: {e}")
                await self.telegram_bot.send_message("🔴 Health check failed")

            # Wait before next health check
            await asyncio.sleep(3600)  # Every hour