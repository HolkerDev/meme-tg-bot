import logging
from collections.abc import Callable, Coroutine
from typing import Any

from telegram import Message, MessageEntity, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from meme_nova.platforms import Platform, PlatformHandler, build_handlers, find_handler
from meme_nova.settings import Settings

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("meme-nova online. Send text, get echo.")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message and update.message.text:
        await update.message.reply_text(update.message.text)


def extract_urls(message: Message) -> list[str]:
    urls: list[str] = []
    urls.extend(message.parse_entities([MessageEntity.URL]).values())
    urls.extend(message.parse_caption_entities([MessageEntity.URL]).values())
    for ent in tuple(message.entities) + tuple(message.caption_entities):
        if ent.type == MessageEntity.TEXT_LINK and ent.url:
            urls.append(ent.url)
    return urls


def make_log_group_message(
    handlers: tuple[PlatformHandler, ...],
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, None]]:
    async def log_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        msg = update.effective_message
        chat = update.effective_chat
        user = update.effective_user
        if not msg or not chat:
            return
        content = msg.text or msg.caption or ""
        logger.info(
            "group_message chat_id=%s chat_title=%s user_id=%s username=%s text=%r",
            chat.id,
            chat.title,
            user.id if user else None,
            user.username if user else None,
            content,
        )
        for url in extract_urls(msg):
            handler = find_handler(handlers, url)
            platform = handler.platform if handler else Platform.UNKNOWN
            logger.info("link platform=%s url=%s", platform.value, url)
            if handler:
                await handler.process(url, msg)

    return log_group_message


def build_app(settings: Settings) -> Application[Any, Any, Any, Any, Any, Any]:
    handlers = build_handlers(
        instagram_username=settings.instagram_username,
        instagram_session_file=settings.instagram_session_file,
    )
    app = ApplicationBuilder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start))
    group_filter = filters.ChatType.GROUPS & ~filters.COMMAND & ~filters.StatusUpdate.ALL
    app.add_handler(MessageHandler(group_filter, make_log_group_message(handlers)))
    app.add_handler(
        MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, echo)
    )
    return app


def main() -> None:
    settings = Settings.load()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    app = build_app(settings)
    logger.info("Starting bot polling")
    app.run_polling()
