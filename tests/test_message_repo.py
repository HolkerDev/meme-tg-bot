from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession
from telegram import (
    Chat,
    MessageReactionCountUpdated,
    MessageReactionUpdated,
    ReactionCount,
    ReactionType,
    ReactionTypeEmoji,
    Update,
    User,
)
from telegram.constants import ChatType

from meme_nova.handlers.reaction_handler import ReactionHandler
from meme_nova.models import MessageModel
from meme_nova.repositories.message_repo import MessageRepo, WeeklyReactionCount

CHAT_ID = 100
WEEK_START = datetime(2026, 7, 11, tzinfo=UTC)


def _counts_map(rows: list[WeeklyReactionCount]) -> dict[int, int]:
    return {row.user_id: row.reaction_count for row in rows}


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


def _make_reaction_update(
    chat_id: int,
    message_id: int,
    *,
    old: tuple[ReactionType, ...] = (),
    new: tuple[ReactionType, ...] = (),
    user_id: int = 7,
) -> Update:
    event = MessageReactionUpdated(
        chat=Chat(id=chat_id, type=ChatType.GROUP),
        message_id=message_id,
        date=datetime.now(tz=UTC),
        user=User(id=user_id, is_bot=False, first_name="Reactor"),
        old_reaction=old,
        new_reaction=new,
    )
    return Update(update_id=1, message_reaction=event)


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


async def test_register_message_upserts_without_resetting_counts(
    message_repo: MessageRepo,
    engine: AsyncEngine,
) -> None:
    posted_at = datetime(2026, 7, 12, tzinfo=UTC)
    await message_repo.register_message(CHAT_ID, 10, user_id=1, posted_at=posted_at)
    await message_repo.update_reaction_count(CHAT_ID, 10, 5)

    await message_repo.register_message(
        CHAT_ID,
        10,
        user_id=2,
        username="bob",
        display_name="Bob",
        posted_at=posted_at,
    )

    async with AsyncSession(engine) as session:
        message = await session.get(MessageModel, (CHAT_ID, 10))
        assert message is not None
        assert message.user_id == 2
        assert message.username == "bob"
        assert message.display_name == "Bob"
        assert message.reaction_count == 5


async def test_register_message_persists_username_and_display_name(
    message_repo: MessageRepo,
    engine: AsyncEngine,
) -> None:
    await message_repo.register_message(
        CHAT_ID,
        10,
        user_id=1,
        username="alice",
        display_name="Alice",
        posted_at=datetime(2026, 7, 12, tzinfo=UTC),
    )

    async with AsyncSession(engine) as session:
        message = await session.get(MessageModel, (CHAT_ID, 10))
        assert message is not None
        assert message.username == "alice"
        assert message.display_name == "Alice"


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

    rows = await message_repo.weekly_reaction_counts(CHAT_ID, WEEK_START)
    assert _counts_map(rows) == {1: 5, 2: 1}


async def test_weekly_reaction_counts_include_identity(message_repo: MessageRepo) -> None:
    await message_repo.register_message(
        CHAT_ID,
        10,
        user_id=1,
        username="alice",
        display_name="Alice",
        posted_at=datetime(2026, 7, 12, tzinfo=UTC),
    )
    await message_repo.update_reaction_count(CHAT_ID, 10, 3)

    rows = await message_repo.weekly_reaction_counts(CHAT_ID, WEEK_START)
    assert len(rows) == 1
    assert rows[0].user_id == 1
    assert rows[0].reaction_count == 3
    assert rows[0].username == "alice"
    assert rows[0].display_name == "Alice"


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

    assert _counts_map(await message_repo.weekly_reaction_counts(CHAT_ID, WEEK_START)) == {1: 4}
    assert _counts_map(await message_repo.weekly_reaction_counts(200, WEEK_START)) == {1: 7}


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

    assert _counts_map(await message_repo.weekly_reaction_counts(CHAT_ID, WEEK_START)) == {1: 3}


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

    counts = _counts_map(await message_repo.weekly_reaction_counts(CHAT_ID, WEEK_START))
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

    assert await message_repo.weekly_reaction_counts(CHAT_ID, WEEK_START) == []


async def test_apply_reaction_delta_clamps_at_zero(message_repo: MessageRepo) -> None:
    await message_repo.register_message(
        CHAT_ID,
        10,
        user_id=1,
        posted_at=datetime(2026, 7, 12, tzinfo=UTC),
    )
    await message_repo.update_reaction_count(CHAT_ID, 10, 1)

    assert await message_repo.apply_reaction_delta(CHAT_ID, 10, -5) is True
    assert _counts_map(await message_repo.weekly_reaction_counts(CHAT_ID, WEEK_START)) == {1: 0}
    assert await message_repo.apply_reaction_delta(CHAT_ID, 99, 1) is False


async def test_reaction_handler_applies_user_reaction_deltas(
    message_repo: MessageRepo,
) -> None:
    await message_repo.register_message(
        CHAT_ID,
        10,
        user_id=1,
        posted_at=datetime(2026, 7, 12, tzinfo=UTC),
    )
    handler = ReactionHandler(message_repo)
    fire = ReactionTypeEmoji("🔥")
    thumb = ReactionTypeEmoji("👍")

    # add → remove → add should net to 1
    await handler.handle(
        _make_reaction_update(CHAT_ID, 10, old=(), new=(fire,)),
        cast(Any, None),
    )
    await handler.handle(
        _make_reaction_update(CHAT_ID, 10, old=(fire,), new=()),
        cast(Any, None),
    )
    await handler.handle(
        _make_reaction_update(CHAT_ID, 10, old=(), new=(fire,)),
        cast(Any, None),
    )
    assert _counts_map(await message_repo.weekly_reaction_counts(CHAT_ID, WEEK_START)) == {1: 1}

    # two emoji types from one user count as +2
    await handler.handle(
        _make_reaction_update(CHAT_ID, 10, old=(fire,), new=(fire, thumb)),
        cast(Any, None),
    )
    assert _counts_map(await message_repo.weekly_reaction_counts(CHAT_ID, WEEK_START)) == {1: 2}


async def test_reaction_handler_ignores_untracked_user_reactions(
    message_repo: MessageRepo,
) -> None:
    handler = ReactionHandler(message_repo)
    await handler.handle(
        _make_reaction_update(CHAT_ID, 10, old=(), new=(ReactionTypeEmoji("🔥"),)),
        cast(Any, None),
    )
    assert await message_repo.weekly_reaction_counts(CHAT_ID, WEEK_START) == []


async def test_distinct_chat_ids(message_repo: MessageRepo) -> None:
    await message_repo.register_message(
        CHAT_ID,
        10,
        user_id=1,
        posted_at=datetime(2026, 7, 12, tzinfo=UTC),
    )
    await message_repo.register_message(
        200,
        10,
        user_id=1,
        posted_at=datetime(2026, 7, 12, tzinfo=UTC),
    )
    await message_repo.register_message(
        CHAT_ID,
        20,
        user_id=2,
        posted_at=datetime(2026, 7, 12, tzinfo=UTC),
    )

    assert sorted(await message_repo.distinct_chat_ids()) == [CHAT_ID, 200]
