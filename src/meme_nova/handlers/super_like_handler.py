import asyncio
import logging

from telegram import Message, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from meme_nova.constants import MAIN_CHAT_ID, SUPER_LIKE_CALLBACK
from meme_nova.handlers.base import Handler
from meme_nova.repositories.message_repo import MessageRepo
from meme_nova.super_like import super_like_markup
from meme_nova.types import BotApplication

logger = logging.getLogger(__name__)


class SuperLikeHandler(Handler):
    def __init__(self, message_repo: MessageRepo) -> None:
        self._message_repo = message_repo
        self._lock = asyncio.Lock()

    async def handle(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None or query.data != SUPER_LIKE_CALLBACK:
            return
        message = query.message
        if not isinstance(message, Message) or message.chat.id != MAIN_CHAT_ID:
            await query.answer("Super Likes are available only in Memeproxy.")
            return
        async with self._lock:
            result = await self._message_repo.add_super_like(
                message.chat.id, message.message_id, query.from_user.id
            )
            if result == "added":
                count = await self._message_repo.super_like_count(
                    message.chat.id, message.message_id
                )
                try:
                    await query.edit_message_reply_markup(reply_markup=super_like_markup(count))
                except Exception:
                    logger.exception(
                        "failed to update super like count chat_id=%s message_id=%s",
                        message.chat.id,
                        message.message_id,
                    )
        response = {
            "added": "Потужний лайк зараховано!",
            "already_today": "You already used today's Super Like.",
            "self": "You can't Super Like your own post.",
            "unknown": "This post is no longer available for Super Likes.",
        }[result]
        await query.answer(response)

    def register(self, app: BotApplication) -> None:
        app.add_handler(CallbackQueryHandler(self.handle, pattern=f"^{SUPER_LIKE_CALLBACK}$"))
