"""Enhanced trade monitor using Goldsky subgraph data for insider detection."""

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from .api.goldsky_client import GoldskyClient
from .api.models import Trade
from .bot.telegram_bot import TelegramAlertBot
from .connection_manager import ConnectionManager
from .config.settings import settings
from .detector.insider_detector import InsiderDetector
from .detector.suspicious_trade_detector import SuspiciousTradeDetector
from .exceptions import TradeProcessingError, WebSocketError
from .utils.logger import setup_logger

logger = setup_logger(__name__)


class EnhancedTradeMonitor:
    """Enhanced trade monitor with Goldsky subgraph integration."""

    def __init__(self, connection_manager: ConnectionManager,
                 telegram_bot: TelegramAlertBot,
                 goldsky_client: GoldskyClient):
        """Initialize the enhanced trade monitor."""
        self.connection_manager = connection_manager
        self.telegram_bot = telegram_bot
        self.goldsky_client = goldsky_client

        # Initialize detectors
        self.suspicious_detector = SuspiciousTradeDetector()
        self.insider_detector = InsiderDetector(goldsky_client)

        self.running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._subgraph_monitor_task: Optional[asyncio.Task] = None

        # Track processed trades
        self.processed_trade_hashes: set = set()

    async def start(self) -> None:
        """Start the enhanced trade monitor."""
        logger.info("Starting enhanced trade monitor with Goldsky subgraph integration")
        self.running = True

        # Start traditional monitoring (WebSocket + polling)
        self._monitor_task = asyncio.create_task(self._monitor_traditional())

        # Start subgraph-based monitoring
        self._subgraph_monitor_task = asyncio.create_task(self._monitor_subgraph())

        # Wait for both tasks to complete (they run forever until stopped)
        try:
            await asyncio.gather(self._monitor_task, self._subgraph_monitor_task)
        except asyncio.CancelledError:
            logger.info("Enhanced trade monitor tasks cancelled")
            raise

    async def stop(self) -> None:
        """Stop the enhanced trade monitor."""
        logger.info("Stopping enhanced trade monitor")
        self.running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        if self._subgraph_monitor_task:
            self._subgraph_monitor_task.cancel()
            try:
                await self._subgraph_monitor_task
            except asyncio.CancelledError:
                pass

    async def _monitor_traditional(self) -> None:
        """Monitor trades using traditional WebSocket/polling methods."""
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
                await asyncio.sleep(settings.polling_interval_seconds * 2)

    async def _monitor_subgraph(self) -> None:
        """Monitor trades using Goldsky subgraph data."""
        logger.info("Starting Goldsky subgraph monitoring")

        while self.running:
            try:
                # Get recent trades from subgraph
                subgraph_trades = await self.goldsky_client.get_recent_trades(limit=100)

                # Process each trade for insider activity
                for trade_data in subgraph_trades:
                    await self._analyze_subgraph_trade(trade_data)

                # Also check for suspicious patterns
                await self._analyze_suspicious_patterns()

                # Wait before next check
                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Error during subgraph monitoring: {e}")
                await asyncio.sleep(120)  # Wait longer on error

    async def _analyze_suspicious_patterns(self) -> None:
        """Analyze broader suspicious patterns using subgraph data."""
        try:
            # Get large trades from the last few hours
            large_trades = await self.goldsky_client.get_large_trades(
                min_value_usd=settings.min_trade_size_usd,
                hours=6
            )

            # Group trades by wallet to identify patterns
            wallet_trades = defaultdict(list)
            for trade in large_trades:
                wallet = trade.get('maker', '').lower()
                if wallet:
                    wallet_trades[wallet].append(trade)

            # Analyze each wallet with multiple large trades
            for wallet, trades in wallet_trades.items():
                if len(trades) >= 2:  # Multiple large trades
                    await self._analyze_multi_trade_pattern(wallet, trades)

        except Exception as e:
            logger.error(f"Error analyzing suspicious patterns: {e}")

    async def _analyze_multi_trade_pattern(self, wallet: str, trades: List[Dict]) -> None:
        """Analyze wallets with multiple large trades."""
        try:
            # Get comprehensive wallet analysis
            wallet_analysis = await self.insider_detector._analyze_wallet_behavior(wallet)
            if not wallet_analysis:
                return

            # Calculate total volume
            total_volume = sum(
                float(trade.get('amount', 0)) * float(trade.get('price', 0)) * 1000
                for trade in trades
            )

            # Check if this is suspicious
            if (wallet_analysis.get('is_new_wallet') or
                wallet_analysis.get('trading_frequency', 0) < 0.1):

                # Create a special alert for multi-trade patterns
                alert_data = {
                    'trade': trades[0],  # Use the first trade as reference
                    'wallet_address': wallet,
                    'confidence_score': 70,
                    'risk_level': 'HIGH',
                    'reasons': [
                        f"Multiple large trades: {len(trades)} trades totaling ${total_volume:,.2f}",
                        f"New wallet: {wallet_analysis.get('is_new_wallet', False)}",
                        f"Low trading frequency: {wallet_analysis.get('trading_frequency', 0):.2f}/hr"
                    ],
                    'pattern_type': 'MULTI_LARGE_TRADES'
                }

                await self._send_enhanced_alert(alert_data)

        except Exception as e:
            logger.error(f"Error analyzing multi-trade pattern: {e}")

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
        """Analyze a trade using both traditional and subgraph methods."""
        try:
            logger.debug(f"Analyzing trade: {trade.transaction_hash}")

            # Skip if already processed
            if trade.transaction_hash in self.processed_trade_hashes:
                return

            self.processed_trade_hashes.add(trade.transaction_hash)

            # Traditional analysis
            funding_history = await self.connection_manager.get_wallet_funding_history(
                trade.maker if trade.side == "BUY" else trade.taker,
                hours=self.suspicious_detector.funding_lookback_hours
            )

            trade_history = await self.connection_manager.get_wallet_trade_history(
                trade.maker if trade.side == "BUY" else trade.taker,
                days=self.suspicious_detector.trade_history_check_days
            )

            traditional_alert = await self.suspicious_detector.analyze_trade(trade, funding_history, trade_history)
            if traditional_alert:
                logger.info(f"Traditional suspicious trade detected: {traditional_alert.reason}")
                await self.telegram_bot.send_alert(traditional_alert)

            # Enhanced subgraph analysis
            await self._analyze_trade_with_subgraph(trade)

        except Exception as e:
            logger.error(f"Error analyzing trade {trade.transaction_hash}: {e}")

    async def _analyze_trade_with_subgraph(self, trade: Trade) -> None:
        """Analyze trade using subgraph data."""
        try:
            # Convert trade to subgraph format
            trade_data = {
                'id': trade.transaction_hash,
                'transactionHash': trade.transaction_hash,
                'maker': trade.maker,
                'taker': trade.taker,
                'price': str(trade.price),
                'amount': str(trade.size),
                'type': trade.side,
                'timestamp': str(int(trade.timestamp.timestamp())),
                'token': {
                    'id': trade.token_id,
                    'market': {
                        'id': 'unknown',  # Will be filled if available
                        'question': trade.market_question or '',
                        'description': '',
                        'endDate': None
                    }
                }
            }

            # Use insider detector
            insider_alert = await self.insider_detector.analyze_trade_for_insider_activity(trade_data)
            if insider_alert:
                logger.info(f"Insider activity detected: {insider_alert.risk_level} risk")
                await self._send_insider_alert(insider_alert)

        except Exception as e:
            logger.error(f"Error in subgraph analysis: {e}")

    async def _analyze_subgraph_trade(self, trade_data: Dict) -> None:
        """Analyze trade data directly from subgraph."""
        try:
            tx_hash = trade_data.get('transactionHash', '')
            if not tx_hash or tx_hash in self.processed_trade_hashes:
                return

            self.processed_trade_hashes.add(tx_hash)

            # Analyze for insider activity
            insider_alert = await self.insider_detector.analyze_trade_for_insider_activity(trade_data)
            if insider_alert:
                logger.info(f"Subgraph insider activity detected: {insider_alert.risk_level} risk")
                await self._send_insider_alert(insider_alert)

        except Exception as e:
            logger.error(f"Error analyzing subgraph trade: {e}")

    async def _send_insider_alert(self, alert) -> None:
        """Send insider activity alert via Telegram."""
        try:
            # Format alert message
            message = f"""🚨 **INSIDER ACTIVITY DETECTED** 🚨

📊 **Trade Details:**
- Market: {alert.wallet_analysis.get('market_context', {}).get('question', 'Unknown')}
- Size: ${self._calculate_trade_size_usd(alert.trade):,.2f}
- Price: ${float(alert.trade.get('price', 0)):.4f}
- Type: {alert.trade.get('type', 'Unknown')}
- Time: {datetime.fromtimestamp(int(alert.trade.get('timestamp', 0))).strftime('%Y-%m-%d %H:%M:%S')} UTC

🔍 **Risk Assessment:**
- Risk Level: {alert.risk_level}
- Confidence: {alert.confidence_score}%

👛 **Wallet Analysis:**
- Address: `{alert.wallet_address}`
- New Wallet: {alert.wallet_analysis.get('is_new_wallet', False)}
- Total Activities: {alert.wallet_analysis.get('total_activities', 0)}
- Trading Frequency: {alert.wallet_analysis.get('trading_frequency', 0):.2f}/hr

🎯 **Suspicious Patterns:**
{chr(10).join(f"• {reason}" for reason in alert.reasons)}

🔗 **Transaction:** [View on Etherscan](https://etherscan.io/tx/{alert.trade.get('transactionHash', '')})
"""

            await self.telegram_bot.send_message(message)

        except Exception as e:
            logger.error(f"Error sending insider alert: {e}")

    async def _send_enhanced_alert(self, alert_data: Dict) -> None:
        """Send enhanced alert for special patterns."""
        try:
            message = f"""🔴 **ENHANCED PATTERN DETECTED** 🔴

📊 **Pattern Details:**
- Type: {alert_data.get('pattern_type', 'Unknown')}
- Risk Level: {alert_data.get('risk_level', 'UNKNOWN')}
- Confidence: {alert_data.get('confidence_score', 0)}%

👛 **Wallet:** `{alert_data.get('wallet_address', '')}`

🎯 **Detection Reasons:**
{chr(10).join(f"• {reason}" for reason in alert_data.get('reasons', []))}

🔗 **Transaction:** [View on Etherscan](https://etherscan.io/tx/{alert_data.get('trade', {}).get('transactionHash', '')})
"""

            await self.telegram_bot.send_message(message)

        except Exception as e:
            logger.error(f"Error sending enhanced alert: {e}")

    def _calculate_trade_size_usd(self, trade_data: Dict) -> float:
        """Calculate trade size in USD."""
        try:
            amount = float(trade_data.get('amount', 0))
            price = float(trade_data.get('price', 0))
            return amount * price * 1000
        except (ValueError, TypeError):
            return 0

    def clear_processed_trades(self, older_than_hours: int = 24) -> None:
        """Clear processed trades to prevent memory buildup."""
        if len(self.processed_trade_hashes) > 50000:  # Prevent memory issues
            self.processed_trade_hashes.clear()
            logger.info("Cleared processed trades cache")

        # Also clear detector caches
        self.suspicious_detector.clear_processed_trades(older_than_hours)
        self.insider_detector.clear_cache()