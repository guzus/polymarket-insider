# Goldsky Subgraph Integration

This document describes the enhanced Polymarket Insider system with Goldsky subgraph integration for advanced insider trading detection.

## Overview

The enhanced system uses Goldsky's Polymarket subgraphs to provide comprehensive insider trading detection with real-time monitoring capabilities. It combines traditional trade monitoring with advanced pattern analysis using blockchain data.

## New Features

### 🚀 Advanced Insider Detection

- **New Wallet Detection**: Identifies newly created wallets making large trades
- **Unusual Trade Patterns**: Detects trades significantly larger than a wallet's average
- **Market Timing Analysis**: Flags trading activity on markets about to expire
- **Behavioral Analysis**: Analyzes trading frequency and patterns
- **Multi-Trade Patterns**: Identifies wallets with multiple suspicious large trades

### 📊 Real-Time Subgraph Monitoring

- **GraphQL Integration**: Direct access to Polymarket's Goldsky subgraphs
- **Multi-Subgraph Support**: Orders, Positions, Activity, and Market data
- **Comprehensive Wallet Analysis**: Deep dive into wallet behavior and history
- **Market Context**: Understands market conditions and expiration timing

### 🎯 Enhanced Risk Assessment

- **Confidence Scoring**: 0-100% confidence levels for alerts
- **Risk Levels**: LOW, MEDIUM, HIGH, CRITICAL categorization
- **Pattern Recognition**: Multiple detection algorithms working together
- **Context-Aware**: Consider market conditions and wallet history

## Architecture

```
Enhanced System Architecture:
├── Traditional Monitoring (WebSocket + Polling)
├── Goldsky Subgraph Integration
│   ├── Orders Subgraph (Trade data)
│   ├── Positions Subgraph (User positions)
│   ├── Activity Subgraph (User activity history)
│   └── Market Subgraph (Market data)
├── Insider Detection Engine
│   ├── Pattern Recognition
│   ├── Behavioral Analysis
│   └── Risk Scoring
└── Enhanced Alert System
    └── Telegram Integration
```

## Detection Patterns

### 1. New Wallet Large Trade
- **Trigger**: New wallet (created < 24 hours ago) makes large trade
- **Confidence**: 60-90%
- **Risk Level**: HIGH

### 2. Unusually Large Trade
- **Trigger**: Trade is 5x+ larger than wallet's average trade size
- **Confidence**: 40-80%
- **Risk Level**: MEDIUM to HIGH

### 3. Expiring Market Activity
- **Trigger**: Large trades on markets expiring within 7 days
- **Confidence**: 50%
- **Risk Level**: MEDIUM

### 4. Sudden Activity
- **Trigger**: Low-frequency wallet suddenly makes large trades
- **Confidence**: 45%
- **Risk Level**: MEDIUM

### 5. Concentrated Trading
- **Trigger**: Wallet focusing on few markets with large trades
- **Confidence**: 35%
- **Risk Level**: LOW

### 6. Multi-Large Trade Pattern
- **Trigger**: Same wallet makes multiple large trades
- **Confidence**: 70%
- **Risk Level**: HIGH

## Configuration

### Environment Variables

Add these to your `.env` file:

```env
# Goldsky Subgraph Configuration
GOLDSKY_API_URL=https://api.goldsky.com/api/public/project_clqj02d9h3t099wqv50zr5w7f/subgraphs/poly-market
GOLDSKY_ORDERS_URL=https://api.goldsky.com/api/public/project_clqj02d9h3t099wqv50zr5w7f/subgraphs/poly-market-orders
GOLDSKY_POSITIONS_URL=https://api.goldsky.com/api/public/project_clqj02d9h3t099wqv50zr5w7f/subgraphs/poly-market-positions
GOLDSKY_ACTIVITY_URL=https://api.goldsky.com/api/public/project_clqj02d9h3t099wqv50zr5w7f/subgraphs/poly-market-activity

# Detection Thresholds
MIN_TRADE_SIZE_USD=10000
FUNDING_LOOKBACK_HOURS=24
TRADE_HISTORY_CHECK_DAYS=30
```

### Detection Settings

- **New Wallet Threshold**: 24 hours
- **Large Trade Multiplier**: 5x average trade size
- **Timing Suspicion**: Trading within 1 hour of funding
- **Minimum Confidence**: 30% for alerts

## Installation

1. **Install Dependencies**:
   ```bash
   pip install gql>=3.4.1 ujson>=5.8.0
   ```

2. **Update Configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Run Enhanced System**:
   ```bash
   python -m polymarket_insider
   ```

## Alert Format

### Insider Activity Alert

```
🚨 INSIDER ACTIVITY DETECTED 🚨

📊 Trade Details:
- Market: [Market Question]
- Size: $XX,XXX.XX
- Price: $X.XXXX
- Type: BUY/SELL
- Time: YYYY-MM-DD HH:MM:SS UTC

🔍 Risk Assessment:
- Risk Level: HIGH/MEDIUM/LOW
- Confidence: XX%

👛 Wallet Analysis:
- Address: 0x...
- New Wallet: Yes/No
- Total Activities: X
- Trading Frequency: X.XX/hr

🎯 Suspicious Patterns:
• Pattern description 1
• Pattern description 2

🔗 Transaction: [Etherscan Link]
```

## Performance Considerations

### Caching Strategy
- **Wallet Analysis**: Cached for 30 minutes
- **Market Data**: Cached for 1 hour
- **Processed Trades**: Prevents duplicate alerts

### Rate Limiting
- **GraphQL Queries**: 5 requests/second
- **Subgraph Monitoring**: 1 query/minute
- **Circuit Breaker**: Automatic failure handling

### Memory Management
- **Trade Cache**: Automatically cleared when > 50,000 entries
- **Regular Cleanup**: Old entries removed periodically

## Troubleshooting

### Common Issues

1. **GraphQL Connection Errors**:
   - Check Goldsky API URLs
   - Verify network connectivity
   - Check API rate limits

2. **Memory Usage**:
   - Monitor cache sizes
   - Adjust cleanup intervals
   - Check for memory leaks

3. **Missing Alerts**:
   - Verify confidence thresholds
   - Check trade size requirements
   - Review detection patterns

### Debug Mode

Enable debug logging:
```env
LOG_LEVEL=DEBUG
```

This will provide detailed information about:
- GraphQL queries and responses
- Pattern detection logic
- Cache operations
- Alert generation

## API Reference

### GoldskyClient Methods

- `get_recent_trades(limit, start_timestamp)`: Get recent trades
- `get_user_positions(user_address, limit)`: Get user positions
- `get_user_activity(user_address, hours)`: Get user activity
- `get_market_data(market_id)`: Get market information
- `get_large_trades(min_value_usd, hours)`: Get large trades
- `analyze_wallet_behavior(wallet_address)`: Comprehensive wallet analysis

### InsiderDetector Methods

- `analyze_trade_for_insider_activity(trade_data)`: Main detection method
- `get_market_insider_activity(market_id, hours)`: Market-specific analysis
- `clear_cache()`: Clear analysis caches

## Contributing

To contribute to the enhanced detection system:

1. **Add New Patterns**: Implement new detection algorithms in `InsiderDetector`
2. **Improve Queries**: Optimize GraphQL queries for better performance
3. **Enhance Analysis**: Add new behavioral analysis techniques
4. **Testing**: Add comprehensive tests for new features

## Security Considerations

- **API Keys**: Never commit API keys to repository
- **Rate Limiting**: Respect API rate limits
- **Data Privacy**: Handle wallet addresses responsibly
- **Error Handling**: Graceful degradation on API failures

## Future Enhancements

- **Machine Learning**: ML-based pattern recognition
- **Cross-Platform Analysis**: Integration with other prediction markets
- **Historical Analysis**: Long-term pattern analysis
- **Custom Alerts**: User-defined detection rules
- **Dashboard**: Web interface for monitoring and analysis