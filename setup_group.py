#!/usr/bin/env python3
"""Script to help set up the Telegram group and invite the user."""

import asyncio
import sys
from telegram import Bot, Update
from telegram.ext import Application

async def create_group_and_invite():
    """Bot instructions for group setup."""
    print("🤖 *Telegram Bot Setup Instructions* 🤖\n")

    print("Since I cannot directly create Telegram groups, here's what you need to do:\n")

    print("1️⃣ **Create the Group:**")
    print("   • Open Telegram and create a new group")
    print("   • Name it something like 'Polymarket Insider Alerts'")
    print("   • Make it public or invite-only as you prefer\n")

    print("2️⃣ **Add the Bot to the Group:**")
    print("   • Search for '@polymarket_insiders_bot' in Telegram")
    print("   • Add the bot to the group you just created")
    print("   • Make sure the bot has permission to send messages\n")

    print("3️⃣ **Get the Group Chat ID:**")
    print("   • Send any message to the group")
    print("   • Forward that message to @userinfobot")
    print("   • The bot will tell you the chat ID (format: -100xxxxx)")
    print("   • Update the .env file with this chat ID\n")

    print("4️⃣ **Alternative - Use a Private Chat:**")
    print("   • Simply start a private chat with @polymarket_insiders_bot")
    print("   • Send /start to test the bot")
    print("   • Use your personal chat ID instead of a group\n")

    print("5️⃣ **Test the Bot:**")
    print("   • Run this test script again")
    print("   • Or send /start, /help, /status commands to the bot\n")

    print("📱 *Bot Information:*")

    # Show actual bot info
    try:
        from src.polymarket_insider.config.settings import settings

        bot = Bot(token=settings.telegram_bot_token)
        bot_info = await bot.get_me()

        print(f"🤖 Bot Name: {bot_info.first_name}")
        print(f"🆔 Bot Username: @{bot_info.username}")
        print(f"📱 Bot ID: {bot_info.id}")
        print(f"🔑 Token: {settings.telegram_bot_token}")

        # Test sending a private message to check bot works
        print(f"\n📞 *Quick Test:*")
        print(f"If you want to test in a private chat,")
        print(f"simply message the bot at: @{bot_info.username}")
        print(f"Send: /start")

    except Exception as e:
        print(f"Error getting bot info: {e}")

    print(f"\n💡 *Next Steps:*")
    print(f"1. Create the group or use a private chat")
    print(f"2. Add the bot and get the chat ID")
    print(f"3. Update .env with the correct chat ID")
    print(f"4. Run the test script again to verify everything works")


if __name__ == "__main__":
    asyncio.run(create_group_and_invite())
