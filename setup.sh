#!/bin/bash

# Polymarket Insider Setup Script

set -e

echo "🚀 Setting up Polymarket Insider..."

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "❌ UV is not installed. Please install UV first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ UV found"

# Create virtual environment and install dependencies
echo "📦 Installing dependencies..."
uv sync

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your Telegram bot token and chat ID"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Telegram bot configuration"
echo "2. Run the application: uv run polymarket-insider"
echo "3. Or use Python module: python -m polymarket_insider"
echo ""
echo "For help setting up Telegram bot, see README.md"