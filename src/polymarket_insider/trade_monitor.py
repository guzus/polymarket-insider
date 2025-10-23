"""Trade monitoring and processing logic."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional

from .api.models import Trade
from .bot.telegram_bot import TelegramAlertBot
from .connection_manager import ConnectionManager
from .config.settings import settings
from .detector.suspicious_trade_detector import SuspiciousTradeDetector
from .exceptions import TradeProcessingError, WebSocketError
from .utils.logger import setup_logger

logger = setup_logger(__name__)


class TradeMonitor:
    """Monitors and processes trades from Polymarket."""

    def __init__(self, connection_manager: ConnectionManager,
                 telegram_bot: TelegramAlertBot,
                 detector: SuspiciousTradeDetector):
        """Initialize the trade monitor."""
        self.connection_manager = connection_manager
        self.telegram_bot = telegram_bot
        self.detector = detector
        self.running = False
        self._monitor_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the trade monitor."""
        logger.info("Starting trade monitor")
        self.running = True
        self._monitor_task = asyncio.create_task(self._monitor_trades())

    async def stop(self) -> None:
        """Stop the trade monitor."""
        logger.info("Stopping trade monitor")
        self.running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    async def _monitor_trades(self) -> None:
        """Monitor trades with WebSocket fallback to polling."""
        while self.running:
            try:
                # Try WebSocket monitoring first
                await self._monitor_websocket()
            except (WebSocketError, Exception) as e:
                logger.error(f"WebSocket monitoring failed: {e}")
                logger.info("Falling back to polling mode")
                await self._monitor_polling()

            # Reconnect delay
            if self.running:
                logger.info(f"Reconnecting in {settings.reconnect_delay_seconds} seconds...")
                await asyncio.sleep(settings.reconnect_delay_seconds)

    async def _monitor_websocket(self) -> None:
        """Monitor trades via WebSocket connection."""
        try:
            websocket = await self.connection_manager.connect_websocket(
                callback=self._handle_websocket_message
            )

            logger.info("Connected to WebSocket, monitoring trades")

            async for message in websocket:
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
                trades = await self.connection_manager.get_recent_trades(limit=50)

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
                await asyncio.sleep(settings.polling_interval_seconds)

            except Exception as e:
                logger.error(f"Error during polling: {e}")
                await asyncio.sleep(settings.polling_interval_seconds * 2)  # Wait longer on error

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
            # Convert trade data to Trade model
            trade = self._parse_trade_data(trade_data)
            if trade:
                await self._analyze_trade(trade)

        except Exception as e:
            logger.error(f"Error processing trade data: {e}")
            raise TradeProcessingError(f"Failed to process trade data: {e}")

    def _parse_trade_data(self, trade_data: dict) -> Optional[Trade]:
        """Parse raw trade data into a Trade model."""
        try:
            # Validate required fields
            required_fields = ["maker", "taker", "price", "size", "side", "token_id", "timestamp", "transaction_hash"]
            if not all(field in trade_data for field in required_fields):
                logger.warning(f"Missing required fields in trade data: {trade_data}")
                return None

            return Trade(
                maker=trade_data["maker"],
                taker=trade_data["taker"],
                price=float(trade_data["price"]),
                size=float(trade_data["size"]),
                side=trade_data["side"],
                token_id=trade_data["token_id"],
                timestamp=datetime.fromisoformat(trade_data["timestamp"]),
                transaction_hash=trade_data["transaction_hash"],
                market_question=trade_data.get("market_question"),
                usd_size=float(trade_data["size"]) * float(trade_data["price"]) * settings.usd_conversion_multiplier
            )

        except (ValueError, KeyError) as e:
            logger.error(f"Error parsing trade data: {e}")
            return None

    async def _analyze_trade(self, trade: Trade) -> None:
        """Analyze a trade for suspicious activity."""
        try:
            logger.debug(f"Analyzing trade: {trade.transaction_hash}")

            # Skip trades below minimum size
            if trade.usd_size and trade.usd_size < self.detector.min_trade_size_usd:
                logger.debug(f"Trade too small: ${trade.usd_size:.2f}")
                return

            # Get the wallet address to analyze
            wallet_address = trade.maker if trade.side == "BUY" else trade.taker

            # Fetch wallet funding history
            funding_history = await self.connection_manager.get_wallet_funding_history(
                wallet_address,
                hours=self.detector.funding_lookback_hours
            )

            # Fetch wallet trade history
            trade_history = await self.connection_manager.get_wallet_trade_history(
                wallet_address,
                days=self.detector.trade_history_check_days
            )

            # Analyze for suspicious patterns
            alert = await self.detector.analyze_trade(trade, funding_history, trade_history)

            if alert:
                logger.info(f"Suspicious trade detected: {alert.reason}")
                await self.telegram_bot.send_alert(alert)

        except Exception as e:
            logger.error(f"Error analyzing trade {trade.transaction_hash}: {e}")
            raise TradeProcessingError(f"Failed to analyze trade: {e}")