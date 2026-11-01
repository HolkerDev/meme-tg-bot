from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

from telegram import Chat, Message
from telegram.constants import ChatType

from meme_nova.constants import MAIN_CHAT_ID, SUPER_LIKE_CALLBACK
from meme_nova.handlers.super_like_handler import SuperLikeHandler
from meme_nova.repositories.message_repo import MessageRepo


async def test_super_like_callback_credits_video_sender_once(message_repo: MessageRepo) -> None:
    await message_repo.register_message(MAIN_CHAT_ID, 42, user_id=1)
    message = Message(
        message_id=42,
        date=datetime.now(tz=UTC),
        chat=Chat(id=MAIN_CHAT_ID, type=ChatType.SUPERGROUP),
    )
    query = SimpleNamespace(
        data=SUPER_LIKE_CALLBACK,
        message=message,
        from_user=SimpleNamespace(id=2),
        answer=AsyncMock(),
        edit_message_reply_markup=AsyncMock(),
    )
    update = cast(Any, SimpleNamespace(callback_query=query))
    handler = SuperLikeHandler(message_repo)

    await handler.handle(update, cast(Any, None))
    query.answer.assert_awaited_with("Потужний лайк зараховано!")
    markup = query.edit_message_reply_markup.await_args.kwargs["reply_markup"]
    assert markup.inline_keyboard[0][0].text == "Потужний лайк · 1"

    await handler.handle(update, cast(Any, None))
    query.answer.assert_awaited_with("You already used today's Super Like.")
    query.edit_message_reply_markup.assert_awaited_once()

    rows = await message_repo.weekly_reaction_counts(MAIN_CHAT_ID, datetime(2026, 1, 1, tzinfo=UTC))
    assert rows[0].user_id == 1
    assert rows[0].super_like_count == 1


async def test_super_like_callback_ignores_other_chats(message_repo: MessageRepo) -> None:
    message = Message(
        message_id=42,
        date=datetime.now(tz=UTC),
        chat=Chat(id=100, type=ChatType.GROUP),
    )
    query = SimpleNamespace(
        data=SUPER_LIKE_CALLBACK,
        message=message,
        from_user=SimpleNamespace(id=2),
        answer=AsyncMock(),
        edit_message_reply_markup=AsyncMock(),
    )
    handler = SuperLikeHandler(message_repo)

    await handler.handle(cast(Any, SimpleNamespace(callback_query=query)), cast(Any, None))

    query.answer.assert_awaited_with("Super Likes are available only in Memeproxy.")
