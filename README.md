# Polymarket Insider

🔍 **Track suspicious large trades on Polymarket and get alerts via Telegram bot**

Polymarket Insider monitors Polymarket for potentially manipulative trading activity, specifically looking for:

- Large trades from newly created wallets
- Wallets that are funded immediately before making large trades
- Wallets with no prior trading history making significant trades

## Features

- 🚀 Real-time trade monitoring via WebSocket connection
- 🤖 Telegram bot integration for instant alerts
- 🔍 Advanced suspicious pattern detection algorithms
- 📊 Configurable alert thresholds
- 🛡️ Graceful error handling and fallback mechanisms
- 📝 Comprehensive logging

## Installation

### Using UV (Recommended)

```bash
# Clone the repository
git clone https://github.com/guzus/polymarket-insider.git
cd polymarket-insider

# Install dependencies with UV
uv sync

# Install in development mode
uv pip install -e .
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/guzus/polymarket-insider.git
cd polymarket-insider

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

## Configuration

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit the `.env` file with your configuration:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# Trade Detection Configuration
MIN_TRADE_SIZE_USD=10000          # Minimum trade size to trigger alert
FUNDING_LOOKBACK_HOURS=24         # Hours to look back for wallet funding
TRADE_HISTORY_CHECK_DAYS=30       # Days to check for trade history

# Logging Configuration
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
```

### Setting up Telegram Bot

1. Create a new bot with [@BotFather](https://t.me/botfather) on Telegram
2. Get your bot token
3. Get your chat ID (you can use [@userinfobot](https://t.me/userinfobot) to find it)
4. Add both to your `.env` file

## Usage

### Command Line

```bash
# Run the application
polymarket-insider

# Or using Python module
python -m polymarket_insider
```

### Development Mode

```bash
# Install development dependencies
uv sync --dev

# Run with development settings
python -m polymarket_insider
```

## Alert Types

The bot detects and alerts on several suspicious patterns:

### 1. Large New Wallet Trades
- New wallets (no previous trades) making large transactions
- High confidence alerts for wallets funded immediately before trading

### 2. Recent Funding Patterns
- Wallets that received funding within the lookback period
- Trades that closely match recent funding amounts
- Temporal proximity analysis between funding and trading

### 3. Low Activity Wallets
- Wallets with minimal trading history suddenly making large trades
- Pattern analysis to identify potentially suspicious behavior

## Alert Format

🔴 **SUSPICIOUS TRADE DETECTED** 🔴

📊 **Trade Details:**
- Market: [Market Question]
- Size: $XX,XXX.XX
- Price: $X.XXXX
- Side: BUY/SELL
- Time: YYYY-MM-DD HH:MM:SS UTC

🔍 **Suspicious Activity:**
- Detailed explanation of suspicious patterns

👛 **Wallet Analysis:**
- Address: `0x...`
- Previous Trades: X
- Confidence: XX%

🔗 **Transaction:** [View on Etherscan](link)

## Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `MIN_TRADE_SIZE_USD` | Minimum trade size in USD to trigger alert | 10000 |
| `FUNDING_LOOKBACK_HOURS` | Hours to look back for wallet funding | 24 |
| `TRADE_HISTORY_CHECK_DAYS` | Days to check for trade history | 30 |
| `LOG_LEVEL` | Logging verbosity level | INFO |

## Development

### Code Quality

```bash
# Format code
uv run black src/

# Lint code
uv run ruff check src/

# Type checking
uv run mypy src/
```

### Testing

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src/polymarket_insider
```

## Architecture

```
src/polymarket_insider/
├── api/                    # Polymarket API integration
│   ├── client.py          # Main API client
│   └── models.py          # Data models
├── bot/                   # Telegram bot integration
│   └── telegram_bot.py    # Telegram bot implementation
├── detector/              # Suspicious pattern detection
│   └── suspicious_trade_detector.py
├── config/                # Configuration management
│   └── settings.py        # Application settings
├── utils/                 # Utilities
│   └── logger.py          # Logging configuration
├── trade_tracker.py       # Main tracking logic
├── main.py               # Application entry point
└── __init__.py
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational and research purposes only. It does not provide financial advice. Always do your own research before making any trading decisions.

## Support

If you encounter any issues or have questions, please open an issue on the GitHub repository.