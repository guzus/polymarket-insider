"""Service for analyzing trades and detecting suspicious patterns."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ..api.models import Trade, WalletFunding, WalletTradeHistory, SuspiciousTradeAlert
from ..config.settings import settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class TradeAnalysisService:
    """Service for analyzing trades and managing suspicious trade detection."""

    def __init__(self):
        """Initialize the trade analysis service."""
        self._processed_trades: Dict[str, datetime] = {}
        self._max_processed_trades = 10000  # Prevent memory leaks

    def is_trade_processed(self, transaction_hash: str) -> bool:
        """Check if a trade has already been processed."""
        return transaction_hash in self._processed_trades

    def mark_trade_processed(self, transaction_hash: str) -> None:
        """Mark a trade as processed and cleanup old entries."""
        self._processed_trades[transaction_hash] = datetime.now()

        # Cleanup old entries to prevent memory leaks
        if len(self._processed_trades) > self._max_processed_trades:
            self._cleanup_old_processed_trades()

    def _cleanup_old_processed_trades(self) -> None:
        """Remove old processed trade entries."""
        cutoff_time = datetime.now() - timedelta(days=7)
        old_hashes = [
            hash_val for hash_val, timestamp in self._processed_trades.items()
            if timestamp < cutoff_time
        ]
        for hash_val in old_hashes:
            del self._processed_trades[hash_val]

    def should_analyze_trade(self, trade: Trade) -> bool:
        """Determine if a trade should be analyzed."""
        # Skip if already processed
        if self.is_trade_processed(trade.transaction_hash):
            return False

        # Skip trades below minimum size
        if trade.usd_size and trade.usd_size < settings.min_trade_size_usd:
            logger.debug(f"Trade too small: ${trade.usd_size:.2f}")
            return False

        # Skip trades older than 24 hours
        if datetime.now() - trade.timestamp > timedelta(hours=24):
            logger.debug(f"Trade too old: {trade.timestamp}")
            return False

        return True

    def prepare_wallet_analysis_context(
        self,
        trade: Trade,
        funding_history: List[WalletFunding],
        trade_history: WalletTradeHistory
    ) -> Dict[str, Any]:
        """Prepare analysis context for wallet assessment."""
        wallet_address = trade.maker if trade.side == "BUY" else trade.taker

        # Calculate funding statistics
        total_funding = sum(f.amount for f in funding_history)
        recent_funding = [
            f for f in funding_history
            if (datetime.now() - f.timestamp).total_seconds() < (settings.funding_lookback_hours * 3600)
        ]
        total_recent_funding = sum(f.amount for f in recent_funding)

        # Determine if wallet is new/low activity
        is_new_wallet = (
            trade_history.total_trades == 0 or
            (trade_history.first_trade_date and
             datetime.now() - trade_history.first_trade_date < timedelta(days=30))
        )
        is_low_activity = trade_history.total_trades < 10

        # Check for funding timing patterns
        has_recent_funding = len(recent_funding) > 0
        funding_matches_trade = (
            has_recent_funding and
            abs(total_recent_funding - trade.usd_size) < (trade.usd_size * 0.1)
        )

        return {
            'wallet_address': wallet_address,
            'trade': trade,
            'funding_history': funding_history,
            'trade_history': trade_history,
            'total_funding': total_funding,
            'total_recent_funding': total_recent_funding,
            'recent_funding_count': len(recent_funding),
            'is_new_wallet': is_new_wallet,
            'is_low_activity': is_low_activity,
            'has_recent_funding': has_recent_funding,
            'funding_matches_trade': funding_matches_trade,
            'hours_since_first_trade': (
                (datetime.now() - trade_history.first_trade_date).total_seconds() / 3600
                if trade_history.first_trade_date else None
            ),
            'hours_since_last_trade': (
                (datetime.now() - trade_history.last_trade_date).total_seconds() / 3600
                if trade_history.last_trade_date else None
            )
        }

    def generate_suspicious_activity_description(self, context: Dict[str, Any]) -> str:
        """Generate a description of suspicious activity for alerts."""
        trade = context['trade']
        reasons = []

        if context['is_new_wallet']:
            reasons.append(f"New wallet with no prior trading history")

        if context['has_recent_funding']:
            funding_desc = (
                f"Wallet received ${context['total_recent_funding']:,.2f} in funding "
                f"in the last {settings.funding_lookback_hours} hours"
            )
            reasons.append(funding_desc)

        if context['funding_matches_trade']:
            reasons.append("Trade size matches recent funding amount")

        if context['is_low_activity']:
            reasons.append(f"Low activity wallet (only {context['trade_history'].total_trades} prior trades)")

        # Add timing analysis
        hours_since_first = context['hours_since_first_trade']
        if hours_since_first and hours_since_first < 1:
            reasons.append("First trade occurred within 1 hour of wallet creation/funding")

        hours_since_last = context['hours_since_last_trade']
        if hours_since_last and hours_since_last > 168:  # 1 week
            reasons.append(f"Inactive wallet making trade after {hours_since_last/24:.1f} days")

        return "; ".join(reasons) if reasons else "Unusual trading pattern detected"

    def calculate_confidence_score(self, context: Dict[str, Any]) -> int:
        """Calculate confidence score for suspicious activity (0-100)."""
        score = 0

        # New wallet patterns (highest confidence)
        if context['is_new_wallet']:
            score += 40

        # Recent funding patterns (high confidence)
        if context['has_recent_funding']:
            score += 25
            if context['funding_matches_trade']:
                score += 20

        # Low activity patterns (medium confidence)
        if context['is_low_activity']:
            score += 15

        # Timing patterns
        hours_since_first = context['hours_since_first_trade']
        if hours_since_first and hours_since_first < 1:
            score += 15

        hours_since_last = context['hours_since_last_trade']
        if hours_since_last and hours_since_last > 168:
            score += 10

        # Recent funding count factor
        if context['recent_funding_count'] > 1:
            score += 10

        # Cap at 100
        return min(score, 100)

    def should_send_alert(self, context: Dict[str, Any]) -> bool:
        """Determine if an alert should be sent based on analysis."""
        # Always alert if confidence is high
        confidence = self.calculate_confidence_score(context)
        if confidence >= 70:
            return True

        # Alert for large trades even with lower confidence
        trade = context['trade']
        if trade.usd_size and trade.usd_size >= settings.min_trade_size_usd * 5:
            return confidence >= 50

        # Alert for very suspicious patterns even on smaller trades
        if context['funding_matches_trade'] and context['is_new_wallet']:
            return confidence >= 60

        return False

    def process_trade_analysis(self, context: Dict[str, Any]) -> Optional[SuspiciousTradeAlert]:
        """Process trade analysis and generate alert if appropriate."""
        if not self.should_send_alert(context):
            return None

        trade = context['trade']
        confidence = self.calculate_confidence_score(context)
        reason = self.generate_suspicious_activity_description(context)

        alert = SuspiciousTradeAlert(
            transaction_hash=trade.transaction_hash,
            market_question=trade.market_question,
            trade_size=trade.usd_size or 0,
            trade_price=trade.price,
            trade_side=trade.side,
            wallet_address=context['wallet_address'],
            confidence_score=confidence,
            reason=reason,
            timestamp=trade.timestamp,
            funding_history=context['funding_history'],
            trade_history=context['trade_history']
        )

        # Mark trade as processed
        self.mark_trade_processed(trade.transaction_hash)

        return alert