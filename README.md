# Polymarket Insider

<img src="https://github.com/user-attachments/assets/4c21c7c4-440d-4f1f-a5fe-91128158aebf" width="50%">

🔍 **Track large trades on Polymarket with detailed market and trader insights via Telegram bot**

Polymarket Insider monitors Polymarket for large trading activity, providing comprehensive alerts that include:

- **Market names and outcomes** - Human-readable market questions instead of token IDs
- **Trade direction** - Clear BUY/SELL indicators with visual indicators
- **Detailed trader profiles** - Names, pseudonyms, activity levels, and trading history
- **Direct profile links** - Click through to view complete Polymarket trader profiles
- **Smart filtering** - Configurable thresholds to focus on significant trades

## ✨ Key Features

- 🎯 **Market Intelligence**: Full market names and questions from Polymarket Gamma API
- 📊 **Trade Direction**: Automatic BUY/SELL detection with color-coded indicators
- 👤 **Trader Profiles**: Detailed trader information including activity levels and volume
- 🔗 **Profile Links**: Direct links to Polymarket trader profiles for due diligence
- 🤖 **Telegram Integration**: Instant, richly-formatted alerts with actionable information
- 🚀 **High Performance**: Multi-API integration with intelligent caching
- 🛡️ **Robust Architecture**: Graceful error handling and comprehensive logging
- ⚙️ **Configurable**: Adjustable thresholds and monitoring parameters

## 🏗️ Architecture

The application uses a sophisticated multi-API architecture:

```
src/polymarket_insider/
├── api/                    # API integration layer
│   ├── goldsky_client.py   # Goldsky Orderbook GraphQL client
│   ├── gamma_client.py     # Polymarket Gamma API client
│   └── data_api_client.py  # Polymarket Data API client
├── bot/                   # Telegram bot integration
│   └── telegram_bot.py    # Telegram bot implementation
├── config/                # Configuration management
│   ├── settings.py        # Application settings
│   └── validator.py       # Configuration validation
├── utils/                 # Utilities
│   ├── logger.py          # Logging configuration
│   └── retry.py           # Retry mechanisms
├── container.py           # Dependency injection
├── large_trade_monitor.py # Main monitoring logic
├── main.py               # Application entry point
└── __init__.py
```

## 🚀 Installation

### Prerequisites

- Python 3.11 or higher
- UV (recommended) or pip
- Telegram Bot Token and Chat ID

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

## ⚙️ Configuration

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
MIN_TRADE_SIZE_USD=100000         # Minimum trade size to trigger alert (default: $100k)

# API Configuration
HTTP_TIMEOUT=30                   # API request timeout in seconds
GOLDSKY_ORDERBOOK_URL=https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn

# Monitoring Configuration
POLLING_INTERVAL_SECONDS=60       # How often to check for new trades

# Logging Configuration
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
```

### Setting up Telegram Bot

1. Create a new bot with [@BotFather](https://t.me/botfather) on Telegram
2. Get your bot token
3. Get your chat ID (you can use [@userinfobot](https://t.me/userinfobot) to find it)
4. Add both to your `.env` file

## 🎯 Usage

### Command Line

```bash
# Run the application
uv run python -m polymarket_insider

# Or using Python module directly
python -m polymarket_insider
```

### Development Mode

```bash
# Install development dependencies
uv sync --dev

# Run with development settings
python -m polymarket_insider
```

## 📱 Alert Format

The bot sends richly-formatted alerts with comprehensive information:

### 🟢 BUY Alert Example

```
🟢 LARGE TRADE ALERT 🟢

📊 Trade Details:
• Size: $482,414.91
• Action: BUY Yes
• Amount: $100,000.00
• Fee: $0.50
• Time: 2025-10-24 02:40:34 UTC

🎯 Market:
• Will How to Train Your Dragon be the top grossing movie of 2025?

👤 Taker:
• tmry-st "Sandy-Doctrine" (Activity: high • Markets: 11 • Recent Volume: $672,241)
• [View Profile](https://polymarket.com/profile/0x63274ff0...)
• `0x6327...5e92`

🔗 Transaction: [View on Polygonscan](https://polygonscan.com/tx/...)
```

### 🔴 SELL Alert Example

```
🔴 LARGE TRADE ALERT 🔴

📊 Trade Details:
• Size: $135,000.00
• Action: SELL No
• Amount: $135,000.00
• Fee: $0.67
• Time: 2025-10-24 02:40:36 UTC

🎯 Market:
• Will Ethereum be above $4,000 by end of 2025?

👤 Taker:
• crypto_whale "Bearish-Believer" (Activity: medium • Markets: 23 • Recent Volume: $2,845,120)
• [View Profile](https://polymarket.com/profile/0xabc123...)
• `0xabc1...def0`

🔗 Transaction: [View on Polygonscan](https://polygonscan.com/tx/...)
```

## 🔍 Alert Information

Each alert includes:

### 📊 Trade Details
- **Size**: Total USD value of the trade
- **Action**: Trade direction (BUY/SELL) and outcome (Yes/No)
- **Amount**: Specific amount traded in USD
- **Fee**: Transaction fee paid
- **Time**: Timestamp of the trade

### 🎯 Market Information
- **Market Name**: Human-readable market question
- **Context**: Full market context for understanding the trade

### 👤 Trader Profile
- **Name & Pseudonym**: Trader's display name and pseudonym
- **Activity Level**: Trading frequency (very high/high/medium/low)
- **Market Diversity**: Number of unique markets traded
- **Recent Volume**: Recent trading volume in USD
- **Profile Link**: Direct link to Polymarket profile
- **Wallet Address**: Truncated wallet address for reference

## 📊 API Integration

### Goldsky Orderbook Subgraph
- Fetches real-time trade data from Polymarket orderbook
- Provides transaction details, amounts, and participant addresses
- Updated every 60 seconds for comprehensive coverage

### Polymarket Gamma API
- Supplies market names, questions, and token mappings
- Maps token IDs to human-readable market information
- Caches data for 15 minutes to optimize performance

### Polymarket Data API
- Provides detailed trader profiles and activity data
- Analyzes trading patterns, frequency, and volume
- Caches trader information for 30 minutes

## ⚙️ Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `MIN_TRADE_SIZE_USD` | Minimum trade size in USD to trigger alert | 100000 |
| `HTTP_TIMEOUT` | API request timeout in seconds | 30 |
| `POLLING_INTERVAL_SECONDS` | Trade monitoring check interval | 60 |
| `LOG_LEVEL` | Logging verbosity level | INFO |

## 🐳 Docker Deployment

### Quick Start

```bash
# Clone and setup
git clone https://github.com/guzus/polymarket-insider.git
cd polymarket-insider
cp .env.example .env
# Edit .env with your configuration

# Build and run
docker build -t polymarket-insider .
docker run -d --env-file .env --name polymarket-insider polymarket-insider
```

### Docker Compose

```bash
# Using docker-compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

## 🔧 Development

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

## 🚀 Production Deployment

### Environment Setup

For production deployment, ensure:

1. **Environment Variables**: All required variables are properly configured
2. **Resource Limits**: Appropriate memory and CPU limits set
3. **Monitoring**: Logging and health checks configured
4. **Security**: Proper bot token management and access control

### Monitoring

The application provides comprehensive logging:

```bash
# View application logs
docker logs polymarket-insider

# Follow logs in real-time
docker logs -f polymarket-insider
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This tool is for educational and research purposes only. It does not provide financial advice. Always do your own research before making any trading decisions.

The information provided is based on publicly available data from Polymarket and should not be used as the sole basis for any investment decisions.

## 🆘 Support

If you encounter any issues or have questions, please open an issue on the GitHub repository with:

- Detailed description of the problem
- Error messages or logs (if applicable)
- Steps to reproduce the issue
- Your environment details (OS, Python version, etc.)

---

**Built with ❤️ for the Polymarket community**