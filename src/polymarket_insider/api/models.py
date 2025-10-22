"""Data models for Polymarket API responses."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class Token(BaseModel):
    """Token information."""
    token_id: str
    price: float
    outcome: str


class Market(BaseModel):
    """Market information."""
    question: str
    description: str
    end_date: Optional[datetime] = None
    tokens: List[Token]


class Trade(BaseModel):
    """Trade information."""
    maker: str
    taker: str
    price: float
    size: float
    side: str  # "BUY" or "SELL"
    token_id: str
    timestamp: datetime
    transaction_hash: str
    market_question: Optional[str] = None
    usd_size: Optional[float] = None


class WalletFunding(BaseModel):
    """Wallet funding information."""
    address: str
    amount: float
    token_address: str
    timestamp: datetime
    transaction_hash: str
    usd_value: Optional[float] = None


class WalletTradeHistory(BaseModel):
    """Wallet trade history summary."""
    address: str
    total_trades: int
    first_trade_date: Optional[datetime] = None
    last_trade_date: Optional[datetime] = None
    total_volume_usd: float = 0.0