"""Polymarket Data API client for fetching trader information."""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import httpx

from ..config.settings import settings
from ..exceptions import APIError
from ..utils.logger import setup_logger
from ..utils.retry import retry_async, rate_limit_async

logger = setup_logger(__name__)


class DataAPIClient:
    """Client for Polymarket Data API."""

    def __init__(self):
        """Initialize the Data API client."""
        self.base_url = "https://data-api.polymarket.com"
        self._trader_cache: Dict[str, Dict[str, Any]] = {}
        self._last_cache_update: Optional[datetime] = None
        self._cache_ttl_minutes = 30  # Cache trader info for 30 minutes

    async def _fetch_trader_trades(self, user_address: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch recent trades for a specific trader."""
        url = f"{self.base_url}/trades"
        params = {
            "user": user_address.lower(),  # Normalize address to lowercase
            "limit": limit,
            "takerOnly": "true",  # Only get taker trades
            "order": "desc",  # Most recent first
            "sortBy": "timestamp"
        }

        try:
            async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()

                trades = response.json()
                logger.debug(f"Fetched {len(trades)} trades for trader {user_address[:10]}...")
                return trades

        except httpx.HTTPError as e:
            logger.warning(f"HTTP error fetching trader data: {e}")
            return []
        except Exception as e:
            logger.warning(f"Error fetching trader data: {e}")
            return []

    @rate_limit_async(calls_per_second=2.0)  # Conservative rate limiting
    async def get_trader_info(self, user_address: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive trader information.

        Args:
            user_address: The trader's wallet address

        Returns:
            Dictionary containing trader profile and recent activity information
        """
        # Check cache first
        if self._is_cache_valid(user_address):
            return self._trader_cache.get(user_address)

        try:
            # Fetch recent trades for the user
            trades = await self._fetch_trader_trades(user_address, limit=20)

            if not trades:
                logger.debug(f"No trades found for trader {user_address[:10]}...")
                return None

            # Extract profile information from the most recent trade
            latest_trade = trades[0]

            trader_info = {
                'address': user_address,
                'name': latest_trade.get('name', 'Unknown'),
                'pseudonym': latest_trade.get('pseudonym', ''),
                'bio': latest_trade.get('bio', ''),
                'profile_image': latest_trade.get('profileImage', ''),
                'profile_image_optimized': latest_trade.get('profileImageOptimized', ''),
                'recent_trades_count': len(trades),
                'first_trade_date': None,
                'last_trade_date': None,
                'total_volume_usd': 0,
                'unique_markets': set(),
                'trade_frequency': 'unknown'
            }

            # Analyze recent trading activity
            if trades:
                # Convert timestamps and calculate statistics
                timestamps = []
                volumes = []

                for trade in trades:
                    timestamp = trade.get('timestamp', 0)
                    if timestamp:
                        timestamps.append(datetime.fromtimestamp(timestamp))

                    # Calculate volume (size * price)
                    size = trade.get('size', 0)
                    price = trade.get('price', 0)
                    volume = size * price if size and price else 0
                    volumes.append(volume)

                    # Track unique markets
                    title = trade.get('title', '')
                    if title:
                        trader_info['unique_markets'].add(title)

                # Set trading time range
                if timestamps:
                    trader_info['first_trade_date'] = min(timestamps)
                    trader_info['last_trade_date'] = max(timestamps)

                    # Calculate trade frequency
                    time_span = (max(timestamps) - min(timestamps)).days
                    if time_span > 0:
                        trades_per_day = len(trades) / time_span
                        if trades_per_day >= 10:
                            trader_info['trade_frequency'] = 'very high'
                        elif trades_per_day >= 5:
                            trader_info['trade_frequency'] = 'high'
                        elif trades_per_day >= 1:
                            trader_info['trade_frequency'] = 'medium'
                        else:
                            trader_info['trade_frequency'] = 'low'
                    elif len(trades) >= 5:
                        trader_info['trade_frequency'] = 'high'
                    elif len(trades) >= 2:
                        trader_info['trade_frequency'] = 'medium'
                    else:
                        trader_info['trade_frequency'] = 'low'

                # Convert set back to list for JSON serialization
                trader_info['unique_markets'] = list(trader_info['unique_markets'])
                trader_info['unique_markets_count'] = len(trader_info['unique_markets'])

                # Calculate total volume
                trader_info['total_volume_usd'] = sum(volumes)

            # Cache the trader information
            self._trader_cache[user_address] = trader_info
            if self._last_cache_update is None:
                self._last_cache_update = datetime.now()

            logger.info(f"Fetched trader info for {user_address[:10]}...: {trader_info['name']} ({trader_info['pseudonym']})")
            return trader_info

        except Exception as e:
            logger.error(f"Error getting trader info for {user_address[:10]}...: {e}")
            return None

    def _is_cache_valid(self, user_address: str) -> bool:
        """Check if cached trader information is still valid."""
        if user_address not in self._trader_cache:
            return False

        if self._last_cache_update is None:
            return False

        cache_age = datetime.now() - self._last_cache_update
        return cache_age.total_seconds() < (self._cache_ttl_minutes * 60)

    async def get_trader_summary(self, user_address: str) -> str:
        """
        Get a formatted summary of trader information for alerts.

        Args:
            user_address: The trader's wallet address

        Returns:
            Formatted string with trader information
        """
        trader_info = await self.get_trader_info(user_address)

        if not trader_info:
            return f"Unknown Trader (`{user_address[:10]}...{user_address[-8:]}`)"

        # Build trader display name
        display_parts = []

        if trader_info['name'] and trader_info['name'] != 'Unknown':
            display_parts.append(trader_info['name'])

        if trader_info['pseudonym']:
            display_parts.append(f"\"{trader_info['pseudonym']}\"")

        if not display_parts:
            display_parts.append("Anonymous Trader")

        display_name = " ".join(display_parts)

        # Build trading activity summary
        activity_parts = []

        if trader_info['trade_frequency'] != 'unknown':
            activity_parts.append(f"Activity: {trader_info['trade_frequency']}")

        if trader_info['unique_markets_count'] > 1:
            activity_parts.append(f"Markets: {trader_info['unique_markets_count']}")

        if trader_info['total_volume_usd'] > 1000:
            volume_formatted = f"${trader_info['total_volume_usd']:,.0f}"
            activity_parts.append(f"Recent Volume: {volume_formatted}")

        # Combine into final summary
        if activity_parts:
            activity_summary = f" ({' • '.join(activity_parts)})"
        else:
            activity_summary = ""

        return f"{display_name}{activity_summary}"

    def cleanup_cache(self) -> None:
        """Clean up old entries from the cache."""
        if self._last_cache_update and (datetime.now() - self._last_cache_update).total_seconds() > (self._cache_ttl_minutes * 60):
            self._trader_cache.clear()
            self._last_cache_update = None
            logger.info("Cleaned up trader info cache")