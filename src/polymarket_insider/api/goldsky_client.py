"""Goldsky Subgraph GraphQL client for Polymarket data."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal

import httpx
from gql import gql, Client
from gql.transport.httpx import HTTPXAsyncTransport
from gql.transport.websockets import WebsocketsTransport

from ..api.models import Trade, Market, Token, WalletFunding, WalletTradeHistory
from ..config.settings import settings
from ..exceptions import APIError
from ..utils.logger import setup_logger
from ..utils.retry import retry_async, rate_limit_async, api_circuit_breaker

logger = setup_logger(__name__)


class GoldskyClient:
    """GraphQL client for Goldsky Polymarket subgraphs."""

    def __init__(self):
        """Initialize the Goldsky client."""
        self.base_url = settings.goldsky_api_url
        self.orders_url = settings.goldsky_orders_url
        self.positions_url = settings.goldsky_positions_url
        self.activity_url = settings.goldsky_activity_url

        self._clients: Dict[str, Client] = {}
        self._http_client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        """Initialize GraphQL clients."""
        try:
            # Initialize HTTP client
            self._http_client = httpx.AsyncClient(timeout=settings.http_timeout)

            # Initialize GraphQL clients for different subgraphs
            transport_configs = {
                'base': self.base_url,
                'orders': self.orders_url,
                'positions': self.positions_url,
                'activity': self.activity_url
            }

            for name, url in transport_configs.items():
                # Create transport without sharing the http client
                transport = HTTPXAsyncTransport(url=url, timeout=settings.http_timeout)
                self._clients[name] = Client(transport=transport, fetch_schema_from_transport=True)

            logger.info("Goldsky GraphQL clients initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Goldsky clients: {e}")
            raise APIError(f"Failed to initialize Goldsky clients: {e}")

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._http_client:
            await self._http_client.aclose()

        for client in self._clients.values():
            try:
                # Close the transport session instead of the client
                if hasattr(client.transport, 'close'):
                    await client.transport.close()
            except Exception as e:
                logger.warning(f"Error closing GraphQL client: {e}")

        self._clients.clear()
        logger.info("Goldsky clients cleaned up")

    @api_circuit_breaker
    @retry_async(max_attempts=3, initial_delay=1.0)
    @rate_limit_async(calls_per_second=5.0)
    async def get_recent_trades(self, limit: int = 100,
                              start_timestamp: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent trades from the orders subgraph."""

        query = gql("""
            query getRecentTrades($limit: Int!, $startTimestamp: BigInt) {
                orders(
                    first: $limit,
                    orderBy: timestamp,
                    orderDirection: desc,
                    where: {
                        timestamp_gte: $startTimestamp,
                        type: "BUY"
                    }
                ) {
                    id
                    transactionHash
                    maker
                    taker
                    token {
                        id
                        outcome
                        market {
                            id
                            question
                            description
                            endDate
                            outcomes
                        }
                    }
                    price
                    amount
                    type
                    timestamp
                    blockNumber
                }
            }
        """)

        variables = {
            "limit": limit,
            "startTimestamp": start_timestamp or int((datetime.now() - timedelta(hours=1)).timestamp())
        }

        try:
            result = await self._clients['orders'].execute_async(query, variable_values=variables)
            return result.get('orders', [])
        except Exception as e:
            logger.error(f"Failed to fetch recent trades: {e}")
            raise APIError(f"Failed to fetch recent trades: {e}")

    @api_circuit_breaker
    @retry_async(max_attempts=3, initial_delay=1.0)
    @rate_limit_async(calls_per_second=5.0)
    async def get_user_positions(self, user_address: str,
                               limit: int = 50) -> List[Dict[str, Any]]:
        """Get user positions from the positions subgraph."""

        query = gql("""
            query getUserPositions($userAddress: String!, $limit: Int!) {
                positions(
                    first: $limit,
                    orderBy: timestamp,
                    orderDirection: desc,
                    where: {
                        user: $userAddress
                    }
                ) {
                    id
                    user
                    token {
                        id
                        outcome
                        market {
                            id
                            question
                            endDate
                        }
                    }
                    balance
                    price
                    value
                    timestamp
                    transactionHash
                }
            }
        """)

        variables = {
            "userAddress": user_address.lower(),
            "limit": limit
        }

        try:
            result = await self._clients['positions'].execute_async(query, variable_values=variables)
            return result.get('positions', [])
        except Exception as e:
            logger.error(f"Failed to fetch user positions: {e}")
            raise APIError(f"Failed to fetch user positions: {e}")

    @api_circuit_breaker
    @retry_async(max_attempts=3, initial_delay=1.0)
    @rate_limit_async(calls_per_second=3.0)
    async def get_user_activity(self, user_address: str,
                              hours: int = 24) -> List[Dict[str, Any]]:
        """Get user activity from the activity subgraph."""

        start_timestamp = int((datetime.now() - timedelta(hours=hours)).timestamp())

        query = gql("""
            query getUserActivity($userAddress: String!, $startTimestamp: BigInt!) {
                activities(
                    first: 100,
                    orderBy: timestamp,
                    orderDirection: desc,
                    where: {
                        user: $userAddress,
                        timestamp_gte: $startTimestamp
                    }
                ) {
                    id
                    user
                    type
                    token {
                        id
                        outcome
                        market {
                            id
                            question
                        }
                    }
                    amount
                    price
                    timestamp
                    transactionHash
                    blockNumber
                }
            }
        """)

        variables = {
            "userAddress": user_address.lower(),
            "startTimestamp": start_timestamp
        }

        try:
            result = await self._clients['activity'].execute_async(query, variable_values=variables)
            return result.get('activities', [])
        except Exception as e:
            logger.error(f"Failed to fetch user activity: {e}")
            raise APIError(f"Failed to fetch user activity: {e}")

    @api_circuit_breaker
    @retry_async(max_attempts=3, initial_delay=1.0)
    @rate_limit_async(calls_per_second=5.0)
    async def get_market_data(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Get market data from the base subgraph."""

        query = gql("""
            query getMarket($marketId: String!) {
                market(id: $marketId) {
                    id
                    question
                    description
                    endDate
                    outcomes
                    liquidity
                    volume
                    tokens {
                        id
                        outcome
                        price
                        supply
                    }
                    createdAt
                    lastUpdated
                }
            }
        """)

        variables = {
            "marketId": market_id.lower()
        }

        try:
            result = await self._clients['base'].execute_async(query, variable_values=variables)
            return result.get('market')
        except Exception as e:
            logger.error(f"Failed to fetch market data: {e}")
            raise APIError(f"Failed to fetch market data: {e}")

    @api_circuit_breaker
    @retry_async(max_attempts=3, initial_delay=1.0)
    @rate_limit_async(calls_per_second=5.0)
    async def get_large_trades(self, min_value_usd: float = 10000,
                             hours: int = 24) -> List[Dict[str, Any]]:
        """Get large trades that might indicate insider activity."""

        start_timestamp = int((datetime.now() - timedelta(hours=hours)).timestamp())

        query = gql("""
            query getLargeTrades($startTimestamp: BigInt!, $minAmount: String!) {
                orders(
                    first: 100,
                    orderBy: timestamp,
                    orderDirection: desc,
                    where: {
                        timestamp_gte: $startTimestamp,
                        amount_gte: $minAmount,
                        type: "BUY"
                    }
                ) {
                    id
                    transactionHash
                    maker
                    taker
                    token {
                        id
                        outcome
                        market {
                            id
                            question
                            description
                            endDate
                        }
                    }
                    price
                    amount
                    type
                    timestamp
                    blockNumber
                }
            }
        """)

        # Convert USD to token amount (simplified)
        min_amount = str(min_value_usd / 1000)  # Rough conversion

        variables = {
            "startTimestamp": start_timestamp,
            "minAmount": min_amount
        }

        try:
            result = await self._clients['orders'].execute_async(query, variable_values=variables)
            return result.get('orders', [])
        except Exception as e:
            logger.error(f"Failed to fetch large trades: {e}")
            raise APIError(f"Failed to fetch large trades: {e}")

    @api_circuit_breaker
    @retry_async(max_attempts=3, initial_delay=1.0)
    @rate_limit_async(calls_per_second=3.0)
    async def get_suspicious_patterns(self, hours: int = 24) -> Dict[str, List[Dict[str, Any]]]:
        """Get data for analyzing suspicious trading patterns."""

        start_timestamp = int((datetime.now() - timedelta(hours=hours)).timestamp())

        # Query for users with high concentration in recent trades
        query = gql("""
            query getSuspiciousPatterns($startTimestamp: BigInt!) {
                # Get recent large orders
                orders: orders(
                    first: 200,
                    orderBy: timestamp,
                    orderDirection: desc,
                    where: {
                        timestamp_gte: $startTimestamp,
                        type: "BUY"
                    }
                ) {
                    id
                    maker
                    taker
                    token {
                        id
                        outcome
                        market {
                            id
                            question
                            endDate
                        }
                    }
                    price
                    amount
                    timestamp
                    transactionHash
                }
            }
        """)

        variables = {
            "startTimestamp": start_timestamp
        }

        try:
            result = await self._clients['orders'].execute_async(query, variable_values=variables)
            return result
        except Exception as e:
            logger.error(f"Failed to fetch suspicious patterns: {e}")
            raise APIError(f"Failed to fetch suspicious patterns: {e}")

    async def analyze_wallet_behavior(self, wallet_address: str) -> Dict[str, Any]:
        """Comprehensive analysis of wallet behavior for insider detection."""

        try:
            # Get user activity
            activities = await self.get_user_activity(wallet_address, hours=72)

            # Get user positions
            positions = await self.get_user_positions(wallet_address)

            # Analyze patterns
            analysis = {
                'wallet_address': wallet_address,
                'total_activities': len(activities),
                'total_positions': len(positions),
                'first_activity': None,
                'last_activity': None,
                'trading_frequency': 0,
                'large_trades': [],
                'new_wallet': False,
                'suspicious_timing': []
            }

            if activities:
                timestamps = [int(activity['timestamp']) for activity in activities]
                analysis['first_activity'] = min(timestamps)
                analysis['last_activity'] = max(timestamps)

                # Calculate trading frequency (activities per hour)
                time_span = (max(timestamps) - min(timestamps)) / 3600  # Convert to hours
                if time_span > 0:
                    analysis['trading_frequency'] = len(activities) / time_span

                # Check if it's a new wallet (first activity within 24 hours)
                if analysis['first_activity'] >= int((datetime.now() - timedelta(hours=24)).timestamp()):
                    analysis['new_wallet'] = True

                # Identify large trades
                for activity in activities:
                    if activity['type'] in ['BUY', 'SELL']:
                        amount = float(activity['amount'])
                        if amount * float(activity.get('price', 1)) >= settings.min_trade_size_usd / 1000:
                            analysis['large_trades'].append(activity)

            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze wallet behavior: {e}")
            raise APIError(f"Failed to analyze wallet behavior: {e}")