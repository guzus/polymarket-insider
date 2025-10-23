"""Connection management for Polymarket API and WebSocket connections."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Callable, Optional, Dict, List

import httpx
import websockets
from websockets.client import WebSocketClientProtocol

from .api.models import Trade, Market, WalletFunding, WalletTradeHistory, Token
from .config.settings import settings
from .exceptions import ConnectionError, WebSocketError, APIError
from .utils.logger import setup_logger
from .utils.retry import retry_async, rate_limit_async, api_circuit_breaker

logger = setup_logger(__name__)


class ConnectionManager:
    """Manages connections to Polymarket API and WebSocket."""

    def __init__(self):
        """Initialize the connection manager."""
        self.api_base_url = settings.polymarket_api_url
        self.ws_url = settings.polymarket_ws_url
        self.websocket: Optional[WebSocketClientProtocol] = None
        self._markets_cache: Dict[str, Market] = {}
        self._markets_cache_updated: Optional[datetime] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        """Initialize connection manager resources."""
        self._http_client = httpx.AsyncClient(timeout=settings.http_timeout)
        # Warm up markets cache
        await self.get_markets()

    async def cleanup(self) -> None:
        """Clean up connection manager resources."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    @api_circuit_breaker
    @retry_async(max_attempts=3, initial_delay=1.0)
    @rate_limit_async(calls_per_second=10.0)
    async def get_markets(self) -> Dict[str, Market]:
        """Get markets with caching."""
        now = datetime.now()

        # Return cached markets if still valid
        if (self._markets_cache and self._markets_cache_updated and
            (now - self._markets_cache_updated) < timedelta(minutes=5)):
            return self._markets_cache

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{settings.polymarket_api_url}/markets")
                response.raise_for_status()

                markets_data = response.json()
                markets = {}

                # API returns {"data": [...]} format
                market_list = markets_data.get("data", []) if isinstance(markets_data, dict) else markets_data
                for market_data in market_list:
                    tokens = [
                        Token(
                            token_id=token["token_id"],
                            price=float(token["price"]),
                            outcome=token["outcome"]
                        ) for token in market_data.get("tokens", [])
                    ]

                    market = Market(
                        question=market_data.get("question", ""),
                        description=market_data.get("description", ""),
                        end_date=datetime.fromisoformat(market_data["end_date"])
                                if market_data.get("end_date") else None,
                        tokens=tokens
                    )

                    for token in market.tokens:
                        self._markets_cache[token.token_id] = market

                self._markets_cache_updated = now
                logger.info(f"Fetched {len(self._markets_cache)} markets")
                return self._markets_cache

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch markets: {e}")
            raise APIError(f"Failed to fetch markets: {e}")

    @api_circuit_breaker
    @retry_async(max_attempts=3, initial_delay=1.0)
    @rate_limit_async(calls_per_second=5.0)
    async def get_recent_trades(self, limit: int = 100) -> List[Trade]:
        """Get recent trades from Polymarket."""
        try:
            if not self._http_client:
                raise ConnectionError("Connection manager not initialized")

            response = await self._http_client.get(
                f"{settings.polymarket_api_url}/trades",
                params={"limit": limit}
            )
            response.raise_for_status()

            trades_data = response.json()
            trades = []
            markets = await self.get_markets()

            for trade_data in trades_data:
                trade = Trade(
                    maker=trade_data["maker"],
                    taker=trade_data["taker"],
                    price=float(trade_data["price"]),
                    size=float(trade_data["size"]),
                    side=trade_data["side"],
                    token_id=trade_data["token_id"],
                    timestamp=datetime.fromisoformat(trade_data["timestamp"]),
                    transaction_hash=trade_data["transaction_hash"],
                    market_question=markets.get(trade_data["token_id"], Market(question="")).question
                                   if trade_data["token_id"] in markets else None,
                    usd_size=float(trade_data["size"]) * float(trade_data["price"]) * 1000
                )
                trades.append(trade)

            return trades

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch recent trades: {e}")
            raise APIError(f"Failed to fetch recent trades: {e}")

    async def get_wallet_funding_history(self, address: str, hours: int = 24) -> List[WalletFunding]:
        """Get wallet funding history for the specified hours."""
        logger.info(f"Fetching funding history for wallet {address} in last {hours} hours")

        # TODO: Implement actual blockchain API integration
        return []

    @api_circuit_breaker
    @retry_async(max_attempts=2, initial_delay=2.0)
    @rate_limit_async(calls_per_second=2.0)
    async def get_wallet_trade_history(self, address: str, days: int = 30) -> WalletTradeHistory:
        """Get wallet trade history summary for the specified days."""
        try:
            if not self._http_client:
                raise ConnectionError("Connection manager not initialized")

            response = await self._http_client.get(
                f"{settings.polymarket_api_url}/trades",
                params={"maker": address, "taker": address, "limit": 1000}
            )
            response.raise_for_status()

            trades_data = response.json()

            if not trades_data:
                return WalletTradeHistory(
                    address=address,
                    total_trades=0,
                    total_volume_usd=0.0
                )

            timestamps = [
                datetime.fromisoformat(trade["timestamp"])
                for trade in trades_data
            ]

            first_trade = min(timestamps)
            last_trade = max(timestamps)

            total_volume = sum(
                float(trade["size"]) * float(trade["price"]) * 1000
                for trade in trades_data
            )

            return WalletTradeHistory(
                address=address,
                total_trades=len(trades_data),
                first_trade_date=first_trade,
                last_trade_date=last_trade,
                total_volume_usd=total_volume
            )

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch wallet trade history: {e}")
            raise APIError(f"Failed to fetch wallet trade history: {e}")

    async def connect_websocket(self, callback: Callable[[str], None]) -> WebSocketClientProtocol:
        """Connect to Polymarket WebSocket for real-time trade updates."""
        try:
            if self.websocket:
                await self.websocket.close()

            self.websocket = await websockets.connect(
                settings.polymarket_ws_url,
                ping_interval=settings.websocket_ping_interval,
                ping_timeout=settings.websocket_ping_timeout
            )
            logger.info("Connected to Polymarket WebSocket")

            # Subscribe to trades
            subscribe_message = {
                "type": "subscribe",
                "channel": "trades"
            }
            await self.websocket.send(json.dumps(subscribe_message))

            return self.websocket

        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            raise WebSocketError(f"Failed to connect to WebSocket: {e}")

    async def disconnect_websocket(self) -> None:
        """Disconnect from WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            logger.info("Disconnected from WebSocket")

    async def test_connectivity(self) -> bool:
        """Test connectivity to Polymarket API."""
        try:
            await self.get_markets()
            return True
        except Exception as e:
            logger.error(f"Connectivity test failed: {e}")
            return False