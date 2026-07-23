from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import AsyncMock

from meme_nova.reports.weekly_reaction_job import publish_weekly_reaction_reports
from meme_nova.repositories.message_repo import MessageRepo

CHAT_ID = 100


async def test_publish_weekly_reaction_reports_uses_db_username(
    message_repo: MessageRepo,
) -> None:
    await message_repo.register_message(
        CHAT_ID,
        10,
        user_id=1,
        username="alice",
        display_name="Alice",
        posted_at=datetime.now(tz=UTC),
    )
    await message_repo.update_reaction_count(CHAT_ID, 10, 4)

    bot = AsyncMock()
    await publish_weekly_reaction_reports(cast(Any, bot), message_repo)

    bot.get_chat_member.assert_not_awaited()
    bot.send_message.assert_awaited_once()
    call = bot.send_message.await_args
    assert call is not None
    assert call.kwargs["chat_id"] == CHAT_ID
    assert "@alice — 4 reactions" in call.kwargs["text"]


async def test_publish_weekly_reaction_reports_falls_back_to_telegram(
    message_repo: MessageRepo,
) -> None:
    await message_repo.register_message(
        CHAT_ID,
        10,
        user_id=1,
        posted_at=datetime.now(tz=UTC),
    )
    await message_repo.update_reaction_count(CHAT_ID, 10, 4)

    bot = AsyncMock()
    bot.get_chat_member.return_value = type(
        "Member",
        (),
        {"user": type("User", (), {"username": "alice", "full_name": "Alice"})()},
    )()

    await publish_weekly_reaction_reports(cast(Any, bot), message_repo)

    bot.get_chat_member.assert_awaited_once()
    bot.send_message.assert_awaited_once()
    call = bot.send_message.await_args
    assert call is not None
    assert call.kwargs["chat_id"] == CHAT_ID
    assert "@alice — 4 reactions" in call.kwargs["text"]


async def test_publish_weekly_reaction_reports_skips_channels_without_reactions(
    message_repo: MessageRepo,
) -> None:
    await message_repo.register_message(
        CHAT_ID,
        10,
        user_id=1,
        posted_at=datetime.now(tz=UTC),
    )

    bot = AsyncMock()
    await publish_weekly_reaction_reports(cast(Any, bot), message_repo)

    bot.send_message.assert_not_awaited()
