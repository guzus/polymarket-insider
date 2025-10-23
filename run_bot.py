#!/usr/bin/env python3
"""Simple script to run the Telegram bot for testing."""

import asyncio
import sys
import signal
from telegram.ext import Application

from src.polymarket_insider.bot.telegram_bot import TelegramAlertBot
from src.polymarket_insider.config.settings import settings

async def main():
    """Run the bot."""
    print("🤖 Starting Polymarket Insider Telegram Bot...")
    print(f"📱 Bot token: {settings.telegram_bot_token[:10]}...")
    print(f"💬 Target chat: {settings.telegram_chat_id}")
    print("📡 Bot is now running. Press Ctrl+C to stop.\n")
    
    bot = TelegramAlertBot()
    
    try:
        await bot.start_polling()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user.")
        await bot.stop()
    except Exception as e:
        print(f"\n❌ Bot error: {e}")
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
