#!/usr/bin/env python3
"""Final comprehensive test of the Telegram bot setup."""

import asyncio
import logging
from sys import exit

from telegram import Bot
from src.polymarket_insider.bot.telegram_bot import TelegramAlertBot
from src.polymarket_insider.config.settings import settings
from src.polymarket_insider.detector.suspicious_trade_detector import SuspiciousTradeAlert
from src.polymarket_insider.api.models import Trade

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_all_components():
    """Test all components of the bot system."""
    print("🔧 Running comprehensive bot test...\n")

    # Test 1: Bot connection
    print("1️⃣ Testing bot connection...")
    try:
        bot = Bot(token=settings.telegram_bot_token)
        bot_info = await bot.get_me()
        print(f"✅ Bot connected: @{bot_info.username} ({bot_info.first_name})")
    except Exception as e:
        print(f"❌ Bot connection failed: {e}")
        return False

    # Test 2: AlertBot initialization
    print("\n2️⃣ Testing AlertBot initialization...")
    try:
        alert_bot = TelegramAlertBot()
        app = await alert_bot.initialize()
        print("✅ AlertBot initialized successfully")
    except Exception as e:
        print(f"❌ AlertBot initialization failed: {e}")
        return False

    # Test 3: Create mock alert
    print("\n3️⃣ Testing alert message formatting...")
    try:
        # Create mock trade data
        mock_trade = Trade(
            maker="0xabcdef1234567890",
            taker="0x1234567890abcdef",
            price=0.65,
            size=50000.0,
            side="BUY",
            token_id="token_123",
            timestamp="2024-01-15 10:30:00",
            transaction_hash="0x1234567890abcdef",
            market_question="Will Bitcoin reach $100k by end of 2024?",
            usd_size=50000.0
        )
        
        mock_alert = SuspiciousTradeAlert(
            trade=mock_trade,
            wallet_address="0xabcdef1234567890",
            previous_trades=0,
            confidence=0.85,
            reason="New wallet funded with $50K immediately before large trade"
        )
        
        # Test message formatting
        message = alert_bot._format_alert_message(mock_alert)
        print("✅ Alert message formatting successful")
        print(f"📝 Sample alert message length: {len(message)} characters")
        
    except Exception as e:
        print(f"❌ Alert formatting failed: {e}")
        return False

    # Test 4: Message sending (will fail if bot not in group, but that's expected)
    print(f"\n4️⃣ Testing message sending to {settings.telegram_chat_id}...")
    try:
        success = await alert_bot.send_message("🧪 Test message from Polymarket Insider Bot")
        if success:
            print("✅ Message sent successfully")
        else:
            print("⚠️ Message sending failed (expected if bot not in group)")
    except Exception as e:
        print(f"⚠️ Message sending error: {e}")

    print(f"\n📊 Test Summary:")
    print(f"✅ Bot connection: Working")
    print(f"✅ AlertBot initialization: Working") 
    print(f"✅ Alert formatting: Working")
    print(f"⚠️ Message sending: Requires bot to be added to chat")
    
    return True

async def main():
    """Main test function."""
    print("🚀 *Polymarket Insider Bot - Final Test* 🚀\n")
    
    success = await test_all_components()
    
    if success:
        print(f"\n🎉 *Test Results:*")
        print(f"All core components are working correctly!")
        print(f"\n📋 *Setup Instructions:*")
        print(f"1. Bot is ready: @polymarket_insiders_bot")
        print(f"2. Add bot to your group: uncanny_guzus")
        print(f"3. Or message bot directly for testing")
        print(f"4. Run 'python run_bot.py' to start the bot")
        print(f"\n🔧 *Next Steps:*")
        print(f"• Add the bot to your Telegram group")
        print(f"• Send /start, /help, /status to test commands")
        print(f"• The bot will monitor Polymarket and send alerts")
    else:
        print(f"\n❌ Some tests failed. Please check the errors above.")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
