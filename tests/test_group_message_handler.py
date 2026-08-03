from datetime import UTC, datetime
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession
from telegram import Chat, Message, MessageEntity, Update, User
from telegram.constants import ChatType

from meme_nova.handlers.group_message_handler import GroupMessageHandler
from meme_nova.models import MessageModel
from meme_nova.platforms import Platform
from meme_nova.platforms.base import ProcessResult
from meme_nova.repositories.message_repo import MessageRepo

CHAT_ID = 100
AUTHOR_USER_ID = 1
LINK_MESSAGE_ID = 10
BOT_VIDEO_MESSAGE_ID = 99
INSTAGRAM_URL = "https://www.instagram.com/reel/abc/"


class StubPlatformHandler:
    def __init__(
        self,
        *,
        bot_message_ids: tuple[int, ...] = (),
        ok: bool = True,
    ) -> None:
        self._bot_message_ids = bot_message_ids
        self._ok = ok
        self.process_calls: list[str] = []

    @property
    def platform(self) -> Platform:
        return Platform.INSTAGRAM

    def matches(self, url: str) -> bool:
        return "instagram.com" in url

    async def process(self, url: str, message: Message) -> ProcessResult:
        self.process_calls.append(url)
        if not self._ok:
            return ProcessResult.failure()
        if self._bot_message_ids:
            return ProcessResult.success(*self._bot_message_ids)
        return ProcessResult.skipped()


def _make_group_link_message(
    *,
    chat_id: int = CHAT_ID,
    message_id: int = LINK_MESSAGE_ID,
    user_id: int = AUTHOR_USER_ID,
    username: str | None = "alice",
    first_name: str = "Alice",
    url: str = INSTAGRAM_URL,
    edit_date: datetime | None = None,
) -> Message:
    text = f"check this {url}"
    offset = text.index(url)
    entities = (MessageEntity(type=MessageEntity.URL, offset=offset, length=len(url)),)
    chat = Chat(id=chat_id, type=ChatType.GROUP, title="Test")
    user = User(id=user_id, is_bot=False, first_name=first_name, username=username)
    return Message(
        message_id=message_id,
        date=datetime.now(tz=UTC),
        chat=chat,
        from_user=user,
        text=text,
        entities=entities,
        edit_date=edit_date,
    )


def _make_group_link_update(
    *,
    chat_id: int = CHAT_ID,
    message_id: int = LINK_MESSAGE_ID,
    user_id: int = AUTHOR_USER_ID,
    username: str | None = "alice",
    first_name: str = "Alice",
    url: str = INSTAGRAM_URL,
) -> Update:
    message = _make_group_link_message(
        chat_id=chat_id,
        message_id=message_id,
        user_id=user_id,
        username=username,
        first_name=first_name,
        url=url,
    )
    return Update(update_id=1, message=message)


def _make_group_link_edited_update(
    *,
    chat_id: int = CHAT_ID,
    message_id: int = LINK_MESSAGE_ID,
    user_id: int = AUTHOR_USER_ID,
    username: str | None = "alice",
    first_name: str = "Alice",
    url: str = INSTAGRAM_URL,
) -> Update:
    """Simulate Telegram's edited_message update sent when a reaction changes."""
    message = _make_group_link_message(
        chat_id=chat_id,
        message_id=message_id,
        user_id=user_id,
        username=username,
        first_name=first_name,
        url=url,
        edit_date=datetime.now(tz=UTC),
    )
    return Update(update_id=2, edited_message=message)


async def _get_message(
    engine: AsyncEngine, chat_id: int, message_id: int
) -> MessageModel | None:
    async with AsyncSession(engine) as session:
        return await session.get(MessageModel, (chat_id, message_id))


async def _get_user_id(engine: AsyncEngine, chat_id: int, message_id: int) -> int | None:
    message = await _get_message(engine, chat_id, message_id)
    return message.user_id if message is not None else None


async def test_registers_link_message_when_user_posts_valid_url(
    engine: AsyncEngine,
    message_repo: MessageRepo,
) -> None:
    handler = GroupMessageHandler((StubPlatformHandler(),), message_repo)
    update = _make_group_link_update()

    await handler.handle(update, cast(Any, None))

    message = await _get_message(engine, CHAT_ID, LINK_MESSAGE_ID)
    assert message is not None
    assert message.user_id == AUTHOR_USER_ID
    assert message.username == "alice"
    assert message.display_name == "Alice"


async def test_registers_bot_video_with_same_user_id_after_successful_process(
    engine: AsyncEngine,
    message_repo: MessageRepo,
) -> None:
    handler = GroupMessageHandler(
        (StubPlatformHandler(bot_message_ids=(BOT_VIDEO_MESSAGE_ID,)),),
        message_repo,
    )
    update = _make_group_link_update()

    await handler.handle(update, cast(Any, None))

    assert await _get_user_id(engine, CHAT_ID, LINK_MESSAGE_ID) == AUTHOR_USER_ID
    assert await _get_user_id(engine, CHAT_ID, BOT_VIDEO_MESSAGE_ID) == AUTHOR_USER_ID


async def test_does_not_register_bot_video_when_process_fails(
    engine: AsyncEngine,
    message_repo: MessageRepo,
) -> None:
    handler = GroupMessageHandler(
        (StubPlatformHandler(bot_message_ids=(BOT_VIDEO_MESSAGE_ID,), ok=False),),
        message_repo,
    )
    update = _make_group_link_update()

    await handler.handle(update, cast(Any, None))

    assert await _get_user_id(engine, CHAT_ID, LINK_MESSAGE_ID) == AUTHOR_USER_ID
    assert await _get_user_id(engine, CHAT_ID, BOT_VIDEO_MESSAGE_ID) is None


async def test_skips_registration_for_unknown_platform(
    engine: AsyncEngine,
    message_repo: MessageRepo,
) -> None:
    handler = GroupMessageHandler((StubPlatformHandler(),), message_repo)
    update = _make_group_link_update(url="https://example.com/video")

    await handler.handle(update, cast(Any, None))

    assert await _get_user_id(engine, CHAT_ID, LINK_MESSAGE_ID) is None


async def test_registers_link_once_for_multiple_urls(
    engine: AsyncEngine,
    message_repo: MessageRepo,
) -> None:
    handler = GroupMessageHandler(
        (StubPlatformHandler(bot_message_ids=(BOT_VIDEO_MESSAGE_ID,)),),
        message_repo,
    )
    text = f"{INSTAGRAM_URL} and {INSTAGRAM_URL}"
    offset = text.index(INSTAGRAM_URL)
    entities = (
        MessageEntity(type=MessageEntity.URL, offset=offset, length=len(INSTAGRAM_URL)),
        MessageEntity(
            type=MessageEntity.URL,
            offset=offset + len(INSTAGRAM_URL) + 5,
            length=len(INSTAGRAM_URL),
        ),
    )
    chat = Chat(id=CHAT_ID, type=ChatType.GROUP, title="Test")
    user = User(id=AUTHOR_USER_ID, is_bot=False, first_name="Alice")
    message = Message(
        message_id=LINK_MESSAGE_ID,
        date=datetime.now(tz=UTC),
        chat=chat,
        from_user=user,
        text=text,
        entities=entities,
    )
    update = Update(update_id=1, message=message)

    await handler.handle(update, cast(Any, None))

    assert await _get_user_id(engine, CHAT_ID, LINK_MESSAGE_ID) == AUTHOR_USER_ID


async def test_does_not_redownload_when_reaction_triggers_edited_message(
    message_repo: MessageRepo,
) -> None:
    """Telegram may send edited_message when a reaction changes, with the same URL.

    The bot must not download/send the video again for that non-content update.
    """
    platform = StubPlatformHandler(bot_message_ids=(BOT_VIDEO_MESSAGE_ID,))
    handler = GroupMessageHandler((platform,), message_repo)

    await handler.handle(_make_group_link_update(), cast(Any, None))
    assert platform.process_calls == [INSTAGRAM_URL]

    await handler.handle(_make_group_link_edited_update(), cast(Any, None))
    assert platform.process_calls == [INSTAGRAM_URL]
