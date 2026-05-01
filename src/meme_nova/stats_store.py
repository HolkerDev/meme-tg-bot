import asyncio
import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

WEEK_SECONDS = 7 * 24 * 3600
TOP_N = 3


@dataclass(frozen=True)
class TopUser:
    user_id: int
    display_name: str
    count: int


@dataclass(frozen=True)
class DueChat:
    chat_id: int
    last_published_at: float


class StatsStore:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
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
                CREATE TABLE IF NOT EXISTS link_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    display_name TEXT NOT NULL,
                    posted_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_link_posts_chat_time "
                "ON link_posts(chat_id, posted_at)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_stats_state (
                    chat_id INTEGER PRIMARY KEY,
                    last_published_at REAL NOT NULL
                )
                """
            )

    async def record_post(
        self, chat_id: int, user_id: int, display_name: str, now: float | None = None
    ) -> None:
        ts = now if now is not None else time.time()
        await asyncio.to_thread(self._record_sync, chat_id, user_id, display_name, ts)

    def _record_sync(
        self, chat_id: int, user_id: int, display_name: str, ts: float
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO link_posts (chat_id, user_id, display_name, posted_at) "
                "VALUES (?, ?, ?, ?)",
                (chat_id, user_id, display_name, ts),
            )
            conn.execute(
                "INSERT OR IGNORE INTO chat_stats_state (chat_id, last_published_at) "
                "VALUES (?, ?)",
                (chat_id, ts),
            )

    async def top_users(self, chat_id: int, since: float, limit: int = TOP_N) -> list[TopUser]:
        rows = await asyncio.to_thread(self._top_users_sync, chat_id, since, limit)
        return [TopUser(user_id=r["user_id"], display_name=r["display_name"], count=r["cnt"])
                for r in rows]

    def _top_users_sync(
        self, chat_id: int, since: float, limit: int
    ) -> list[sqlite3.Row]:
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT user_id, display_name, cnt FROM (
                    SELECT
                        user_id,
                        display_name,
                        COUNT(*) OVER (PARTITION BY user_id) AS cnt,
                        ROW_NUMBER() OVER (
                            PARTITION BY user_id ORDER BY posted_at DESC
                        ) AS rn
                    FROM link_posts
                    WHERE chat_id = ? AND posted_at >= ?
                )
                WHERE rn = 1
                ORDER BY cnt DESC, user_id
                LIMIT ?
                """,
                (chat_id, since, limit),
            )
            return list(cur.fetchall())

    async def due_chats(
        self, now: float | None = None, interval: float = WEEK_SECONDS
    ) -> list[DueChat]:
        ts = now if now is not None else time.time()
        rows = await asyncio.to_thread(self._due_chats_sync, ts, interval)
        return [DueChat(chat_id=r["chat_id"], last_published_at=r["last_published_at"])
                for r in rows]

    def _due_chats_sync(self, ts: float, interval: float) -> list[sqlite3.Row]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT chat_id, last_published_at FROM chat_stats_state "
                "WHERE last_published_at <= ?",
                (ts - interval,),
            )
            return list(cur.fetchall())

    async def mark_published(self, chat_id: int, now: float | None = None) -> None:
        ts = now if now is not None else time.time()
        await asyncio.to_thread(self._mark_published_sync, chat_id, ts)

    def _mark_published_sync(self, chat_id: int, ts: float) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE chat_stats_state SET last_published_at = ? WHERE chat_id = ?",
                (ts, chat_id),
            )
