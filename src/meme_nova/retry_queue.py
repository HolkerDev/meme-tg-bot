import asyncio
import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

BACKOFF_SCHEDULE: tuple[float, ...] = (15.0, 30.0, 60.0)
POLL_INTERVAL_SECONDS = 5.0


@dataclass(frozen=True)
class RetryItem:
    id: int
    url: str
    chat_id: int
    chat_type: str
    message_id: int
    attempt: int
    created_at: float


class RetryQueue:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._lock = asyncio.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS retry_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    chat_id INTEGER NOT NULL,
                    chat_type TEXT NOT NULL,
                    message_id INTEGER NOT NULL,
                    attempt INTEGER NOT NULL DEFAULT 0,
                    next_attempt_at REAL NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_retry_next ON retry_queue(next_attempt_at)"
            )

    async def enqueue(
        self, url: str, chat_id: int, chat_type: str, message_id: int
    ) -> None:
        now = time.time()
        next_at = now + BACKOFF_SCHEDULE[0]
        await asyncio.to_thread(
            self._enqueue_sync, url, chat_id, chat_type, message_id, now, next_at
        )

    def _enqueue_sync(
        self,
        url: str,
        chat_id: int,
        chat_type: str,
        message_id: int,
        created_at: float,
        next_at: float,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO retry_queue
                    (url, chat_id, chat_type, message_id, attempt, next_attempt_at, created_at)
                VALUES (?, ?, ?, ?, 0, ?, ?)
                """,
                (url, chat_id, chat_type, message_id, next_at, created_at),
            )

    async def fetch_due(self, now: float | None = None) -> list[RetryItem]:
        ts = now if now is not None else time.time()
        rows = await asyncio.to_thread(self._fetch_due_sync, ts)
        return [
            RetryItem(
                id=r["id"],
                url=r["url"],
                chat_id=r["chat_id"],
                chat_type=r["chat_type"],
                message_id=r["message_id"],
                attempt=r["attempt"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def _fetch_due_sync(self, ts: float) -> list[sqlite3.Row]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM retry_queue WHERE next_attempt_at <= ? ORDER BY next_attempt_at",
                (ts,),
            )
            return list(cur.fetchall())

    async def mark_failed(self, item: RetryItem) -> None:
        next_idx = item.attempt + 1
        if next_idx >= len(BACKOFF_SCHEDULE):
            await self.delete(item.id)
            logger.info("retry exhausted for url=%s after %d attempts", item.url, next_idx)
            return
        next_at = item.created_at + BACKOFF_SCHEDULE[next_idx]
        await asyncio.to_thread(self._mark_failed_sync, item.id, next_idx, next_at)

    def _mark_failed_sync(self, item_id: int, attempt: int, next_at: float) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE retry_queue SET attempt = ?, next_attempt_at = ? WHERE id = ?",
                (attempt, next_at, item_id),
            )

    async def delete(self, item_id: int) -> None:
        await asyncio.to_thread(self._delete_sync, item_id)

    def _delete_sync(self, item_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM retry_queue WHERE id = ?", (item_id,))
