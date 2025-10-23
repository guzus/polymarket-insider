#!/usr/bin/env python3
"""
Direct test of the bot with the provided token.
"""

import asyncio
import sys
from pathlib import Path
from telegram import Bot

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_direct_bot():
    """Test the bot directly with provided token."""
    # Use the exact token you provided
    token = "8427076253:AAG89bR6c6uGBRrE0VqQrIWEME61w5QCqVY"

    try:
        # Create bot instance
        bot = Bot(token=token)

        # Get bot info
        bot_info = await bot.get_me()

        print("🤖 BOT INFORMATION:")
        print(f"   Name: {bot_info.first_name}")
        print(f"   Username: @{bot_info.username}")
        print(f"   ID: {bot_info.id}")
        print(f"   Token: {token[:20]}...")
        print()

        print("✅ Bot is accessible and working!")
        print("📋 NEXT STEPS:")
        print("1. Start a conversation with @{bot_info.username}")
        print("2. Create a group named 'uncanny_guzus'")
        print("3. Add @{bot_info.username} to the group as admin")
        print("4. The bot will be able to send messages once added")

        # Try to send a message to the bot (this won't work but tests the connection)
        print()
        print("🔧 Bot connection test successful!")

        return True

    except Exception as e:
        print(f"❌ Error testing bot: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Direct Bot Test")
    print("=" * 40)

    try:
        asyncio.run(test_direct_bot())
    except KeyboardInterrupt:
        print("\n🛑 Test cancelled")
    except Exception as e:
        print(f"❌ Test error: {e}")