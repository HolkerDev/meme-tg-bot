import asyncio
import logging
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
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
    MessageReactionHandler,
    filters,
)

from meme_nova.media_dedup import MediaDedupStore
from meme_nova.platforms import Platform, PlatformHandler, build_handlers, find_handler
from meme_nova.platforms.base import ProcessResult, safe_chat_action
from meme_nova.reaction_store import ReactionStore, TopRecipient
from meme_nova.retry_queue import POLL_INTERVAL_SECONDS, RetryItem, RetryQueue
from meme_nova.settings import Settings
from meme_nova.stats_store import TOP_N, StatsStore, TopUser

logger = logging.getLogger(__name__)

STATS_POLL_INTERVAL_SECONDS = 3600.0


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


def _display_name(update: Update) -> str:
    user = update.effective_user
    if not user:
        return "user"
    if user.username:
        return f"@{user.username}"
    return user.first_name or "user"


def make_log_group_message(
    handlers: tuple[PlatformHandler, ...],
    queue: RetryQueue,
    stats: StatsStore,
    dedup: MediaDedupStore,
    reactions: ReactionStore,
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, None]]:
    async def log_group_message(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
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
        had_valid_link = False
        registered_author = False
        display_name = _display_name(update) if user else "user"
        for url in extract_urls(msg):
            handler = find_handler(handlers, url)
            platform = handler.platform if handler else Platform.UNKNOWN
            logger.info("link platform=%s url=%s", platform.value, url)
            if not handler:
                continue
            had_valid_link = True
            if user and not registered_author:
                await reactions.register_message(chat.id, msg.message_id, user.id, display_name)
                registered_author = True
            lock = await dedup.lock(chat.id, msg.message_id, url)
            async with lock:
                if await dedup.is_posted(chat.id, msg.message_id, url):
                    logger.info("skipping already-posted url=%s", url)
                    continue
                await safe_chat_action(msg, ChatAction.TYPING)
                result = await handler.process(url, msg)
            if not result.ok:
                if await queue.enqueue(url, chat.id, chat.type, msg.message_id):
                    logger.info("queued retry url=%s platform=%s", url, platform.value)
            elif result.bot_message_ids and user:
                for bot_message_id in result.bot_message_ids:
                    await reactions.register_message(
                        chat.id, bot_message_id, user.id, display_name
                    )
        if had_valid_link and user:
            await stats.record_post(chat.id, user.id, display_name)

    return log_group_message


async def _register_bot_messages(
    reactions: ReactionStore,
    chat_id: int,
    source_message_id: int,
    bot_message_ids: tuple[int, ...],
) -> None:
    if not bot_message_ids:
        return
    author = await reactions.lookup_author(chat_id, source_message_id)
    if not author:
        return
    for bot_message_id in bot_message_ids:
        await reactions.register_message(
            chat_id, bot_message_id, author.user_id, author.display_name
        )


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
    dedup: MediaDedupStore,
    reactions: ReactionStore,
) -> None:
    if await dedup.is_posted(item.chat_id, item.message_id, item.url):
        logger.info("retry skip already-posted url=%s", item.url)
        await queue.delete(item.id)
        return
    handler = find_handler(handlers, item.url)
    if not handler:
        await queue.delete(item.id)
        return
    msg = _rebuild_message(item, bot)
    logger.info("retry attempt=%d url=%s", item.attempt + 1, item.url)
    lock = await dedup.lock(item.chat_id, item.message_id, item.url)
    async with lock:
        if await dedup.is_posted(item.chat_id, item.message_id, item.url):
            logger.info("retry skip already-posted url=%s", item.url)
            await queue.delete(item.id)
            return
        await safe_chat_action(msg, ChatAction.TYPING)
        try:
            result = await handler.process(item.url, msg)
        except Exception:
            logger.exception("retry crashed url=%s", item.url)
            result = ProcessResult.failure()
    if result.ok:
        await _register_bot_messages(
            reactions, item.chat_id, item.message_id, result.bot_message_ids
        )
        await queue.delete(item.id)
    else:
        await queue.mark_failed(item)


async def retry_worker(
    queue: RetryQueue,
    handlers: tuple[PlatformHandler, ...],
    bot: Bot,
    dedup: MediaDedupStore,
    reactions: ReactionStore,
) -> None:
    while True:
        try:
            due = await queue.fetch_due()
            for item in due:
                await _retry_one(item, handlers, queue, bot, dedup, reactions)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("retry worker iteration failed")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


@dataclass(frozen=True)
class WeeklyUserRow:
    user_id: int
    display_name: str
    link_count: int
    reaction_count: int


def _format_stats(rows: list[WeeklyUserRow]) -> str:
    return "\n".join(
        f"{i}. {row.display_name} — {row.reaction_count} reactions, {row.link_count} links"
        for i, row in enumerate(rows, start=1)
    )


def rank_weekly_users(
    link_users: list[TopUser],
    reaction_counts: dict[int, int],
    reaction_users: list[TopRecipient],
    limit: int = TOP_N,
) -> list[WeeklyUserRow]:
    display_names = {user.user_id: user.display_name for user in link_users}
    for recipient in reaction_users:
        display_names.setdefault(recipient.user_id, recipient.display_name)
    link_counts = {user.user_id: user.count for user in link_users}
    user_ids = set(link_counts) | set(reaction_counts)
    rows = [
        WeeklyUserRow(
            user_id=user_id,
            display_name=display_names.get(user_id, "user"),
            link_count=link_counts.get(user_id, 0),
            reaction_count=reaction_counts.get(user_id, 0),
        )
        for user_id in user_ids
    ]
    rows.sort(key=lambda row: (-row.reaction_count, -row.link_count, row.user_id))
    return rows[:limit]


async def _publish_due_stats(
    stats: StatsStore, reactions: ReactionStore, bot: Bot
) -> None:
    for chat in await stats.due_chats():
        since = chat.last_published_at
        link_users = await stats.user_link_counts(chat.chat_id, since)
        reaction_counts = await reactions.recipient_counts(chat.chat_id, since)
        reaction_users = await reactions.top_recipients(chat.chat_id, since, limit=1000)
        ranked = rank_weekly_users(link_users, reaction_counts, reaction_users)
        if ranked:
            try:
                await bot.send_message(
                    chat_id=chat.chat_id,
                    text=_format_stats(ranked),
                )
            except Exception:
                logger.exception("failed to send stats to chat=%s", chat.chat_id)
                continue
        await stats.mark_published(chat.chat_id)


async def stats_worker(stats: StatsStore, reactions: ReactionStore, bot: Bot) -> None:
    while True:
        try:
            await _publish_due_stats(stats, reactions, bot)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("stats worker iteration failed")
        await asyncio.sleep(STATS_POLL_INTERVAL_SECONDS)


def make_reaction_handler(
    reactions: ReactionStore,
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, None]]:
    async def on_reaction(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        event = update.message_reaction
        if not event or not event.user:
            return
        await reactions.apply_reaction_delta(
            chat_id=event.chat.id,
            message_id=event.message_id,
            reactor_user_id=event.user.id,
            old_reactions=event.old_reaction,
            new_reactions=event.new_reaction,
        )

    return on_reaction


def build_app(settings: Settings) -> Application[Any, Any, Any, Any, Any, Any]:
    queue = RetryQueue(settings.db_path)
    stats = StatsStore(settings.db_path)
    dedup = MediaDedupStore(settings.db_path)
    reactions = ReactionStore(settings.db_path)
    handlers = build_handlers(
        instagram_username=settings.instagram_username,
        instagram_password=settings.instagram_password,
        instagram_session_file=settings.instagram_session_file,
        instagram_cookies_file=settings.instagram_cookies_file,
        media_dedup=dedup,
    )

    async def post_init(app: Application[Any, Any, Any, Any, Any, Any]) -> None:
        app.create_task(retry_worker(queue, handlers, app.bot, dedup, reactions))
        app.create_task(stats_worker(stats, reactions, app.bot))

    app = ApplicationBuilder().token(settings.telegram_bot_token).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    group_filter = filters.ChatType.GROUPS & ~filters.COMMAND & ~filters.StatusUpdate.ALL
    app.add_handler(
        MessageHandler(
            group_filter,
            make_log_group_message(handlers, queue, stats, dedup, reactions),
        )
    )
    app.add_handler(MessageReactionHandler(make_reaction_handler(reactions)))
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
    app.run_polling(allowed_updates=Update.ALL_TYPES)
