#!/usr/bin/env python3
"""Test script to set up and verify Telegram bot functionality."""

import asyncio
import logging
from sys import exit

from telegram import Bot
from telegram.ext import Application
from src.polymarket_insider.config.settings import settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_bot():
    """Test bot functionality and set up group chat."""
    try:
        # Initialize bot
        bot = Bot(token=settings.telegram_bot_token)

        # Test bot info
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot connected successfully!")
        logger.info(f"🤖 Bot name: {bot_info.first_name}")
        logger.info(f"🆔 Bot username: @{bot_info.username}")
        logger.info(f"📱 Bot ID: {bot_info.id}")

        # Test sending a message to the target chat
        try:
            await bot.send_message(
                chat_id=settings.telegram_chat_id,
                text="🚀 *Polymarket Insider Bot is now active!* 🚀\n\n"
                     "I'm ready to monitor Polymarket for suspicious trading patterns.\n\n"
                     "Commands you can use:\n"
                     "/start - Welcome message\n"
                     "/help - Show help information\n"
                     "/status - Check bot status\n\n"
                     "Alerts will be sent automatically when suspicious activity is detected!",
                parse_mode="Markdown"
            )
            logger.info(f"✅ Test message sent successfully to {settings.telegram_chat_id}")
        except Exception as e:
            logger.error(f"❌ Failed to send test message: {e}")
            logger.info("💡 Make sure the bot is added to the group and has permission to send messages")
            return False

        return True

    except Exception as e:
        logger.error(f"❌ Bot setup failed: {e}")
        return False


async def main():
    """Main test function."""
    logger.info("🔧 Starting Telegram bot setup test...")

    # Check if configuration is valid
    if not settings.telegram_bot_token:
        logger.error("❌ Telegram bot token is not configured")
        exit(1)

    if not settings.telegram_chat_id:
        logger.error("❌ Telegram chat ID is not configured")
        exit(1)

    logger.info(f"📱 Bot token configured: {settings.telegram_bot_token[:10]}...")
    logger.info(f"💬 Target chat ID: {settings.telegram_chat_id}")

    # Test the bot
    success = await test_bot()

    if success:
        logger.info("🎉 Bot setup completed successfully!")
        logger.info(f"📝 Next steps:")
        logger.info(f"   1. Make sure the bot is added to the group '{settings.telegram_chat_id}'")
        logger.info(f"   2. The bot should now be ready to receive and send messages")
        logger.info(f"   3. Run the main application to start monitoring Polymarket")
    else:
        logger.error("❌ Bot setup failed. Please check the error messages above.")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())