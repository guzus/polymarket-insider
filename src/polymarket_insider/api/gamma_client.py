"""Polymarket Gamma API client for fetching market information."""

import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import httpx

from ..config.settings import settings
from ..exceptions import APIError
from ..utils.logger import setup_logger
from ..utils.retry import retry_async, rate_limit_async

logger = setup_logger(__name__)


class GammaClient:
    """Client for Polymarket Gamma API."""

    def __init__(self):
        """Initialize the Gamma client."""
        self.base_url = "https://gamma-api.polymarket.com"
        self._markets_cache: Dict[str, Dict[str, Any]] = {}
        self._token_to_market: Dict[str, Dict[str, Any]] = {}
        self._last_cache_update: Optional[datetime] = None
        self._cache_ttl_minutes = 15  # Cache for 15 minutes

    async def _fetch_markets(self) -> List[Dict[str, Any]]:
        """Fetch all markets from Gamma API."""
        url = f"{self.base_url}/markets"
        params = {
            "limit": 1000,  # Fetch more markets to reduce API calls
            "offset": 0
        }

        try:
            async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()

                markets = response.json()
                logger.info(f"Fetched {len(markets)} markets from Gamma API")
                return markets

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching markets: {e}")
            raise APIError(f"Failed to fetch markets: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error fetching markets: {e}")
            raise APIError(f"Invalid JSON response from markets API: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching markets: {e}")
            raise APIError(f"Failed to fetch markets: {e}")

    @rate_limit_async(calls_per_second=2.0)  # Conservative rate limiting
    async def _update_markets_cache(self) -> None:
        """Update the markets cache if needed."""
        now = datetime.now()

        # Check if cache needs updating
        if (self._last_cache_update is None or
            (now - self._last_cache_update) > timedelta(minutes=self._cache_ttl_minutes)):

            logger.info("Updating markets cache from Gamma API")
            markets = await self._fetch_markets()

            # Clear existing cache
            self._markets_cache.clear()
            self._token_to_market.clear()

            # Populate cache
            for market in markets:
                try:
                    # Use question as key
                    question = market.get('question', '')
                    if question:
                        self._markets_cache[question] = market

                    # Map token IDs to market for lookup
                    clob_token_ids_str = market.get('clobTokenIds', '[]')
                    if clob_token_ids_str:
                        try:
                            token_ids = json.loads(clob_token_ids_str)
                            outcomes = json.loads(market.get('outcomes', '[]'))

                            # Create mapping for each token ID
                            for i, token_id in enumerate(token_ids):
                                if i < len(outcomes):
                                    self._token_to_market[token_id] = {
                                        'question': question,
                                        'outcome': outcomes[i],
                                        'market': market
                                    }
                        except (json.JSONDecodeError, IndexError) as e:
                            logger.warning(f"Error parsing token IDs for market {question}: {e}")

                except Exception as e:
                    logger.warning(f"Error processing market in cache update: {e}")

            self._last_cache_update = now
            logger.info(f"Markets cache updated: {len(self._markets_cache)} markets, {len(self._token_to_market)} token mappings")

    @retry_async(max_attempts=3, initial_delay=1.0)
    async def get_market_by_token(self, token_id: str) -> Optional[Dict[str, Any]]:
        """Get market information by token ID."""
        await self._update_markets_cache()
        return self._token_to_market.get(token_id)

    @retry_async(max_attempts=3, initial_delay=1.0)
    async def get_market_by_question(self, question: str) -> Optional[Dict[str, Any]]:
        """Get market information by question."""
        await self._update_markets_cache()
        return self._markets_cache.get(question)

    async def get_token_info(self, token_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed token information including market and outcome."""
        token_data = await self.get_market_by_token(token_id)
        if not token_data:
            return None

        return {
            'token_id': token_id,
            'market_question': token_data['question'],
            'outcome': token_data['outcome'],
            'market_data': token_data['market']
        }

    def is_buy_order(self, maker_asset_id: str, taker_asset_id: str) -> Optional[bool]:
        """
        Determine if a trade is a buy or sell order.

        In Polymarket, if the taker is buying YES tokens, they're buying the outcome.
        If they're buying NO tokens, they're selling the outcome (or buying the opposite).

        Args:
            maker_asset_id: The maker's asset ID
            taker_asset_id: The taker's asset ID

        Returns:
            True if it's a buy order, False if it's a sell order, None if unknown
        """
        try:
            # Look up both tokens to determine the trade direction
            maker_token_data = self._token_to_market.get(maker_asset_id)
            taker_token_data = self._token_to_market.get(taker_asset_id)

            if not maker_token_data or not taker_token_data:
                return None

            # If taker is buying YES tokens for a market, it's a buy order
            if (taker_token_data['outcome'].upper() == 'YES' and
                maker_token_data['outcome'].upper() == 'NO'):
                return True  # Taker is buying YES (buying the outcome)

            # If taker is buying NO tokens for a market, it's a sell order
            if (taker_token_data['outcome'].upper() == 'NO' and
                maker_token_data['outcome'].upper() == 'YES'):
                return False  # Taker is buying NO (selling the outcome)

            # Same market, different outcomes - determine by which outcome is being bought
            if (taker_token_data['market_question'] == maker_token_data['market_question']):
                # If buying YES, it's a buy; if buying NO, it's a sell
                return taker_token_data['outcome'].upper() == 'YES'

            return None

        except Exception as e:
            logger.warning(f"Error determining trade direction: {e}")
            return None

    async def enrich_trade_data(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich trade data with market information and trade direction.

        Args:
            trade: Raw trade data from orderbook subgraph

        Returns:
            Enriched trade data with market name and direction
        """
        enriched_trade = trade.copy()

        try:
            # Get market information for taker asset (what the taker received)
            taker_asset_id = trade.get('takerAssetId', '')
            if taker_asset_id:
                token_info = await self.get_token_info(taker_asset_id)
                if token_info:
                    enriched_trade['market_question'] = token_info['market_question']
                    enriched_trade['taker_outcome'] = token_info['outcome']

            # Get market information for maker asset (what the maker received)
            maker_asset_id = trade.get('makerAssetId', '')
            if maker_asset_id:
                token_info = await self.get_token_info(maker_asset_id)
                if token_info:
                    enriched_trade['maker_outcome'] = token_info['outcome']

            # Determine trade direction
            trade_direction = self.is_buy_order(maker_asset_id, taker_asset_id)
            if trade_direction is not None:
                enriched_trade['is_buy'] = trade_direction
                enriched_trade['trade_type'] = 'BUY' if trade_direction else 'SELL'
            else:
                enriched_trade['trade_type'] = 'UNKNOWN'

        except Exception as e:
            logger.warning(f"Error enriching trade data: {e}")
            enriched_trade['market_question'] = 'Unknown Market'
            enriched_trade['trade_type'] = 'UNKNOWN'

        return enriched_trade