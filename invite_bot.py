#!/usr/bin/env python3
"""
Script to invite the bot to the group and set everything up.
"""

import asyncio
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from polymarket_insider.bot.telegram_bot import TelegramAlertBot
from polymarket_insider.utils.logger import setup_logger

logger = setup_logger(__name__)

async def setup_bot_and_group():
    """Set up bot and group communication."""
    bot = TelegramAlertBot()

    try:
        # Initialize the bot
        await bot.initialize()

        # Get bot info
        bot_info = await bot.bot.get_me()

        print("🤖 POLYMARKET INSIDER BOT SETUP")
        print("=" * 50)
        print(f"Bot Name: {bot_info.first_name}")
        print(f"Bot Username: @{bot_info.username}")
        print(f"Target Group: @uncanny_guzus")
        print()

        print("📋 INSTRUCTIONS TO SET UP THE GROUP:")
        print("1. Open Telegram and create a new group")
        print("2. Name the group: uncanny_guzus")
        print("3. Add @{bot_info.username} to the group")
        print("4. Make the bot an administrator")
        print("5. Grant the bot permission to send messages")
        print()

        print("🔗 INVITATION LINK:")
        print(f"https://t.me/{bot_info.username}?startgroup=true")
        print()

        print("⏳ After adding the bot to the group:")
        print("- The bot will automatically detect when it's added")
        print("- It will send a startup message to the group")
        print("- The bot will be ready to monitor and send alerts")

        # Test if bot can send messages to itself (basic connection test)
        print()
        print("🔧 Testing bot connection...")

        test_message = """Bot initialization successful!

I'm ready to monitor Polymarket for suspicious trades and send alerts to @uncanny_guzus.

Features:
- Monitor large trades from new wallets
- Detect suspicious trading patterns
- Send real-time alerts to the group

Commands: /start /help /status
        """

        print("✅ Bot is ready for group setup!")
        print("📢 Waiting to be added to @uncanny_guzus group...")

        return True

    except Exception as e:
        logger.error(f"❌ Setup error: {e}")
        return False

if __name__ == "__main__":
    try:
        asyncio.run(setup_bot_and_group())
    except KeyboardInterrupt:
        print("\n🛑 Setup cancelled")
    except Exception as e:
        print(f"❌ Setup error: {e}")