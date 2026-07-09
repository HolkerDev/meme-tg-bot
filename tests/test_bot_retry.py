import asyncio
from unittest.mock import MagicMock

import pytest
from telegram import Bot

from meme_nova.bot import _retry_one
from meme_nova.media_dedup import MediaDedupStore
from meme_nova.platforms.base import Platform, ProcessResult
from meme_nova.reaction_store import ReactionStore
from meme_nova.retry_queue import RetryQueue


class SlowCountingHandler:
    platform = Platform.YOUTUBE

    def __init__(self) -> None:
        self.process_calls = 0

    def matches(self, url: str) -> bool:
        return True

    async def process(self, url: str, message: object) -> ProcessResult:
        self.process_calls += 1
        await asyncio.sleep(0.05)
        return ProcessResult.success(1)


@pytest.fixture
def dedup(tmp_path) -> MediaDedupStore:
    return MediaDedupStore(tmp_path / "dedup.db")


@pytest.fixture
def queue(tmp_path) -> RetryQueue:
    return RetryQueue(tmp_path / "retry.db")


@pytest.fixture
def reactions(tmp_path) -> ReactionStore:
    return ReactionStore(tmp_path / "reactions.db")


async def test_concurrent_retries_send_once(
    queue: RetryQueue,
    dedup: MediaDedupStore,
    reactions: ReactionStore,
) -> None:
    """Polling while a download is in flight must not re-send the same video."""
    url = "https://www.youtube.com/watch?v=abc"
    await queue.enqueue(url, chat_id=1, chat_type="group", message_id=42)
    [item] = await queue.fetch_due(now=10**12)

    handler = SlowCountingHandler()
    bot = MagicMock(spec=Bot)

    await asyncio.gather(
        _retry_one(item, (handler,), queue, bot, dedup, reactions),
        _retry_one(item, (handler,), queue, bot, dedup, reactions),
        _retry_one(item, (handler,), queue, bot, dedup, reactions),
    )

    assert handler.process_calls == 1
    assert await dedup.is_posted(1, 42, url)
