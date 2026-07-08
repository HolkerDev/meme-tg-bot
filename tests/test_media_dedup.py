from pathlib import Path

import pytest

from meme_nova.media_dedup import MediaDedupStore


@pytest.fixture
def dedup(tmp_path: Path) -> MediaDedupStore:
    return MediaDedupStore(tmp_path / "dedup.db")


async def test_mark_posted_and_is_posted(dedup: MediaDedupStore) -> None:
    assert not await dedup.is_posted(1, 42, "https://instagram.com/p/abc/")
    await dedup.mark_posted(1, 42, "https://instagram.com/p/abc/")
    assert await dedup.is_posted(1, 42, "https://instagram.com/p/abc/")


async def test_is_posted_distinguishes_urls(dedup: MediaDedupStore) -> None:
    await dedup.mark_posted(1, 42, "https://instagram.com/p/abc/")
    assert not await dedup.is_posted(1, 42, "https://instagram.com/p/xyz/")
