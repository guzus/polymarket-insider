"""Polymarket API client."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import httpx
import websockets
from websockets.client import WebSocketClientProtocol

from ..config.settings import settings
from ..utils.logger import setup_logger
from .models import Trade, Market, WalletFunding, WalletTradeHistory

logger = setup_logger(__name__)


class PolymarketClient:
    """Client for interacting with Polymarket API."""

    def __init__(self):
        """Initialize the Polymarket client."""
        self.api_base_url = settings.polymarket_api_url
        self.ws_url = settings.polymarket_ws_url
        self.markets_cache: Dict[str, Market] = {}
        self.last_updated = datetime.now()

    async def get_markets(self) -> Dict[str, Market]:
        """Fetch all markets from Polymarket."""
        if self.markets_cache and (datetime.now() - self.last_updated).seconds < 300:
            return self.markets_cache

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.api_base_url}/markets")
                response.raise_for_status()

                markets_data = response.json()
                markets = {}

                for market_data in markets_data:
                    market = Market(
                        question=market_data.get("question", ""),
                        description=market_data.get("description", ""),
                        end_date=datetime.fromisoformat(market_data["end_date"]) if market_data.get("end_date") else None,
                        tokens=[
                            Token(
                                token_id=token["token_id"],
                                price=float(token["price"]),
                                outcome=token["outcome"]
                            ) for token in market_data.get("tokens", [])
                        ]
                    )

                    for token in market.tokens:
                        self.markets_cache[token.token_id] = market

                logger.info(f"Fetched {len(self.markets_cache)} markets")
                return self.markets_cache

            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch markets: {e}")
                return {}

    async def get_recent_trades(self, limit: int = 100) -> List[Trade]:
        """Get recent trades from Polymarket."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.api_base_url}/trades",
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
                        market_question=markets.get(trade_data["token_id"], {}).question if trade_data["token_id"] in markets else None
                    )

                    # Calculate USD size (this would need price oracle integration)
                    trade.usd_size = trade.size * trade.price * 1000  # Approximation

                    trades.append(trade)

                return trades

            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch recent trades: {e}")
                return []

    async def get_wallet_funding_history(self, address: str, hours: int = 24) -> List[WalletFunding]:
        """Get wallet funding history for the specified hours."""
        # This would typically require integration with Etherscan or similar blockchain API
        # For now, returning empty list as placeholder
        logger.info(f"Fetching funding history for wallet {address} in last {hours} hours")

        # TODO: Implement actual blockchain API integration
        # This would involve:
        # 1. Calling Etherscan API or similar
        # 2. Filtering for token transfers to the address
        # 3. Converting token amounts to USD value

        return []

    async def get_wallet_trade_history(self, address: str, days: int = 30) -> WalletTradeHistory:
        """Get wallet trade history summary for the specified days."""
        async with httpx.AsyncClient() as client:
            try:
                # This endpoint might not exist - would need to check Polymarket API docs
                response = await client.get(
                    f"{self.api_base_url}/trades",
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

                # Calculate trade history summary
                timestamps = [
                    datetime.fromisoformat(trade["timestamp"])
                    for trade in trades_data
                ]

                first_trade = min(timestamps)
                last_trade = max(timestamps)

                # Calculate total volume (approximate)
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
                return WalletTradeHistory(
                    address=address,
                    total_trades=0,
                    total_volume_usd=0.0
                )

    async def connect_websocket(self, callback) -> WebSocketClientProtocol:
        """Connect to Polymarket WebSocket for real-time trade updates."""
        try:
            websocket = await websockets.connect(self.ws_url)
            logger.info("Connected to Polymarket WebSocket")

            # Subscribe to trades
            subscribe_message = {
                "type": "subscribe",
                "channel": "trades"
            }
            await websocket.send(json.dumps(subscribe_message))

            return websocket

        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            raise