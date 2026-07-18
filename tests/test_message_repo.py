from datetime import UTC, datetime
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine
from telegram import (
    Chat,
    MessageReactionCountUpdated,
    ReactionCount,
    ReactionTypeEmoji,
    Update,
)
from telegram.constants import ChatType

from meme_nova.handlers.reaction_handler import ReactionHandler
from meme_nova.repositories.message_repo import MessageRepo

CHAT_ID = 100
WEEK_START = datetime(2026, 7, 11, tzinfo=UTC)


def _make_reaction_count_update(
    chat_id: int,
    message_id: int,
    *,
    reactions: tuple[ReactionCount, ...],
) -> Update:
    event = MessageReactionCountUpdated(
        chat=Chat(id=chat_id, type=ChatType.GROUP),
        message_id=message_id,
        date=datetime.now(tz=UTC),
        reactions=reactions,
    )
    return Update(update_id=1, message_reaction_count=event)


async def test_register_message_and_update_reaction_count(message_repo: MessageRepo) -> None:
    await message_repo.register_message(
        CHAT_ID,
        10,
        user_id=1,
        posted_at=datetime(2026, 7, 12, tzinfo=UTC),
    )

    updated = await message_repo.update_reaction_count(CHAT_ID, 10, 3)
    assert updated is True

    updated = await message_repo.update_reaction_count(CHAT_ID, 99, 1)
    assert updated is False


async def test_weekly_reaction_counts_per_user_in_channel(message_repo: MessageRepo) -> None:
    await message_repo.register_message(
        CHAT_ID,
        10,
        user_id=1,
        posted_at=datetime(2026, 7, 12, tzinfo=UTC),
    )
    await message_repo.update_reaction_count(CHAT_ID, 10, 3)

    await message_repo.register_message(
        CHAT_ID,
        20,
        user_id=2,
        posted_at=datetime(2026, 7, 13, tzinfo=UTC),
    )
    await message_repo.update_reaction_count(CHAT_ID, 20, 1)

    await message_repo.register_message(
        CHAT_ID,
        30,
        user_id=1,
        posted_at=datetime(2026, 7, 14, tzinfo=UTC),
    )
    await message_repo.update_reaction_count(CHAT_ID, 30, 2)

    await message_repo.register_message(
        CHAT_ID,
        40,
        user_id=1,
        posted_at=datetime(2026, 7, 1, tzinfo=UTC),
    )
    await message_repo.update_reaction_count(CHAT_ID, 40, 100)

    counts = await message_repo.weekly_reaction_counts(CHAT_ID, WEEK_START)
    assert counts == {1: 5, 2: 1}


async def test_weekly_reaction_counts_are_scoped_to_channel(message_repo: MessageRepo) -> None:
    await message_repo.register_message(
        CHAT_ID,
        10,
        user_id=1,
        posted_at=datetime(2026, 7, 12, tzinfo=UTC),
    )
    await message_repo.update_reaction_count(CHAT_ID, 10, 4)

    await message_repo.register_message(
        200,
        10,
        user_id=1,
        posted_at=datetime(2026, 7, 12, tzinfo=UTC),
    )
    await message_repo.update_reaction_count(200, 10, 7)

    assert await message_repo.weekly_reaction_counts(CHAT_ID, WEEK_START) == {1: 4}
    assert await message_repo.weekly_reaction_counts(200, WEEK_START) == {1: 7}


async def test_reaction_handler_updates_weekly_counts(
    message_repo: MessageRepo,
) -> None:
    await message_repo.register_message(
        CHAT_ID,
        10,
        user_id=1,
        posted_at=datetime(2026, 7, 12, tzinfo=UTC),
    )

    handler = ReactionHandler(message_repo)
    update = _make_reaction_count_update(
        CHAT_ID,
        10,
        reactions=(
            ReactionCount(type=ReactionTypeEmoji("🔥"), total_count=2),
            ReactionCount(type=ReactionTypeEmoji("👍"), total_count=1),
        ),
    )
    await handler.handle(update, cast(Any, None))

    counts = await message_repo.weekly_reaction_counts(CHAT_ID, WEEK_START)
    assert counts == {1: 3}


async def test_link_and_bot_video_share_user_id(message_repo: MessageRepo) -> None:
    author_user_id = 1
    bot_user_id = 42
    link_message_id = 10
    bot_video_message_id = 99
    posted_at = datetime(2026, 7, 12, tzinfo=UTC)

    await message_repo.register_message(
        CHAT_ID,
        link_message_id,
        user_id=author_user_id,
        posted_at=posted_at,
    )
    await message_repo.register_message(
        CHAT_ID,
        bot_video_message_id,
        user_id=author_user_id,
        posted_at=posted_at,
    )

    await message_repo.update_reaction_count(CHAT_ID, link_message_id, 3)
    await message_repo.update_reaction_count(CHAT_ID, bot_video_message_id, 2)

    counts = await message_repo.weekly_reaction_counts(CHAT_ID, WEEK_START)
    assert counts == {author_user_id: 5}
    assert bot_user_id not in counts


async def test_reaction_handler_ignores_untracked_messages(message_repo: MessageRepo) -> None:
    handler = ReactionHandler(message_repo)
    update = _make_reaction_count_update(
        CHAT_ID,
        10,
        reactions=(ReactionCount(type=ReactionTypeEmoji("🔥"), total_count=1),),
    )

    await handler.handle(update, cast(Any, None))

    assert await message_repo.weekly_reaction_counts(CHAT_ID, WEEK_START) == {}
