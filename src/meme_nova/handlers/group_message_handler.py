import logging

from telegram import Message, MessageEntity, Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes, MessageHandler, filters

from meme_nova.handlers.base import Handler
from meme_nova.platforms import Platform, PlatformHandler, find_handler
from meme_nova.platforms.base import safe_chat_action
from meme_nova.repositories.message_repo import MessageRepo
from meme_nova.types import BotApplication

logger = logging.getLogger(__name__)

_GROUP_FILTER = filters.ChatType.GROUPS & ~filters.COMMAND & ~filters.StatusUpdate.ALL


def extract_urls(message: Message) -> list[str]:
    urls: list[str] = []
    urls.extend(message.parse_entities([MessageEntity.URL]).values())
    urls.extend(message.parse_caption_entities([MessageEntity.URL]).values())
    for ent in tuple(message.entities) + tuple(message.caption_entities):
        if ent.type == MessageEntity.TEXT_LINK and ent.url:
            urls.append(ent.url)
    return urls


class GroupMessageHandler(Handler):
    def __init__(
        self,
        platform_handlers: tuple[PlatformHandler, ...],
        message_repo: MessageRepo,
    ) -> None:
        self._platform_handlers = platform_handlers
        self._message_repo = message_repo

    async def handle(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
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
        registered_link = False
        registered_bot_message_ids: set[int] = set()
        for url in extract_urls(msg):
            handler = find_handler(self._platform_handlers, url)
            platform = handler.platform if handler else Platform.UNKNOWN
            logger.info("link platform=%s url=%s", platform.value, url)
            if not handler:
                continue
            if user and not registered_link:
                await self._message_repo.register_message(
                    chat.id,
                    msg.message_id,
                    user.id,
                    username=user.username,
                    display_name=user.full_name,
                )
                registered_link = True
            await safe_chat_action(msg, ChatAction.TYPING)
            result = await handler.process(url, msg)
            if not result.ok:
                logger.warning("failed to process url=%s platform=%s", url, platform.value)
                continue
            if user and result.bot_message_ids:
                for bot_message_id in result.bot_message_ids:
                    if bot_message_id in registered_bot_message_ids:
                        continue
                    registered_bot_message_ids.add(bot_message_id)
                    await self._message_repo.register_message(
                        chat.id,
                        bot_message_id,
                        user.id,
                        username=user.username,
                        display_name=user.full_name,
                    )

    def register(self, app: BotApplication) -> None:
        app.add_handler(MessageHandler(_GROUP_FILTER, self.handle))
