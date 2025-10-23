"""Command-line interface for Polymarket Insider."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import click
from telegram import Bot

from .bot.telegram_bot import TelegramAlertBot
from .config.settings import settings
from .main import PolymarketInsiderApp
from .utils.logger import setup_logger

logger = setup_logger(__name__)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """Polymarket Insider - Monitor suspicious trading patterns."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@cli.command()
@click.option("--chat-id", help="Override chat ID for testing")
def test_bot(chat_id: Optional[str]) -> None:
    """Test Telegram bot functionality."""
    asyncio.run(_test_bot(chat_id))


async def _test_bot(chat_id: Optional[str]) -> None:
    """Test bot functionality."""
    click.echo("🤖 Testing Telegram Bot...")

    bot = Bot(token=settings.telegram_bot_token)

    try:
        # Get bot info
        bot_info = await bot.get_me()
        click.echo(f"✅ Bot: @{bot_info.username} ({bot_info.full_name})")

        # Test sending message
        target_chat = chat_id or settings.telegram_chat_id
        if target_chat and target_chat != "your_telegram_chat_id_here":
            click.echo(f"📤 Sending test message to {target_chat}...")

            await bot.send_message(
                chat_id=target_chat,
                text="🤖 *Polymarket Insider Bot - Test Message*\n\n"
                     "✅ Bot is working correctly!\n\n"
                     "This is a test message to verify the bot can send "
                     "notifications to this chat.",
                parse_mode="Markdown"
            )
            click.echo("✅ Test message sent successfully!")
        else:
            click.echo("⚠️  No valid chat ID configured.")

    except Exception as e:
        click.echo(f"❌ Error testing bot: {e}")
        sys.exit(1)


@cli.command()
def get_chat_id() -> None:
    """Get Telegram chat ID by listening for messages."""
    asyncio.run(_get_chat_id())


async def _get_chat_id() -> None:
    """Get chat ID by listening for messages."""
    click.echo("=" * 50)
    click.echo("Telegram Bot Setup - Getting Chat ID")
    click.echo("=" * 50)
    click.echo(f"Bot Token: {settings.telegram_bot_token[:10]}...")
    click.echo("\nTo get your chat ID:")
    click.echo("1. Start a chat with your bot in Telegram")
    click.echo("2. Send any message to the bot")
    click.echo("3. The bot will reply with your chat ID")
    click.echo("4. Update the .env file with your chat ID")
    click.echo("\nStarting bot to listen for messages...")

    bot = Bot(token=settings.telegram_bot_token)

    async def handle_message(update, context):
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        user = update.effective_user

        click.echo(f"\n✅ Message received!")
        click.echo(f"   Chat ID: {chat_id}")
        click.echo(f"   Chat Type: {chat_type}")
        click.echo(f"   User: {user.full_name} (@{user.username})" if user.username else f"   User: {user.full_name}")

        if chat_type == "group":
            click.echo(f"   Group Title: {update.effective_chat.title}")

        await update.message.reply_text(
            f"Your chat ID is: `{chat_id}`\n\n"
            f"Chat type: {chat_type}\n\n"
            f"Update your .env file with:\n"
            f"TELEGRAM_CHAT_ID={chat_id}",
            parse_mode="Markdown"
        )

        if chat_type == "private":
            click.echo("\n🎯 This is a private chat. You can use this chat ID.")
        else:
            click.echo("\n🎯 This is a group chat. You can use this chat ID for group notifications.")

    from telegram.ext import Application, MessageHandler, filters

    application = Application.builder().token(settings.telegram_bot_token).build()
    application.add_handler(MessageHandler(filters.ALL, handle_message))

    try:
        click.echo("\nBot is listening... (Press Ctrl+C to stop)")
        await application.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        click.echo("\n\nStopping bot...")


@cli.command()
@click.option("--test-only", is_flag=True, help="Only test bot, don't start monitoring")
def run_bot(test_only: bool) -> None:
    """Run the Telegram bot."""
    asyncio.run(_run_bot(test_only))


async def _run_bot(test_only: bool) -> None:
    """Run the bot."""
    click.echo("🤖 Starting Polymarket Insider Telegram Bot...")
    click.echo(f"📱 Bot token: {settings.telegram_bot_token[:10]}...")
    click.echo(f"💬 Target chat: {settings.telegram_chat_id}")

    if test_only:
        click.echo("🧪 Testing bot functionality only...")
        await _test_bot(None)
        return

    click.echo("📡 Bot is now running. Press Ctrl+C to stop.\n")

    bot = TelegramAlertBot()

    try:
        await bot.start_polling()
    except KeyboardInterrupt:
        click.echo("\n👋 Bot stopped by user.")
        await bot.stop()
    except Exception as e:
        click.echo(f"\n❌ Bot error: {e}")
        await bot.stop()


@cli.command()
@click.option("--bot-only", is_flag=True, help="Run only the Telegram bot")
def monitor(bot_only: bool) -> None:
    """Start the full monitoring system."""
    if bot_only:
        asyncio.run(_run_bot(False))
        return

    click.echo("🚀 Starting Polymarket Insider monitoring system...")
    app = PolymarketInsiderApp()

    try:
        asyncio.run(app.start())
    except KeyboardInterrupt:
        click.echo("\n🛑 Monitoring stopped by user")
    except Exception as e:
        click.echo(f"❌ Fatal error: {e}")
        sys.exit(1)


@cli.command()
def group_instructions() -> None:
    """Show instructions for creating a group chat."""
    click.echo("=" * 50)
    click.echo("Creating Group Chat - Instructions")
    click.echo("=" * 50)
    click.echo("\nTo create a group chat and invite the bot:")
    click.echo("1. Open Telegram")
    click.echo("2. Click the pencil icon (New Message)")
    click.echo("3. Select 'New Group'")
    click.echo("4. Name your group (e.g., 'Polymarket Insider Alerts')")
    click.echo("5. Add participants if desired")
    click.echo("6. Add your bot by searching for @polymarket_insider_bot")
    click.echo("7. Once the group is created, send a message to get the group chat ID")
    click.echo("\nNote: You need to be a group admin to add bots to groups.")


@cli.command()
@click.option("--check", type=click.Choice(['api', 'telegram', 'all']), default='all',
              help="Type of health check to perform")
def health_check(check: str) -> None:
    """Perform system health check."""
    asyncio.run(_health_check(check))


async def _health_check(check_type: str) -> None:
    """Perform health check."""
    from .connection_manager import ConnectionManager
    from .bot.telegram_bot import TelegramAlertBot
    from .detector.suspicious_trade_detector import SuspiciousTradeDetector
    from .health_checker import HealthChecker

    click.echo("🏥 Performing health check...")

    try:
        # Initialize components
        conn_manager = ConnectionManager()
        await conn_manager.initialize()

        bot = TelegramAlertBot()
        await bot.initialize()

        detector = SuspiciousTradeDetector()
        health_checker = HealthChecker(conn_manager, bot, detector)

        # Run health check
        results = await health_checker.run_manual_health_check()

        click.echo("\n📊 Health Check Results:")
        click.echo("=" * 30)
        click.echo(f"API Connectivity: {'✅' if results['api_connectivity'] else '❌'}")
        click.echo(f"Telegram Connectivity: {'✅' if results['telegram_connectivity'] else '❌'}")
        click.echo(f"Trade Cleanup: {'✅' if results['trade_cleanup'] else '❌'}")
        click.echo(f"Overall Health: {'✅' if results['overall_healthy'] else '❌'}")

        if results['overall_healthy']:
            click.echo("\n🎉 All systems operational!")
        else:
            click.echo("\n⚠️  Some issues detected. Check logs for details.")
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Health check failed: {e}")
        sys.exit(1)
    finally:
        if conn_manager:
            await conn_manager.cleanup()


@cli.command()
def config() -> None:
    """Show current configuration."""
    click.echo("⚙️  Current Configuration:")
    click.echo("=" * 40)
    click.echo(f"Polymarket API URL: {settings.polymarket_api_url}")
    click.echo(f"WebSocket URL: {settings.polymarket_ws_url}")
    click.echo(f"HTTP Timeout: {settings.http_timeout}s")
    click.echo(f"Min Trade Size: ${settings.min_trade_size_usd:,.2f}")
    click.echo(f"Funding Lookback: {settings.funding_lookback_hours}h")
    click.echo(f"Trade History Check: {settings.trade_history_check_days} days")
    click.echo(f"Polling Interval: {settings.polling_interval_seconds}s")
    click.echo(f"Health Check Interval: {settings.health_check_interval_seconds}s")
    click.echo(f"Log Level: {settings.log_level}")
    click.echo(f"Chat ID: {settings.telegram_chat_id}")
    click.echo(f"Bot Token: {settings.telegram_bot_token[:10]}... (truncated)")


@cli.command()
def status() -> None:
    """Show application status."""
    click.echo("📊 Polymarket Insider Status")
    click.echo("=" * 30)
    click.echo("Version: 1.0.0")
    click.echo("Mode: Production")

    # Check if configuration is valid
    try:
        if settings.telegram_bot_token == "your_bot_token_here":
            click.echo("⚠️  Bot token not configured")
        else:
            click.echo("✅ Bot token configured")

        if settings.telegram_chat_id == "your_telegram_chat_id_here":
            click.echo("⚠️  Chat ID not configured")
        else:
            click.echo("✅ Chat ID configured")

        click.echo("✅ Configuration loaded successfully")
    except Exception as e:
        click.echo(f"❌ Configuration error: {e}")
        sys.exit(1)


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()