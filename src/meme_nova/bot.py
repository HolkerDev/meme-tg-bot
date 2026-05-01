import asyncio
import logging
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

from telegram import Bot, Chat, Message, MessageEntity, Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from meme_nova.platforms import Platform, PlatformHandler, build_handlers, find_handler
from meme_nova.platforms.base import safe_chat_action
from meme_nova.retry_queue import POLL_INTERVAL_SECONDS, RetryItem, RetryQueue
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
    queue: RetryQueue,
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
            if not handler:
                continue
            await safe_chat_action(msg, ChatAction.TYPING)
            ok = await handler.process(url, msg)
            if not ok:
                await queue.enqueue(url, chat.id, chat.type, msg.message_id)
                logger.info("queued retry url=%s platform=%s", url, platform.value)

    return log_group_message


def _rebuild_message(item: RetryItem, bot: Bot) -> Message:
    msg = Message(
        message_id=item.message_id,
        date=datetime.now(tz=UTC),
        chat=Chat(id=item.chat_id, type=item.chat_type),
    )
    msg.set_bot(bot)
    return msg


async def _retry_one(
    item: RetryItem,
    handlers: tuple[PlatformHandler, ...],
    queue: RetryQueue,
    bot: Bot,
) -> None:
    handler = find_handler(handlers, item.url)
    if not handler:
        await queue.delete(item.id)
        return
    msg = _rebuild_message(item, bot)
    logger.info("retry attempt=%d url=%s", item.attempt + 1, item.url)
    await safe_chat_action(msg, ChatAction.TYPING)
    try:
        ok = await handler.process(item.url, msg)
    except Exception:
        logger.exception("retry crashed url=%s", item.url)
        ok = False
    if ok:
        await queue.delete(item.id)
    else:
        await queue.mark_failed(item)


async def retry_worker(
    queue: RetryQueue,
    handlers: tuple[PlatformHandler, ...],
    bot: Bot,
) -> None:
    while True:
        try:
            due = await queue.fetch_due()
            for item in due:
                await _retry_one(item, handlers, queue, bot)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("retry worker iteration failed")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


def build_app(settings: Settings) -> Application[Any, Any, Any, Any, Any, Any]:
    handlers = build_handlers(
        instagram_username=settings.instagram_username,
        instagram_password=settings.instagram_password,
        instagram_session_file=settings.instagram_session_file,
    )
    queue = RetryQueue(settings.retry_db_path)

    async def post_init(app: Application[Any, Any, Any, Any, Any, Any]) -> None:
        app.create_task(retry_worker(queue, handlers, app.bot))

    app = (
        ApplicationBuilder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    group_filter = filters.ChatType.GROUPS & ~filters.COMMAND & ~filters.StatusUpdate.ALL
    app.add_handler(MessageHandler(group_filter, make_log_group_message(handlers, queue)))
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
