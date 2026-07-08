import asyncio
import sqlite3
import time
from pathlib import Path


class MediaDedupStore:
    """Tracks posted media so retries and duplicate updates do not re-send."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._lock_guard = asyncio.Lock()
        self._locks: dict[tuple[int, int, str], asyncio.Lock] = {}
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS posted_media (
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    posted_at REAL NOT NULL,
                    PRIMARY KEY (chat_id, message_id, url)
                )
                """
            )

    async def lock(self, chat_id: int, message_id: int, url: str) -> asyncio.Lock:
        key = (chat_id, message_id, url)
        async with self._lock_guard:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]

    async def is_posted(self, chat_id: int, message_id: int, url: str) -> bool:
        return await asyncio.to_thread(self._is_posted_sync, chat_id, message_id, url)

    def _is_posted_sync(self, chat_id: int, message_id: int, url: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM posted_media WHERE chat_id = ? AND message_id = ? AND url = ?",
                (chat_id, message_id, url),
            ).fetchone()
            return row is not None

    async def mark_posted(self, chat_id: int, message_id: int, url: str) -> None:
        ts = time.time()
        await asyncio.to_thread(self._mark_posted_sync, chat_id, message_id, url, ts)

    def _mark_posted_sync(
        self, chat_id: int, message_id: int, url: str, ts: float
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO posted_media (chat_id, message_id, url, posted_at)
                VALUES (?, ?, ?, ?)
                """,
                (chat_id, message_id, url, ts),
            )
