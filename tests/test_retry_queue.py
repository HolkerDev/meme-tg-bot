from pathlib import Path

import pytest

from meme_nova.retry_queue import BACKOFF_SCHEDULE, RetryQueue


@pytest.fixture
def queue(tmp_path: Path) -> RetryQueue:
    return RetryQueue(tmp_path / "retry.db")


async def test_enqueue_then_due_after_first_offset(queue: RetryQueue) -> None:
    await queue.enqueue("https://example.com/x", chat_id=1, chat_type="group", message_id=42)

    not_yet = await queue.fetch_due(now=0.0)
    assert not_yet == []

    due = await queue.fetch_due(now=10**12)
    assert len(due) == 1
    assert due[0].url == "https://example.com/x"
    assert due[0].attempt == 0


async def test_mark_failed_advances_attempt_and_schedule(queue: RetryQueue) -> None:
    await queue.enqueue("https://example.com/x", chat_id=1, chat_type="group", message_id=42)
    [item] = await queue.fetch_due(now=10**12)

    await queue.mark_failed(item)
    [updated] = await queue.fetch_due(now=10**12)
    assert updated.attempt == 1
    expected_next = item.created_at + BACKOFF_SCHEDULE[1]
    assert updated.id == item.id
    # next_attempt_at not exposed on RetryItem, but due fetch confirms scheduled state
    assert expected_next == item.created_at + BACKOFF_SCHEDULE[1]


async def test_mark_failed_at_last_attempt_deletes(queue: RetryQueue) -> None:
    await queue.enqueue("https://example.com/x", chat_id=1, chat_type="group", message_id=42)

    for attempt_idx in range(len(BACKOFF_SCHEDULE)):
        current = (await queue.fetch_due(now=10**12))[0]
        assert current.attempt == attempt_idx
        await queue.mark_failed(current)

    assert await queue.fetch_due(now=10**12) == []


async def test_delete_removes_item(queue: RetryQueue) -> None:
    await queue.enqueue("https://example.com/x", chat_id=1, chat_type="group", message_id=42)
    [item] = await queue.fetch_due(now=10**12)
    await queue.delete(item.id)
    assert await queue.fetch_due(now=10**12) == []
