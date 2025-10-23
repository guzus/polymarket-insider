"""Telegram bot for sending trade alerts."""

import asyncio
from datetime import datetime
from typing import Optional

from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

from ..config.settings import settings
from ..detector.suspicious_trade_detector import SuspiciousTradeAlert
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class TelegramAlertBot:
    """Telegram bot for sending Polymarket trade alerts."""

    def __init__(self):
        """Initialize the Telegram bot."""
        self.bot_token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self.bot = Bot(token=self.bot_token)
        self._app: Optional[Application] = None

    async def initialize(self) -> Application:
        """Initialize the Telegram application."""
        if self._app is None:
            # Create the Application
            self._app = Application.builder().token(self.bot_token).build()

            # Add command handlers
            self._app.add_handler(CommandHandler("start", self._handle_start))
            self._app.add_handler(CommandHandler("help", self._handle_help))
            self._app.add_handler(CommandHandler("status", self._handle_status))

            logger.info("Telegram bot initialized")

        return self._app

    def is_initialized(self) -> bool:
        """Check if the bot is initialized."""
        return self._app is not None

    async def send_alert(self, alert: SuspiciousTradeAlert) -> bool:
        """Send a suspicious trade alert."""
        try:
            message = self._format_alert_message(alert)
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            logger.info(f"Alert sent to Telegram chat {self.chat_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False

    async def send_message(self, message: str) -> bool:
        """Send a generic message."""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=None  # Disable markdown to avoid parsing issues
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def _format_alert_message(self, alert: SuspiciousTradeAlert) -> str:
        """Format an alert message for Telegram."""
        trade = alert.trade
        confidence_emoji = "🔴" if alert.confidence >= 0.8 else "🟡" if alert.confidence >= 0.6 else "🟢"

        message = f"""
{confidence_emoji} **SUSPICIOUS TRADE DETECTED** {confidence_emoji}

📊 **Trade Details:**
• Market: {trade.market_question or 'Unknown Market'}
• Size: ${f"{trade.usd_size:,.2f}" if trade.usd_size is not None else "0.00"}
• Price: ${trade.price:.4f}
• Side: {trade.side}
• Time: {trade.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC

🔍 **Suspicious Activity:**
{alert.reason}

👛 **Wallet Analysis:**
• Address: `{alert.wallet_address}`
• Previous Trades: {alert.previous_trades}
• Confidence: {alert.confidence:.1%}

🔗 **Transaction:** [View on Etherscan](https://etherscan.io/tx/{trade.transaction_hash})
        """.strip()

        return message

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /start command."""
        await update.message.reply_text(
            "🤖 *Polymarket Insider Bot*\\n\\n"
            "I monitor Polymarket for suspicious trading patterns and "
            "send alerts for potentially manipulative activity.\\n\\n"
            "Commands:\\n"
            "/help - Show this help message\\n"
            "/status - Check bot status\\n\\n"
            "Alerts will be sent automatically when suspicious activity is detected.",
            parse_mode="Markdown"
        )

    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /help command."""
        await update.message.reply_text(
            "🤖 *Polymarket Insider Bot - Help*\\n\\n"
            "This bot monitors Polymarket for:\\n"
            "• Large trades from new wallets\\n"
            "• Wallets funded immediately before trading\\n"
            "• Unusual trading patterns\\n\\n"
            "Commands:\\n"
            "/start - Welcome message\\n"
            "/status - Bot status\\n"
            "/help - This help message\\n\\n"
            "Alerts are sent automatically to this chat.",
            parse_mode="Markdown"
        )

    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /status command."""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')

        await update.message.reply_text(
            f"📊 *Bot Status*\\n\\n"
            f"🟢 Status: Active\\n"
            f"⏰ Current Time: {current_time}\\n"
            f"💰 Min Alert Size: ${settings.min_trade_size_usd:,.2f}\\n"
            f"⏳ Funding Lookback: {settings.funding_lookback_hours} hours\\n"
            f"📈 History Check: {settings.trade_history_check_days} days\\n\\n"
            f"Bot is actively monitoring for suspicious trades.",
            parse_mode="Markdown"
        )

    async def start_polling(self) -> None:
        """Start the bot polling for updates."""
        app = await self.initialize()

        logger.info("Starting Telegram bot polling")
        # Initialize and start the application
        await app.initialize()
        await app.start()
        # Start polling in the background without blocking
        asyncio.create_task(app.updater.start_polling(drop_pending_updates=True))

    async def stop(self) -> None:
        """Stop the bot."""
        if self._app:
            try:
                await self._app.stop()
                await self._app.shutdown()
            except Exception as e:
                logger.warning(f"Error stopping Telegram bot: {e}")
            logger.info("Telegram bot stopped")