from pathlib import Path

import pytest
from telegram import ReactionTypeCustomEmoji, ReactionTypeEmoji

from meme_nova.reaction_store import ReactionStore, reaction_keys


@pytest.fixture
def store(tmp_path: Path) -> ReactionStore:
    return ReactionStore(tmp_path / "reactions.db")


async def _register_author(
    store: ReactionStore,
    message_id: int,
    *,
    user_id: int = 1,
    display_name: str = "@alice",
) -> None:
    await store.register_message(
        100, message_id, author_user_id=user_id, author_display_name=display_name, now=1000.0
    )


async def test_register_and_lookup_author(store: ReactionStore) -> None:
    await _register_author(store, 10)
    author = await store.lookup_author(100, 10)
    assert author is not None
    assert author.user_id == 1
    assert author.display_name == "@alice"


async def test_reaction_on_original_message_attributes_to_author(store: ReactionStore) -> None:
    await _register_author(store, 10)
    await store.apply_reaction_delta(
        chat_id=100,
        message_id=10,
        reactor_user_id=2,
        old_reactions=[],
        new_reactions=[ReactionTypeEmoji("🔥")],
        now=1001.0,
    )
    counts = await store.recipient_counts(100, since=0.0)
    assert counts == {1: 1}


async def test_reaction_on_bot_message_attributes_to_author(store: ReactionStore) -> None:
    await _register_author(store, 10)
    await _register_author(store, 99)
    await store.apply_reaction_delta(
        chat_id=100,
        message_id=99,
        reactor_user_id=3,
        old_reactions=[],
        new_reactions=[ReactionTypeEmoji("👍")],
        now=1002.0,
    )
    counts = await store.recipient_counts(100, since=0.0)
    assert counts == {1: 1}


async def test_reaction_change_updates_counts(store: ReactionStore) -> None:
    await _register_author(store, 10)
    await store.apply_reaction_delta(
        chat_id=100,
        message_id=10,
        reactor_user_id=2,
        old_reactions=[],
        new_reactions=[ReactionTypeEmoji("🔥")],
        now=1001.0,
    )
    await store.apply_reaction_delta(
        chat_id=100,
        message_id=10,
        reactor_user_id=2,
        old_reactions=[ReactionTypeEmoji("🔥")],
        new_reactions=[ReactionTypeEmoji("👍")],
        now=1002.0,
    )
    counts = await store.recipient_counts(100, since=0.0)
    assert counts == {1: 1}


async def test_multiple_reactors_count_separately(store: ReactionStore) -> None:
    await _register_author(store, 10)
    await store.apply_reaction_delta(
        chat_id=100,
        message_id=10,
        reactor_user_id=2,
        old_reactions=[],
        new_reactions=[ReactionTypeEmoji("🔥")],
        now=1001.0,
    )
    await store.apply_reaction_delta(
        chat_id=100,
        message_id=10,
        reactor_user_id=3,
        old_reactions=[],
        new_reactions=[ReactionTypeEmoji("🔥"), ReactionTypeEmoji("👍")],
        now=1002.0,
    )
    counts = await store.recipient_counts(100, since=0.0)
    assert counts == {1: 3}


async def test_top_recipients_orders_by_count(store: ReactionStore) -> None:
    await _register_author(store, 10)
    await _register_author(store, 20, user_id=2, display_name="@bob")
    await store.apply_reaction_delta(
        chat_id=100,
        message_id=10,
        reactor_user_id=6,
        old_reactions=[],
        new_reactions=[ReactionTypeEmoji("🔥")],
        now=1001.0,
    )
    await store.apply_reaction_delta(
        chat_id=100,
        message_id=10,
        reactor_user_id=7,
        old_reactions=[],
        new_reactions=[ReactionTypeEmoji("👍")],
        now=1001.0,
    )
    await store.apply_reaction_delta(
        chat_id=100,
        message_id=20,
        reactor_user_id=9,
        old_reactions=[],
        new_reactions=[ReactionTypeEmoji("😂")],
        now=1001.0,
    )
    top = await store.top_recipients(100, since=0.0, limit=2)
    assert [(u.user_id, u.count) for u in top] == [(1, 2), (2, 1)]


async def test_untracked_message_ignored(store: ReactionStore) -> None:
    await store.apply_reaction_delta(
        chat_id=100,
        message_id=10,
        reactor_user_id=2,
        old_reactions=[],
        new_reactions=[ReactionTypeEmoji("🔥")],
        now=1001.0,
    )
    assert await store.recipient_counts(100, since=0.0) == {}


def test_reaction_keys_supports_custom_emoji() -> None:
    keys = reaction_keys([ReactionTypeCustomEmoji("12345")])
    assert keys == {"custom:12345"}


async def test_recipient_counts_respects_window(store: ReactionStore) -> None:
    await _register_author(store, 10)
    await store.apply_reaction_delta(
        chat_id=100,
        message_id=10,
        reactor_user_id=2,
        old_reactions=[],
        new_reactions=[ReactionTypeEmoji("🔥")],
        now=100.0,
    )
    await store.apply_reaction_delta(
        chat_id=100,
        message_id=10,
        reactor_user_id=3,
        old_reactions=[],
        new_reactions=[ReactionTypeEmoji("👍")],
        now=2000.0,
    )
    assert await store.recipient_counts(100, since=1000.0) == {1: 1}
