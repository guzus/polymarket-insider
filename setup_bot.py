#!/usr/bin/env python3
"""Setup script for Telegram bot to get chat ID and test functionality."""

import asyncio
import sys
from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, filters
from polymarket_insider.config.settings import settings
from polymarket_insider.utils.logger import setup_logger

logger = setup_logger(__name__)


async def get_chat_id():
    """Get the chat ID by listening for messages."""
    print("=" * 50)
    print("Telegram Bot Setup - Getting Chat ID")
    print("=" * 50)
    print(f"Bot Token: {settings.telegram_bot_token[:10]}...")
    print("\nTo get your chat ID:")
    print("1. Start a chat with your bot in Telegram")
    print("2. Send any message to the bot")
    print("3. The bot will reply with your chat ID")
    print("4. Update the .env file with your chat ID")
    print("\nStarting bot to listen for messages...")

    bot = Bot(token=settings.telegram_bot_token)

    async def handle_message(update, context):
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        user = update.effective_user

        print(f"\n✅ Message received!")
        print(f"   Chat ID: {chat_id}")
        print(f"   Chat Type: {chat_type}")
        print(f"   User: {user.full_name} (@{user.username})" if user.username else f"   User: {user.full_name}")

        if chat_type == "group":
            print(f"   Group Title: {update.effective_chat.title}")

        await update.message.reply_text(
            f"Your chat ID is: `{chat_id}`\n\n"
            f"Chat type: {chat_type}\n\n"
            f"Update your .env file with:\n"
            f"TELEGRAM_CHAT_ID={chat_id}",
            parse_mode="Markdown"
        )

        if chat_type == "private":
            print("\n🎯 This is a private chat. You can use this chat ID.")
        else:
            print("\n🎯 This is a group chat. You can use this chat ID for group notifications.")

    application = Application.builder().token(settings.telegram_bot_token).build()
    application.add_handler(MessageHandler(filters.ALL, handle_message))

    try:
        print("\nBot is listening... (Press Ctrl+C to stop)")
        await application.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        print("\n\nStopping bot...")


async def test_bot():
    """Test bot functionality with current settings."""
    print("=" * 50)
    print("Testing Telegram Bot Functionality")
    print("=" * 50)

    bot = Bot(token=settings.telegram_bot_token)

    try:
        # Get bot info
        bot_info = await bot.get_me()
        print(f"✅ Bot Info:")
        print(f"   Name: {bot_info.full_name}")
        print(f"   Username: @{bot_info.username}")
        print(f"   Bot ID: {bot_info.id}")

        # Test sending message
        if settings.telegram_chat_id and settings.telegram_chat_id != "your_telegram_chat_id_here":
            print(f"\n📤 Sending test message to chat {settings.telegram_chat_id}...")

            await bot.send_message(
                chat_id=settings.telegram_chat_id,
                text="🤖 *Polymarket Insider Bot - Test Message*\n\n"
                     "✅ Bot is working correctly!\n\n"
                     "This is a test message to verify the bot can send "
                     "notifications to this chat.",
                parse_mode="Markdown"
            )
            print("✅ Test message sent successfully!")
        else:
            print("\n⚠️  No valid chat ID configured. Run with --get-chat-id first.")

    except Exception as e:
        print(f"❌ Error testing bot: {e}")
        print("\nPossible solutions:")
        print("1. Check if the bot token is correct")
        print("2. Make sure you've started a chat with the bot")
        print("3. Check if the chat ID is correct")
        print("4. Verify the bot has permission to send messages")


async def create_group_invite():
    """Create instructions for creating a group chat."""
    print("=" * 50)
    print("Creating Group Chat - Instructions")
    print("=" * 50)
    print("\nTo create a group chat and invite the bot:")
    print("1. Open Telegram")
    print("2. Click the pencil icon (New Message)")
    print("3. Select 'New Group'")
    print("4. Name your group (e.g., 'Polymarket Insider Alerts')")
    print("5. Add participants if desired")
    print("6. Add your bot by searching for @polymarket_insider_bot")
    print("7. Once the group is created, send a message to get the group chat ID")
    print("\nNote: You need to be a group admin to add bots to groups.")


async def main():
    """Main function."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--get-chat-id":
            await get_chat_id()
        elif sys.argv[1] == "--test":
            await test_bot()
        elif sys.argv[1] == "--group-instructions":
            await create_group_invite()
        else:
            print("Usage:")
            print("  python setup_bot.py --get-chat-id      # Get chat ID")
            print("  python setup_bot.py --test             # Test bot")
            print("  python setup_bot.py --group-instructions  # Group setup help")
    else:
        print("Telegram Bot Setup Script")
        print("=" * 30)
        print("\nOptions:")
        print("  --get-chat-id          Get your chat ID")
        print("  --test                 Test bot functionality")
        print("  --group-instructions   How to create a group")
        print("\nExample:")
        print("  python setup_bot.py --get-chat-id")


if __name__ == "__main__":
    asyncio.run(main())