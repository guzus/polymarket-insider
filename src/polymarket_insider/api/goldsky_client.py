"""Goldsky Orderbook Subgraph GraphQL client for Polymarket large trade tracking."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from gql import gql, Client
from gql.transport.httpx import HTTPXAsyncTransport

from ..config.settings import settings
from ..exceptions import APIError
from ..utils.logger import setup_logger
from ..utils.retry import retry_async, rate_limit_async, api_circuit_breaker

logger = setup_logger(__name__)


class GoldskyClient:
    """GraphQL client for Goldsky Orderbook Subgraph."""

    def __init__(self):
        """Initialize the Goldsky client."""
        self.orderbook_url = settings.goldsky_orderbook_url
        self._client: Optional[Client] = None

    async def initialize(self) -> None:
        """Initialize GraphQL client."""
        try:
            transport = HTTPXAsyncTransport(url=self.orderbook_url, timeout=settings.http_timeout)
            self._client = Client(transport=transport, fetch_schema_from_transport=False)
            logger.info("Goldsky Orderbook GraphQL client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Goldsky client: {e}")
            raise APIError(f"Failed to initialize Goldsky client: {e}")

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._client:
            try:
                if hasattr(self._client.transport, 'close'):
                    await self._client.transport.close()
            except Exception as e:
                logger.warning(f"Error closing GraphQL client: {e}")

        self._client = None
        logger.info("Goldsky client cleaned up")

    @api_circuit_breaker
    @retry_async(max_attempts=3, initial_delay=1.0)
    @rate_limit_async(calls_per_second=5.0)
    async def get_large_recent_trades(
        self,
        min_value_usd: float = 10000.0,
        limit: int = 100,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get recent large trades from the orderbook subgraph.

        Args:
            min_value_usd: Minimum trade size in USD (default: 10,000)
            limit: Maximum number of trades to return (default: 100)
            hours: Number of hours to look back (default: 24)

        Returns:
            List of orderFilledEvents with large takerAmountFilled values
        """
        # Convert USD to base units (USDC uses 6 decimals, so 10,000 USD = 10,000,000,000 base units)
        min_taker_amount = str(int(min_value_usd * 1_000_000))

        # Calculate timestamp threshold
        start_timestamp = int((datetime.now() - timedelta(hours=hours)).timestamp())

        query = gql("""
            query LargeRecentTrades($minTakerAmount: BigInt!, $startTimestamp: BigInt!, $limit: Int!) {
                orderFilledEvents(
                    where: {
                        takerAmountFilled_gte: $minTakerAmount
                        timestamp_gte: $startTimestamp
                    }
                    orderBy: timestamp
                    orderDirection: desc
                    first: $limit
                ) {
                    id
                    transactionHash
                    timestamp
                    maker
                    taker
                    makerAssetId
                    takerAssetId
                    makerAmountFilled
                    takerAmountFilled
                    fee
                }
            }
        """)

        variables = {
            "minTakerAmount": min_taker_amount,
            "startTimestamp": start_timestamp,
            "limit": limit
        }

        try:
            if not self._client:
                raise APIError("Client not initialized. Call initialize() first.")

            result = await self._client.execute_async(query, variable_values=variables)
            events = result.get('orderFilledEvents', [])

            logger.info(f"Found {len(events)} large trades (>${min_value_usd:,.0f} USD)")
            return events

        except Exception as e:
            logger.error(f"Failed to fetch large trades: {e}")
            raise APIError(f"Failed to fetch large trades: {e}")

    def format_trade_usd(self, event: Dict[str, Any]) -> float:
        """
        Format takerAmountFilled from base units to USD.

        Args:
            event: OrderFilledEvent from subgraph

        Returns:
            Trade size in USD
        """
        try:
            taker_amount = int(event.get('takerAmountFilled', 0))
            # Convert from base units (6 decimals) to USD
            return taker_amount / 1_000_000
        except (ValueError, TypeError):
            return 0.0
