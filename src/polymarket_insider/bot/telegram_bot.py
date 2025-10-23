"""Telegram bot for sending trade alerts."""

import asyncio
from datetime import datetime
from typing import Optional

from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

from ..config.settings import settings
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
        self._polling_task: Optional[asyncio.Task] = None

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

    async def send_message_with_buttons(self, message: str, buttons: list[tuple[str, str]]) -> bool:
        """Send a message with inline buttons."""
        try:
            # Create inline keyboard markup
            keyboard = []
            if buttons:
                # Create rows of buttons (2 buttons per row for better layout)
                for i in range(0, len(buttons), 2):
                    row = []
                    for text, url in buttons[i:i+2]:
                        row.append(InlineKeyboardButton(text=text, url=url))
                    keyboard.append(row)

            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="Markdown",
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send Telegram message with buttons: {e}")
            return False

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /start command."""
        await update.message.reply_text(
            "🤖 *Polymarket Insider Bot*\\n\\n"
            "I monitor Polymarket for large trades (>$10k) and "
            "send alerts automatically.\\n\\n"
            "Commands:\\n"
            "/help - Show this help message\\n"
            "/status - Check bot status\\n\\n"
            "Alerts will be sent automatically when large trades are detected.",
            parse_mode="Markdown"
        )

    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /help command."""
        await update.message.reply_text(
            "🤖 *Polymarket Insider Bot - Help*\\n\\n"
            "This bot monitors Polymarket for:\\n"
            "• Large trades (>${settings.min_trade_size_usd:,.0f})\\n"
            "• Real-time tracking via Goldsky Orderbook Subgraph\\n\\n"
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
            f"🔄 Check Interval: {settings.polling_interval_seconds}s\\n\\n"
            f"Bot is actively monitoring for large trades.",
            parse_mode="Markdown"
        )

    async def start_polling(self) -> None:
        """Start the bot polling for updates."""
        app = await self.initialize()

        logger.info("Starting Telegram bot polling")
        # Initialize and start the application
        await app.initialize()
        await app.start()

        # Start polling in the background with error handling
        async def polling_with_error_handling():
            try:
                await app.updater.start_polling(drop_pending_updates=True)
            except asyncio.CancelledError:
                logger.info("Telegram bot polling cancelled")
                raise
            except Exception as e:
                logger.warning(f"Telegram bot polling error (this is usually a network issue): {e}")

        self._polling_task = asyncio.create_task(polling_with_error_handling())

    async def stop(self) -> None:
        """Stop the bot."""
        # Stop the application (which will stop the updater and its internal tasks)
        if self._app:
            try:
                # Stop the updater first to cancel internal polling tasks
                if self._app.updater.running:
                    await self._app.updater.stop()

                # Then stop and shutdown the application
                await self._app.stop()
                await self._app.shutdown()
            except Exception as e:
                logger.warning(f"Error stopping Telegram bot: {e}")
            logger.info("Telegram bot stopped")

        # Cancel our wrapper task if it's still running
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()
            try:
                await self._polling_task
            except (asyncio.CancelledError, Exception):
                pass