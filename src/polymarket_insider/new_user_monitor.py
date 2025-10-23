"""Monitor for detecting new users making large trades."""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from .api.goldsky_client import GoldskyClient
from .bot.telegram_bot import TelegramAlertBot
from .config.settings import settings
from .utils.logger import setup_logger

logger = setup_logger(__name__)


class NewUserMonitor:
    """Monitor for detecting new users (< 5 trades) making large trades."""

    def __init__(self, goldsky_client: GoldskyClient, telegram_bot: TelegramAlertBot):
        """Initialize the new user monitor."""
        self.goldsky_client = goldsky_client
        self.telegram_bot = telegram_bot
        self.http_client: Optional[httpx.AsyncClient] = None

        # Track alerted users to avoid duplicate alerts
        self.alerted_users: Set[str] = set()
        self.running = False

    async def initialize(self) -> None:
        """Initialize the HTTP client."""
        self.http_client = httpx.AsyncClient(timeout=settings.http_timeout)
        logger.info("NewUserMonitor initialized")

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.http_client:
            await self.http_client.aclose()
        logger.info("NewUserMonitor cleaned up")

    async def start(self) -> None:
        """Start the monitoring loop."""
        logger.info("Starting new user monitoring...")
        self.running = True

        while self.running:
            try:
                await self._check_for_new_users()

                # Wait before next check (60 seconds)
                await asyncio.sleep(settings.polling_interval_seconds)

            except Exception as e:
                logger.error(f"Error in new user monitoring loop: {e}")
                await asyncio.sleep(120)  # Wait longer on error

    async def stop(self) -> None:
        """Stop the monitoring loop."""
        logger.info("Stopping new user monitoring")
        self.running = False

    async def _check_for_new_users(self) -> None:
        """Check recent trades for new users using Polymarket Data API."""
        try:
            if not self.http_client:
                await self.initialize()

            # Use Polymarket Data API to get recent trades
            logger.debug("Fetching recent trades from Polymarket Data API...")

            # Get trades from the past hour
            url = f"{settings.polymarket_data_api_url}/trades"

            # Query for recent large trades
            response = await self.http_client.get(url, params={"limit": 100})
            response.raise_for_status()

            data = response.json()
            trades = data if isinstance(data, list) else data.get('data', [])

            logger.info(f"Found {len(trades)} recent trades")

            # Process each trade
            for trade in trades:
                await self._process_trade(trade)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching trades: {e}")
        except Exception as e:
            logger.error(f"Error checking for new users: {e}")

    async def _process_trade(self, trade: Dict) -> None:
        """Process a single trade and check if user is new."""
        try:
            # Get trade size in USD
            # Polymarket API returns size directly
            trade_size_usd = float(trade.get('size', 0))

            # Only check large trades
            if trade_size_usd < settings.min_trade_size_usd:
                return

            # Get the trader address
            trader = trade.get('maker_address', '').lower()
            if not trader:
                return

            if trader in self.alerted_users:
                return

            # Check if user is new using Polymarket API
            is_new_user = await self._check_if_new_user(trader)

            if is_new_user:
                logger.info(f"New user detected: {trader} with trade size ${trade_size_usd:,.2f}")
                await self._send_new_user_alert(trader, trade, trade_size_usd)
                self.alerted_users.add(trader)

        except Exception as e:
            logger.error(f"Error processing trade: {e}")

    async def _check_if_new_user(self, user_address: str) -> bool:
        """Check if a user is new (< 5 trades) using Polymarket API."""
        try:
            if not self.http_client:
                await self.initialize()

            # Call Polymarket API to get user's trade count
            url = f"{settings.polymarket_data_api_url}/traded"
            params = {"user": user_address}

            logger.debug(f"Checking trade history for {user_address}")
            response = await self.http_client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            # Check if "traded" field is less than threshold
            traded_count = data.get('traded', 0)
            logger.debug(f"User {user_address} has {traded_count} trades")

            return traded_count < settings.min_user_trades_threshold

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # User not found = new user
                logger.debug(f"User {user_address} not found in API (new user)")
                return True
            logger.error(f"HTTP error checking user {user_address}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error checking if user is new: {e}")
            return False

    async def _send_new_user_alert(self, user_address: str, trade: Dict, trade_size_usd: float) -> None:
        """Send Telegram alert for new user making large trade."""
        try:
            # Get market data
            market = trade.get('market', 'Unknown Market')
            asset_id = trade.get('asset_id', 'unknown')

            # Format timestamp
            timestamp = trade.get('created_at', '')
            try:
                time_str = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
            except:
                time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Get transaction hash
            tx_hash = trade.get('transaction_hash', 'unknown')

            message = f"""🚨 **NEW USER LARGE TRADE ALERT** 🚨

📊 **Trade Details:**
• Market: {market}
• Size: ${trade_size_usd:,.2f}
• Price: ${float(trade.get('price', 0)):.4f}
• Side: {trade.get('side', 'Unknown')}
• Time: {time_str} UTC

👤 **User Analysis:**
• Address: `{user_address}`
• Status: NEW USER (< {settings.min_user_trades_threshold} trades)
• This is one of their first trades on Polymarket

⚠️ **Alert Reason:**
New user making large trade above ${settings.min_trade_size_usd:,.2f} threshold

🔗 **Transaction:** [View on Polygonscan](https://polygonscan.com/tx/{tx_hash})
"""

            await self.telegram_bot.send_message(message)
            logger.info(f"Sent new user alert for {user_address}")

        except Exception as e:
            logger.error(f"Error sending new user alert: {e}")
