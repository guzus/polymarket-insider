"""Simple monitor for tracking large trades on Polymarket."""

import asyncio
from datetime import datetime
from typing import Set, Dict, Any, Optional

from .api.goldsky_client import GoldskyClient
from .api.gamma_client import GammaClient
from .api.data_api_client import DataAPIClient
from .bot.telegram_bot import TelegramAlertBot
from .config.settings import settings
from .utils.logger import setup_logger

logger = setup_logger(__name__)


class LargeTradeMonitor:
    """Monitor for tracking large trades (>$100k) on Polymarket."""

    def __init__(self, goldsky_client: GoldskyClient, gamma_client: GammaClient, data_api_client: DataAPIClient, telegram_bot: TelegramAlertBot):
        """Initialize the large trade monitor."""
        self.goldsky_client = goldsky_client
        self.gamma_client = gamma_client
        self.data_api_client = data_api_client
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
            # Fetch large trades from the last 1 hour
            trades = await self.goldsky_client.get_large_recent_trades(
                min_value_usd=settings.min_trade_size_usd,
                limit=100,
                hours=1
            )

            logger.debug(f"Found {len(trades)} large trades in the last 1 hour")

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

            # Enrich trade data with market information
            enriched_trade = await self.gamma_client.enrich_trade_data(trade)

            # Get taker information
            taker_address = trade.get('taker', '')
            taker_info = None
            taker_profile_url = ''
            if taker_address:
                result = await self.data_api_client.get_trader_summary(taker_address)
                if isinstance(result, tuple) and len(result) == 2:
                    taker_info, taker_profile_url = result
                else:
                    taker_info = result

            # Fallback: Try to get market info from Data API if Gamma API didn't find it
            market_name = enriched_trade.get('market_question', 'Unknown Market')
            if market_name == 'Unknown Market':
                taker_asset_id = trade.get('takerAssetId', '')
                if taker_asset_id:
                    market_data = await self.data_api_client.get_market_by_token(taker_asset_id)
                    if market_data:
                        market_name = market_data.get('title', 'Unknown Market')
                        outcome = market_data.get('outcome', 'Unknown')
                        enriched_trade['market_question'] = market_name
                        enriched_trade['taker_outcome'] = outcome
                        logger.debug(f"Found market from Data API: {market_name}")

            # Calculate trade size in USD
            trade_size_usd = self.goldsky_client.format_trade_usd(enriched_trade)

            trade_type = enriched_trade.get('trade_type', 'UNKNOWN')
            outcome = enriched_trade.get('taker_outcome', 'Unknown')

            # Create enhanced log message
            taker_display = taker_info if taker_info else f"Unknown ({taker_address[:10]}...{taker_address[-8:]})"
            logger.info(f"New large trade detected: ${trade_size_usd:,.2f} - {trade_type} {outcome} - {market_name} - Taker: {taker_display} - TX: {tx_hash}")

            # Send Telegram alert
            await self._send_alert(enriched_trade, trade_size_usd, taker_info, taker_profile_url)

        except Exception as e:
            logger.error(f"Error processing trade: {e}")

    async def _send_alert(self, trade: Dict[str, Any], trade_size_usd: float, taker_info: Optional[str] = None, taker_profile_url: str = '') -> None:
        """Send Telegram alert for a large trade."""
        try:
            # Extract trade details
            tx_hash = trade.get('transactionHash', 'unknown')
            timestamp = int(trade.get('timestamp', 0))
            taker = trade.get('taker', 'unknown')
            taker_asset_id = trade.get('takerAssetId', 'unknown')
            taker_amount = trade.get('takerAmountFilled', '0')
            fee = trade.get('fee', '0')

            # Extract enriched data
            market_name = trade.get('market_question', 'Unknown Market')
            trade_type = trade.get('trade_type', 'UNKNOWN')
            outcome = trade.get('taker_outcome', 'Unknown')

            # Format timestamp
            time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

            # Format amounts
            try:
                taker_amount_formatted = int(taker_amount) / 1_000_000
                fee_formatted = int(fee) / 1_000_000
            except (ValueError, TypeError):
                taker_amount_formatted = 0
                fee_formatted = 0

            # Create emoji for trade type
            trade_emoji = "🟢" if trade_type == "BUY" else "🔴" if trade_type == "SELL" else "⚪"

            # Truncate market name if too long
            market_display = market_name[:60] + "..." if len(market_name) > 60 else market_name

            # Format taker information
            if taker_info and taker_info != f"Unknown Trader (`{taker[:10]}...{taker[-8:]}`)":
                taker_lines = [f"• {taker_info}"]

                # Add profile link if available
                if taker_profile_url:
                    taker_lines.append(f"• [View Profile]({taker_profile_url})")

                taker_lines.append(f"• `{taker[:10]}...{taker[-8:]}`")
                taker_display = '\n'.join(taker_lines)
            else:
                taker_display = f"• `{taker[:10]}...{taker[-8:]}`"

                # Add profile link even for unknown traders
                if taker_profile_url:
                    taker_display += f"\n• [View Profile]({taker_profile_url})"

            message = f"""{trade_emoji} **LARGE TRADE ALERT** {trade_emoji}

📊 **Trade Details:**
• Size: ${trade_size_usd:,.2f}
• Action: {trade_type} {outcome}
• Amount: ${taker_amount_formatted:,.2f}
• Fee: ${fee_formatted:,.2f}
• Time: {time_str} UTC

🎯 **Market:**
• {market_display}

👤 **Taker:**
{taker_display}

🔗 **Transaction:** [View on Polygonscan](https://polygonscan.com/tx/{tx_hash})
"""

            await self.telegram_bot.send_message(message)
            logger.info(f"Sent large trade alert for TX: {tx_hash}")

        except Exception as e:
            logger.error(f"Error sending alert: {e}")
