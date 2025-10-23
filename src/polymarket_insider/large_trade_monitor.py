"""Simple monitor for tracking large trades on Polymarket."""

import asyncio
from datetime import datetime
from typing import Set, Dict, Any

from .api.goldsky_client import GoldskyClient
from .bot.telegram_bot import TelegramAlertBot
from .config.settings import settings
from .utils.logger import setup_logger

logger = setup_logger(__name__)


class LargeTradeMonitor:
    """Monitor for tracking large trades (>$10k) on Polymarket."""

    def __init__(self, goldsky_client: GoldskyClient, telegram_bot: TelegramAlertBot):
        """Initialize the large trade monitor."""
        self.goldsky_client = goldsky_client
        self.telegram_bot = telegram_bot
        self.running = False

        # Track processed transaction hashes to avoid duplicate alerts
        self.processed_tx_hashes: Set[str] = set()

    async def start(self) -> None:
        """Start the monitoring loop."""
        logger.info("Starting large trade monitoring...")
        self.running = True

        while self.running:
            try:
                await self._check_for_large_trades()

                # Clean up processed hashes if too many
                if len(self.processed_tx_hashes) > 10000:
                    logger.info("Clearing processed transaction hashes cache")
                    self.processed_tx_hashes.clear()

                # Wait before next check
                await asyncio.sleep(settings.polling_interval_seconds)

            except Exception as e:
                logger.error(f"Error in large trade monitoring loop: {e}")
                await asyncio.sleep(120)  # Wait longer on error

    async def stop(self) -> None:
        """Stop the monitoring loop."""
        logger.info("Stopping large trade monitoring")
        self.running = False

    async def _check_for_large_trades(self) -> None:
        """Check for large recent trades using the orderbook subgraph."""
        try:
            # Fetch large trades from the last hour
            trades = await self.goldsky_client.get_large_recent_trades(
                min_value_usd=settings.min_trade_size_usd,
                limit=100,
                hours=1
            )

            logger.debug(f"Found {len(trades)} large trades in the last hour")

            # Process each trade
            for trade in trades:
                await self._process_trade(trade)

        except Exception as e:
            logger.error(f"Error checking for large trades: {e}")

    async def _process_trade(self, trade: Dict[str, Any]) -> None:
        """Process a single large trade and send alert if new."""
        try:
            tx_hash = trade.get('transactionHash', '')
            if not tx_hash:
                return

            # Skip if already processed
            if tx_hash in self.processed_tx_hashes:
                return

            # Mark as processed
            self.processed_tx_hashes.add(tx_hash)

            # Calculate trade size in USD
            trade_size_usd = self.goldsky_client.format_trade_usd(trade)

            logger.info(f"New large trade detected: ${trade_size_usd:,.2f} - TX: {tx_hash}")

            # Send Telegram alert
            await self._send_alert(trade, trade_size_usd)

        except Exception as e:
            logger.error(f"Error processing trade: {e}")

    async def _send_alert(self, trade: Dict[str, Any], trade_size_usd: float) -> None:
        """Send Telegram alert for a large trade."""
        try:
            # Extract trade details
            tx_hash = trade.get('transactionHash', 'unknown')
            timestamp = int(trade.get('timestamp', 0))
            maker = trade.get('maker', 'unknown')
            taker = trade.get('taker', 'unknown')
            maker_asset_id = trade.get('makerAssetId', 'unknown')
            taker_asset_id = trade.get('takerAssetId', 'unknown')
            maker_amount = trade.get('makerAmountFilled', '0')
            taker_amount = trade.get('takerAmountFilled', '0')
            fee = trade.get('fee', '0')

            # Format timestamp
            time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

            # Format amounts
            try:
                maker_amount_formatted = int(maker_amount) / 1_000_000
                taker_amount_formatted = int(taker_amount) / 1_000_000
                fee_formatted = int(fee) / 1_000_000
            except (ValueError, TypeError):
                maker_amount_formatted = 0
                taker_amount_formatted = 0
                fee_formatted = 0

            message = f"""🚨 **LARGE TRADE ALERT** 🚨

📊 **Trade Details:**
• Size: ${trade_size_usd:,.2f}
• Taker Amount: ${taker_amount_formatted:,.2f}
• Maker Amount: {maker_amount_formatted:,.2f} tokens
• Fee: ${fee_formatted:,.2f}
• Time: {time_str} UTC

👥 **Participants:**
• Maker: `{maker[:10]}...{maker[-8:]}`
• Taker: `{taker[:10]}...{taker[-8:]}`

🔖 **Assets:**
• Maker Asset: `{maker_asset_id[:10]}...{maker_asset_id[-8:]}`
• Taker Asset: `{taker_asset_id[:10]}...{taker_asset_id[-8:]}`

🔗 **Transaction:** [View on Polygonscan](https://polygonscan.com/tx/{tx_hash})
"""

            await self.telegram_bot.send_message(message)
            logger.info(f"Sent large trade alert for TX: {tx_hash}")

        except Exception as e:
            logger.error(f"Error sending alert: {e}")
