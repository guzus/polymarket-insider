#!/usr/bin/env python3
"""Simple script to test the Telegram bot and get chat ID."""

import asyncio
from telegram import Bot
from polymarket_insider.config.settings import settings


async def test_bot():
    """Test bot and show instructions for getting chat ID."""
    print("=" * 50)
    print("Polymarket Insider Bot Setup")
    print("=" * 50)

    bot = Bot(token=settings.telegram_bot_token)

    try:
        # Get bot info
        bot_info = await bot.get_me()
        print(f"✅ Bot Details:")
        print(f"   Name: {bot_info.full_name}")
        print(f"   Username: @{bot_info.username}")
        print(f"   Bot ID: {bot_info.id}")

        print(f"\n📱 Bot is working!")
        print(f"\nNext steps to get your Chat ID:")
        print(f"1. Open Telegram")
        print(f"2. Search for: @{bot_info.username}")
        print(f"3. Start a chat with the bot")
        print(f"4. Send any message (like 'hello')")
        print(f"5. The bot will respond with your Chat ID")

        print(f"\nFor a group chat (uncanny_guzus):")
        print(f"1. Create a new group in Telegram")
        print(f"2. Name it 'uncanny_guzus' or similar")
        print(f"3. Add @{bot_info.username} to the group")
        print(f"4. Send a message in the group")
        print(f"5. The bot will respond with the group Chat ID")

        print(f"\nOnce you have the Chat ID:")
        print(f"1. Update your .env file:")
        print(f"   TELEGRAM_CHAT_ID=your_chat_id_here")
        print(f"2. Run: python setup_bot.py --test")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"\nPlease check:")
        print(f"1. Bot token is correct")
        print(f"2. Bot is properly created in Telegram")
        return False


if __name__ == "__main__":
    asyncio.run(test_bot())