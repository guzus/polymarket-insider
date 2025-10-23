"""Advanced insider trading detection using Goldsky subgraph data."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import statistics

from ..api.models import Trade, WalletFunding, WalletTradeHistory, SuspiciousTradeAlert
from ..api.goldsky_client import GoldskyClient
from ..config.settings import settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class InsiderAlert:
    """Enhanced alert for insider trading detection."""
    trade: Dict
    wallet_address: str
    confidence_score: float  # 0-100
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    reasons: List[str] = field(default_factory=list)
    wallet_analysis: Dict = field(default_factory=dict)
    market_context: Dict = field(default_factory=dict)
    behavioral_patterns: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class InsiderDetector:
    """Advanced insider trading detection using Goldsky subgraph data."""

    def __init__(self, goldsky_client: GoldskyClient):
        """Initialize the insider detector."""
        self.goldsky_client = goldsky_client
        self.min_trade_size_usd = settings.min_trade_size_usd
        self.funding_lookback_hours = settings.funding_lookback_hours
        self.trade_history_check_days = settings.trade_history_check_days

        # Cache for wallet analysis
        self.wallet_cache: Dict[str, Dict] = {}
        self.market_cache: Dict[str, Dict] = {}

        # Pattern detection thresholds
        self.new_wallet_threshold_hours = 24
        self.large_trade_multiplier = 5.0  # Trade is 5x larger than average
        self.timing_suspicion_threshold_minutes = 60  # Trading within 1 hour of funding

    async def analyze_trade_for_insider_activity(self, trade_data: Dict) -> Optional[InsiderAlert]:
        """Analyze a trade for insider trading patterns using subgraph data."""

        try:
            # Extract wallet addresses
            wallet_address = trade_data.get('maker', '').lower()
            if not wallet_address:
                return None

            # Get comprehensive wallet analysis
            wallet_analysis = await self._analyze_wallet_behavior(wallet_address)
            if not wallet_analysis:
                return None

            # Calculate trade size in USD
            trade_size_usd = self._calculate_trade_size_usd(trade_data)
            if trade_size_usd < self.min_trade_size_usd:
                return None

            # Get market context
            market_context = await self._get_market_context(trade_data)

            # Detect various insider patterns
            patterns = await self._detect_insider_patterns(trade_data, wallet_analysis, market_context)

            if not patterns:
                return None

            # Calculate confidence score and risk level
            confidence_score, risk_level = self._calculate_risk_score(patterns, trade_data, wallet_analysis)

            # Create alert if confidence is high enough
            if confidence_score >= 30:  # Minimum confidence threshold
                alert = InsiderAlert(
                    trade=trade_data,
                    wallet_address=wallet_address,
                    confidence_score=confidence_score,
                    risk_level=risk_level,
                    reasons=[pattern['description'] for pattern in patterns],
                    wallet_analysis=wallet_analysis,
                    market_context=market_context,
                    behavioral_patterns=[pattern['type'] for pattern in patterns]
                )

                logger.info(f"Insider activity detected: {risk_level} risk, {confidence_score}% confidence")
                return alert

            return None

        except Exception as e:
            logger.error(f"Error analyzing trade for insider activity: {e}")
            return None

    async def _analyze_wallet_behavior(self, wallet_address: str) -> Optional[Dict]:
        """Comprehensive wallet behavior analysis."""

        # Check cache first
        if wallet_address in self.wallet_cache:
            cache_time = self.wallet_cache[wallet_address].get('cache_time')
            if cache_time and (datetime.now() - cache_time) < timedelta(minutes=30):
                return self.wallet_cache[wallet_address]

        try:
            # Get wallet activity from subgraph
            activities = await self.goldsky_client.get_user_activity(wallet_address, hours=72)
            positions = await self.goldsky_client.get_user_positions(wallet_address)

            if not activities and not positions:
                return None

            analysis = {
                'wallet_address': wallet_address,
                'total_activities': len(activities),
                'total_positions': len(positions),
                'is_new_wallet': False,
                'trading_frequency': 0,
                'average_trade_size': 0,
                'max_trade_size': 0,
                'first_activity': None,
                'last_activity': None,
                'unique_markets': set(),
                'buy_sell_ratio': 0,
                'timing_patterns': [],
                'cache_time': datetime.now()
            }

            if activities:
                # Analyze activity patterns
                timestamps = []
                trade_sizes = []
                buy_count = 0
                sell_count = 0

                for activity in activities:
                    timestamps.append(int(activity['timestamp']))

                    if activity['type'] in ['BUY', 'SELL']:
                        size = float(activity['amount']) * float(activity.get('price', 1))
                        trade_sizes.append(size)

                        if activity['type'] == 'BUY':
                            buy_count += 1
                        else:
                            sell_count += 1

                    # Track unique markets
                    if 'token' in activity and 'market' in activity['token']:
                        analysis['unique_markets'].add(activity['token']['market']['id'])

                # Calculate metrics
                if timestamps:
                    analysis['first_activity'] = min(timestamps)
                    analysis['last_activity'] = max(timestamps)

                    # Check if new wallet (first activity within 24 hours)
                    if analysis['first_activity'] >= int((datetime.now() - timedelta(hours=24)).timestamp()):
                        analysis['is_new_wallet'] = True

                    # Calculate trading frequency
                    time_span = (max(timestamps) - min(timestamps)) / 3600  # hours
                    if time_span > 0:
                        analysis['trading_frequency'] = len(activities) / time_span

                if trade_sizes:
                    analysis['average_trade_size'] = statistics.mean(trade_sizes)
                    analysis['max_trade_size'] = max(trade_sizes)

                # Calculate buy/sell ratio
                total_trades = buy_count + sell_count
                if total_trades > 0:
                    analysis['buy_sell_ratio'] = buy_count / total_trades

                analysis['unique_markets'] = len(analysis['unique_markets'])

            # Cache the analysis
            self.wallet_cache[wallet_address] = analysis
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing wallet behavior for {wallet_address}: {e}")
            return None

    async def _get_market_context(self, trade_data: Dict) -> Dict:
        """Get market context for the trade."""

        try:
            token_id = trade_data.get('token', {}).get('id')
            if not token_id:
                return {}

            market_data = trade_data.get('token', {}).get('market', {})
            market_id = market_data.get('id')

            if not market_id:
                return {}

            # Check cache
            if market_id in self.market_cache:
                cache_time = self.market_cache[market_id].get('cache_time')
                if cache_time and (datetime.now() - cache_time) < timedelta(hours=1):
                    return self.market_cache[market_id]

            # Fetch detailed market data
            detailed_market = await self.goldsky_client.get_market_data(market_id)

            context = {
                'market_id': market_id,
                'question': market_data.get('question', ''),
                'description': market_data.get('description', ''),
                'end_date': market_data.get('endDate'),
                'time_to_expiry': None,
                'is_expiring_soon': False,
                'liquidity': 0,
                'volume': 0,
                'cache_time': datetime.now()
            }

            if detailed_market:
                context.update({
                    'liquidity': float(detailed_market.get('liquidity', 0)),
                    'volume': float(detailed_market.get('volume', 0))
                })

            # Calculate time to expiry
            if context['end_date']:
                end_timestamp = int(context['end_date'])
                current_timestamp = int(datetime.now().timestamp())
                time_to_expiry_hours = (end_timestamp - current_timestamp) / 3600
                context['time_to_expiry'] = time_to_expiry_hours

                # Flag if expiring within 7 days
                if 0 < time_to_expiry_hours <= 168:
                    context['is_expiring_soon'] = True

            self.market_cache[market_id] = context
            return context

        except Exception as e:
            logger.error(f"Error getting market context: {e}")
            return {}

    async def _detect_insider_patterns(self, trade_data: Dict, wallet_analysis: Dict, market_context: Dict) -> List[Dict]:
        """Detect various insider trading patterns."""

        patterns = []
        trade_size_usd = self._calculate_trade_size_usd(trade_data)

        # Pattern 1: New wallet with large initial trade
        if wallet_analysis.get('is_new_wallet') and trade_size_usd >= self.min_trade_size_usd * 2:
            patterns.append({
                'type': 'NEW_WALLET_LARGE_TRADE',
                'description': f"New wallet making large initial trade: ${trade_size_usd:,.2f}",
                'confidence': 60,
                'severity': 'HIGH'
            })

        # Pattern 2: Unusually large trade for this wallet
        if trade_size_usd > 0 and wallet_analysis.get('average_trade_size', 0) > 0:
            size_multiplier = trade_size_usd / wallet_analysis['average_trade_size']
            if size_multiplier >= self.large_trade_multiplier:
                patterns.append({
                    'type': 'UNUSUALLY_LARGE_TRADE',
                    'description': f"Trade is {size_multiplier:.1f}x larger than wallet's average",
                    'confidence': min(40 + (size_multiplier - 5) * 10, 80),
                    'severity': 'HIGH' if size_multiplier >= 10 else 'MEDIUM'
                })

        # Pattern 3: Trading on expiring markets (potential insider knowledge)
        if market_context.get('is_expiring_soon') and trade_size_usd >= self.min_trade_size_usd:
            patterns.append({
                'type': 'EXPIRING_MARKET_ACTIVITY',
                'description': f"Large trade on market expiring in {market_context['time_to_expiry']:.1f} hours",
                'confidence': 50,
                'severity': 'MEDIUM'
            })

        # Pattern 4: Low-frequency wallet suddenly active
        if (wallet_analysis.get('trading_frequency', 0) < 0.1 and  # Less than 1 trade per 10 hours
            trade_size_usd >= self.min_trade_size_usd):
            patterns.append({
                'type': 'SUDDEN_ACTIVITY',
                'description': f"Low-frequency wallet (freq: {wallet_analysis['trading_frequency']:.2f}/hr) making large trade",
                'confidence': 45,
                'severity': 'MEDIUM'
            })

        # Pattern 5: Concentrated trading (single market focus)
        if (wallet_analysis.get('unique_markets', 1) <= 2 and
            trade_size_usd >= self.min_trade_size_usd * 1.5):
            patterns.append({
                'type': 'CONCENTRATED_TRADING',
                'description': f"Wallet focusing on {wallet_analysis['unique_markets']} market(s) with large trade",
                'confidence': 35,
                'severity': 'LOW'
            })

        # Pattern 6: Extreme buy/sell imbalance
        buy_sell_ratio = wallet_analysis.get('buy_sell_ratio', 0.5)
        if buy_sell_ratio >= 0.9 or buy_sell_ratio <= 0.1:
            direction = "buying" if buy_sell_ratio >= 0.9 else "selling"
            patterns.append({
                'type': 'IMBALANCED_TRADING',
                'description': f"Wallet almost exclusively {direction} (ratio: {buy_sell_ratio:.2f})",
                'confidence': 30,
                'severity': 'LOW'
            })

        return patterns

    def _calculate_trade_size_usd(self, trade_data: Dict) -> float:
        """Calculate trade size in USD."""
        try:
            amount = float(trade_data.get('amount', 0))
            price = float(trade_data.get('price', 0))
            return amount * price * 1000  # Approximate USD conversion
        except (ValueError, TypeError):
            return 0

    def _calculate_risk_score(self, patterns: List[Dict], trade_data: Dict, wallet_analysis: Dict) -> Tuple[float, str]:
        """Calculate overall risk score and level."""

        if not patterns:
            return 0, 'LOW'

        # Base confidence from patterns
        total_confidence = sum(p['confidence'] for p in patterns)
        pattern_count = len(patterns)
        avg_confidence = total_confidence / pattern_count

        # Adjustments based on wallet and trade characteristics
        multiplier = 1.0

        # Increase confidence for larger trades
        trade_size_usd = self._calculate_trade_size_usd(trade_data)
        if trade_size_usd >= self.min_trade_size_usd * 5:
            multiplier += 0.3
        elif trade_size_usd >= self.min_trade_size_usd * 2:
            multiplier += 0.15

        # Increase confidence for new wallets
        if wallet_analysis.get('is_new_wallet'):
            multiplier += 0.4

        # Increase confidence for multiple patterns
        if pattern_count >= 3:
            multiplier += 0.3
        elif pattern_count >= 2:
            multiplier += 0.15

        # Calculate final score
        final_score = min(avg_confidence * multiplier, 100)

        # Determine risk level
        if final_score >= 80:
            risk_level = 'CRITICAL'
        elif final_score >= 60:
            risk_level = 'HIGH'
        elif final_score >= 40:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'

        return round(final_score, 1), risk_level

    async def get_market_insider_activity(self, market_id: str, hours: int = 24) -> List[InsiderAlert]:
        """Get insider activity analysis for a specific market."""

        try:
            # Get recent trades for this market
            large_trades = await self.goldsky_client.get_large_trades(
                min_value_usd=self.min_trade_size_usd,
                hours=hours
            )

            alerts = []
            for trade in large_trades:
                # Filter for this specific market
                if trade.get('token', {}).get('market', {}).get('id') == market_id.lower():
                    alert = await self.analyze_trade_for_insider_activity(trade)
                    if alert:
                        alerts.append(alert)

            return alerts

        except Exception as e:
            logger.error(f"Error getting market insider activity: {e}")
            return []

    def clear_cache(self) -> None:
        """Clear analysis caches."""
        self.wallet_cache.clear()
        self.market_cache.clear()
        logger.info("Insider detector caches cleared")