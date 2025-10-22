"""Suspicious trade detection algorithm."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Set
from dataclasses import dataclass

from ..api.models import Trade, WalletFunding, WalletTradeHistory
from ..config.settings import settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class SuspiciousTradeAlert:
    """Alert for suspicious trading activity."""
    trade: Trade
    reason: str
    wallet_address: str
    funding_amount: Optional[float] = None
    funding_time: Optional[datetime] = None
    previous_trades: int = 0
    confidence: float = 0.0  # 0.0 to 1.0


class SuspiciousTradeDetector:
    """Detects suspicious trading patterns on Polymarket."""

    def __init__(self):
        """Initialize the detector."""
        self.min_trade_size = settings.min_trade_size_usd
        self.funding_lookback_hours = settings.funding_lookback_hours
        self.trade_history_check_days = settings.trade_history_check_days

        # Track processed trades to avoid duplicate alerts
        self.processed_trades: Set[str] = set()

        # Cache for wallet analysis results
        self.wallet_analysis_cache: Dict[str, datetime] = {}

    async def analyze_trade(self, trade: Trade,
                           funding_history: List[WalletFunding],
                           trade_history: WalletTradeHistory) -> Optional[SuspiciousTradeAlert]:
        """Analyze a trade for suspicious patterns."""

        # Skip if already processed
        trade_key = f"{trade.transaction_hash}_{trade.maker}_{trade.taker}"
        if trade_key in self.processed_trades:
            return None

        self.processed_trades.add(trade_key)

        # Check 1: Large trade size
        if trade.usd_size and trade.usd_size >= self.min_trade_size:
            alert = await self._check_large_trade_patterns(trade, funding_history, trade_history)
            if alert:
                return alert

        # Check 2: New wallet behavior
        alert = await self._check_new_wallet_patterns(trade, funding_history, trade_history)
        if alert:
            return alert

        # Check 3: Recent funding patterns
        alert = await self._check_funding_patterns(trade, funding_history, trade_history)
        if alert:

            return alert

        return None

    async def _check_large_trade_patterns(self, trade: Trade,
                                         funding_history: List[WalletFunding],
                                         trade_history: WalletTradeHistory) -> Optional[SuspiciousTradeAlert]:
        """Check for patterns in large trades."""

        if not trade.usd_size or trade.usd_size < self.min_trade_size:
            return None

        # Primary wallet to check (maker or taker)
        wallet_address = trade.maker if trade.side == "BUY" else trade.taker

        # Calculate confidence based on trade size and wallet behavior
        confidence = min(0.3 + (trade.usd_size / self.min_trade_size) * 0.2, 0.9)

        reason_parts = [f"Large trade: ${trade.usd_size:,.2f}"]

        # Add context about wallet history
        if trade_history.total_trades == 0:
            reason_parts.append("New wallet (no previous trades)")
            confidence += 0.3
        elif trade_history.total_trades < 5:
            reason_parts.append(f"Low activity wallet ({trade_history.total_trades} total trades)")
            confidence += 0.2

        # Check for recent funding
        recent_funding = self._get_recent_funding(funding_history, wallet_address)
        if recent_funding:
            reason_parts.append(f"Recently funded ${recent_funding.amount:,.2f}")
            confidence += 0.2

        reason = "; ".join(reason_parts)
        confidence = min(confidence, 1.0)

        return SuspiciousTradeAlert(
            trade=trade,
            reason=reason,
            wallet_address=wallet_address,
            funding_amount=recent_funding.amount if recent_funding else None,
            funding_time=recent_funding.timestamp if recent_funding else None,
            previous_trades=trade_history.total_trades,
            confidence=confidence
        )

    async def _check_new_wallet_patterns(self, trade: Trade,
                                        funding_history: List[WalletFunding],
                                        trade_history: WalletTradeHistory) -> Optional[SuspiciousTradeAlert]:
        """Check for new wallet suspicious patterns."""

        wallet_address = trade.maker if trade.side == "BUY" else trade.taker

        # Skip if wallet has trading history
        if trade_history.total_trades > 0:
            return None

        # Check if this is a new wallet with recent funding
        recent_funding = self._get_recent_funding(funding_history, wallet_address)

        if not recent_funding:
            return None

        # Calculate confidence based on funding recency and amount
        hours_since_funding = (datetime.now() - recent_funding.timestamp).total_seconds() / 3600

        confidence = 0.0
        if hours_since_funding <= 1:
            confidence += 0.4
        elif hours_since_funding <= 6:
            confidence += 0.3
        elif hours_since_funding <= 24:
            confidence += 0.2

        if recent_funding.amount >= self.min_trade_size:
            confidence += 0.3
        elif recent_funding.amount >= self.min_trade_size * 0.5:
            confidence += 0.2

        if confidence < 0.5:
            return None

        reason = f"New wallet funded ${recent_funding.amount:,.2f} {hours_since_funding:.1f}h ago, immediately trading"

        return SuspiciousTradeAlert(
            trade=trade,
            reason=reason,
            wallet_address=wallet_address,
            funding_amount=recent_funding.amount,
            funding_time=recent_funding.timestamp,
            previous_trades=0,
            confidence=min(confidence, 1.0)
        )

    async def _check_funding_patterns(self, trade: Trade,
                                    funding_history: List[WalletFunding],
                                    trade_history: WalletTradeHistory) -> Optional[SuspiciousTradeAlert]:
        """Check for suspicious funding patterns."""

        wallet_address = trade.maker if trade.side == "BUY" else trade.taker

        # Get recent funding events
        recent_funding = self._get_recent_funding(funding_history, wallet_address)
        if not recent_funding:
            return None

        # Check if trade size matches recent funding amount closely
        if not trade.usd_size:
            return None

        funding_to_trade_ratio = recent_funding.amount / trade.usd_size

        # Suspicious if trade is very close to funding amount (within 10%)
        if 0.9 <= funding_to_trade_ratio <= 1.1:
            confidence = 0.7

            # Additional confidence if wallet has no history
            if trade_history.total_trades <= 1:
                confidence += 0.2

            reason = f"Trade amount (${trade.usd_size:,.2f}) closely matches recent funding (${recent_funding.amount:,.2f})"

            return SuspiciousTradeAlert(
                trade=trade,
                reason=reason,
                wallet_address=wallet_address,
                funding_amount=recent_funding.amount,
                funding_time=recent_funding.timestamp,
                previous_trades=trade_history.total_trades,
                confidence=min(confidence, 1.0)
            )

        return None

    def _get_recent_funding(self, funding_history: List[WalletFunding],
                          wallet_address: str) -> Optional[WalletFunding]:
        """Get the most recent funding event for a wallet within lookback period."""

        cutoff_time = datetime.now() - timedelta(hours=self.funding_lookback_hours)

        # Filter funding for this wallet within lookback period
        wallet_funding = [
            f for f in funding_history
            if f.address.lower() == wallet_address.lower()
            and f.timestamp >= cutoff_time
        ]

        if not wallet_funding:
            return None

        # Return most recent funding
        return max(wallet_funding, key=lambda f: f.timestamp)

    def clear_processed_trades(self, older_than_hours: int = 24):
        """Clear processed trades older than specified hours to prevent memory buildup."""

        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)

        # This is simplified - in practice you'd need to track timestamps
        # For now, just keep the cache size reasonable
        if len(self.processed_trades) > 10000:
            self.processed_trades.clear()
            logger.info("Cleared processed trades cache")