#!/usr/bin/env python3
"""
Script to start the Telegram bot and test functionality.
Includes group chat setup and testing.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from polymarket_insider.bot.telegram_bot import TelegramAlertBot
from polymarket_insider.utils.logger import setup_logger

# Setup logging
logger = setup_logger(__name__)

async def test_bot_functionality():
    """Test the bot functionality and send a test message."""
    bot = TelegramAlertBot()

    try:
        # Initialize the bot
        app = await bot.initialize()
        logger.info("✅ Bot initialized successfully")

        # Send a test message to the group
        test_message = """🤖 Polymarket Insider Bot - STARTUP SUCCESS 🤖

✅ Bot is now online and monitoring!
📊 Connected to Polymarket API
💬 Sending alerts to @uncanny_guzus

Bot Features:
- Monitors suspicious trading patterns
- Detects large trades from new wallets
- Tracks unusual market activity
- Sends real-time alerts to this group

Use /help to see all available commands."""

        success = await bot.send_message(test_message)
        if success:
            logger.info("✅ Test message sent successfully to @uncanny_guzus")
        else:
            logger.error("❌ Failed to send test message")

        return success

    except Exception as e:
        logger.error(f"❌ Error testing bot: {e}")
        return False

async def start_bot():
    """Start the bot with full functionality."""
    logger.info("🚀 Starting Polymarket Insider Telegram Bot...")

    # First test the bot
    test_success = await test_bot_functionality()

    if not test_success:
        logger.error("❌ Bot test failed. Please check the configuration.")
        return

    logger.info("✅ Bot test passed. Starting polling...")

    # Start the bot polling
    bot = TelegramAlertBot()
    try:
        await bot.start_polling()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
        await bot.stop()
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
        await bot.stop()

if __name__ == "__main__":
    print("🚀 Starting Polymarket Insider Telegram Bot...")
    print("📡 Target group: @uncanny_guzus")
    print("🔑 Using provided bot token")
    print("-" * 50)

    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("\n🛑 Bot shutdown requested")
    except Exception as e:
        print(f"❌ Fatal error: {e}")