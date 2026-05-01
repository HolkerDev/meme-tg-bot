from pathlib import Path

import pytest

from meme_nova.stats_store import WEEK_SECONDS, StatsStore


@pytest.fixture
def store(tmp_path: Path) -> StatsStore:
    return StatsStore(tmp_path / "stats.db")


async def test_top_users_orders_by_count_desc(store: StatsStore) -> None:
    chat = 100
    for _ in range(5):
        await store.record_post(chat, user_id=1, display_name="@alice", now=1000.0)
    for _ in range(2):
        await store.record_post(chat, user_id=2, display_name="@bob", now=1000.0)
    await store.record_post(chat, user_id=3, display_name="@carol", now=1000.0)
    await store.record_post(chat, user_id=4, display_name="@dave", now=1000.0)

    top = await store.top_users(chat, since=0.0)
    assert [(u.user_id, u.count) for u in top] == [(1, 5), (2, 2), (3, 1)]


async def test_top_users_filters_by_chat(store: StatsStore) -> None:
    await store.record_post(100, user_id=1, display_name="@alice", now=1000.0)
    await store.record_post(200, user_id=1, display_name="@alice", now=1000.0)
    await store.record_post(200, user_id=1, display_name="@alice", now=1000.0)

    top_a = await store.top_users(100, since=0.0)
    top_b = await store.top_users(200, since=0.0)
    assert top_a[0].count == 1
    assert top_b[0].count == 2


async def test_top_users_filters_by_window(store: StatsStore) -> None:
    chat = 100
    await store.record_post(chat, user_id=1, display_name="@alice", now=100.0)
    await store.record_post(chat, user_id=1, display_name="@alice", now=2000.0)

    top = await store.top_users(chat, since=1000.0)
    assert top[0].count == 1


async def test_top_users_uses_latest_display_name(store: StatsStore) -> None:
    chat = 100
    await store.record_post(chat, user_id=1, display_name="@old", now=100.0)
    await store.record_post(chat, user_id=1, display_name="@new", now=200.0)

    top = await store.top_users(chat, since=0.0)
    assert top[0].display_name == "@new"


async def test_due_chats_returns_chats_past_interval(store: StatsStore) -> None:
    await store.record_post(100, user_id=1, display_name="@alice", now=1000.0)
    await store.record_post(200, user_id=1, display_name="@alice", now=1000.0 + WEEK_SECONDS)

    due = await store.due_chats(now=1000.0 + WEEK_SECONDS)
    assert {c.chat_id for c in due} == {100}


async def test_mark_published_resets_clock(store: StatsStore) -> None:
    await store.record_post(100, user_id=1, display_name="@alice", now=1000.0)
    assert {c.chat_id for c in await store.due_chats(now=1000.0 + WEEK_SECONDS)} == {100}

    await store.mark_published(100, now=1000.0 + WEEK_SECONDS)
    assert await store.due_chats(now=1000.0 + WEEK_SECONDS) == []
