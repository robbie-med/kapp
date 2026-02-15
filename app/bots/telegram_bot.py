"""Telegram bot for teacher to add vocabulary/grammar."""

import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from app.config import TELEGRAM_BOT_TOKEN as _ENV_TOKEN, TELEGRAM_TEACHER_ID as _ENV_TEACHER_ID
from app.database import get_setting
from app.services.message_parser import process_teacher_items

logger = logging.getLogger(__name__)


async def _get_telegram_config():
    token = await get_setting("telegram_bot_token", _ENV_TOKEN)
    teacher_id = await get_setting("telegram_teacher_id", _ENV_TEACHER_ID)
    return token, teacher_id


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process incoming teacher messages."""
    if not update.message or not update.message.text:
        return

    _, teacher_id = await _get_telegram_config()
    user_id = str(update.message.from_user.id)
    if user_id != teacher_id:
        await update.message.reply_text("Sorry, only the teacher can add items.")
        return

    message = update.message.text
    result = await process_teacher_items(message, source="telegram")
    await update.message.reply_text(result["message"])


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Korean Learning App - Teacher Bot\n\n"
        "Send vocabulary or grammar items:\n"
        "\u2022 \ud589\ubcf5\ud558\ub2e4 - to be happy\n"
        "\u2022 T3: \ud589\ubcf5\ud558\ub2e4 - to be happy (set level)\n"
        "\u2022 \ubc25 - rice #food (add tags)\n"
        "\u2022 Or describe items naturally (AI parsing)\n\n"
        "Commands:\n"
        "\u2022 /level 3 \u2014 set default TOPIK level\n"
        "\u2022 /tags food, daily \u2014 set default tags\n"
        "\u2022 /tags clear \u2014 clear default tags\n"
        "\u2022 /status \u2014 show current context\n"
        "\u2022 /undo \u2014 delete last added batch"
    )


_bot_app: Application | None = None


async def start_telegram_bot():
    """Start the Telegram bot (long-polling)."""
    global _bot_app
    token, _ = await _get_telegram_config()
    if not token:
        logger.info("No Telegram bot token configured, skipping")
        return

    _bot_app = Application.builder().token(token).build()
    _bot_app.add_handler(CommandHandler("start", handle_start))
    _bot_app.add_handler(CommandHandler("level", _handle_command_msg))
    _bot_app.add_handler(CommandHandler("topik", _handle_command_msg))
    _bot_app.add_handler(CommandHandler("tags", _handle_command_msg))
    _bot_app.add_handler(CommandHandler("status", _handle_command_msg))
    _bot_app.add_handler(CommandHandler("undo", _handle_command_msg))
    _bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await _bot_app.initialize()
    await _bot_app.start()
    await _bot_app.updater.start_polling(drop_pending_updates=True)
    logger.info("Telegram bot started")


async def _handle_command_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /level, /tags, /status, /undo commands via Telegram command handlers."""
    if not update.message or not update.message.text:
        return

    _, teacher_id = await _get_telegram_config()
    user_id = str(update.message.from_user.id)
    if user_id != teacher_id:
        await update.message.reply_text("Sorry, only the teacher can use commands.")
        return

    result = await process_teacher_items(update.message.text, source="telegram")
    await update.message.reply_text(result["message"])


async def stop_telegram_bot():
    """Stop the Telegram bot."""
    global _bot_app
    if _bot_app:
        try:
            await _bot_app.updater.stop()
            await _bot_app.stop()
            await _bot_app.shutdown()
        except Exception as e:
            logger.warning(f"Error stopping Telegram bot: {e}")
        _bot_app = None
        logger.info("Telegram bot stopped")


async def restart_telegram_bot():
    """Stop and restart the bot with current config."""
    await stop_telegram_bot()
    await start_telegram_bot()


def get_telegram_status() -> dict:
    """Return current bot status."""
    running = _bot_app is not None
    return {"running": running}
