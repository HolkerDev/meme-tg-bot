import asyncio
import sqlite3
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from telegram import ReactionTypeCustomEmoji, ReactionTypeEmoji, ReactionTypePaid
from telegram.constants import ReactionType

TOP_N = 3


@dataclass(frozen=True)
class MessageAuthor:
    user_id: int
    display_name: str


@dataclass(frozen=True)
class TopRecipient:
    user_id: int
    display_name: str
    count: int


def reaction_keys(reactions: Sequence[object]) -> set[str]:
    keys: set[str] = set()
    for reaction in reactions:
        if isinstance(reaction, ReactionTypeEmoji):
            keys.add(reaction.emoji)
        elif isinstance(reaction, ReactionTypeCustomEmoji):
            keys.add(f"custom:{reaction.custom_emoji_id}")
        elif isinstance(reaction, ReactionTypePaid):
            keys.add("paid")
        elif getattr(reaction, "type", None) == ReactionType.EMOJI:
            keys.add(reaction.emoji)  # type: ignore[attr-defined]
        elif getattr(reaction, "type", None) == ReactionType.CUSTOM_EMOJI:
            keys.add(f"custom:{reaction.custom_emoji_id}")  # type: ignore[attr-defined]
        elif getattr(reaction, "type", None) == ReactionType.PAID:
            keys.add("paid")
    return keys


class ReactionStore:
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
                CREATE TABLE IF NOT EXISTS tracked_messages (
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    author_user_id INTEGER NOT NULL,
                    author_display_name TEXT NOT NULL,
                    source_message_id INTEGER NOT NULL,
                    registered_at REAL NOT NULL,
                    PRIMARY KEY (chat_id, message_id)
                )
                """
            )
            self._ensure_column(
                conn,
                "tracked_messages",
                "source_message_id",
                "INTEGER NOT NULL DEFAULT 0",
            )
            conn.execute(
                """
                UPDATE tracked_messages
                SET source_message_id = message_id
                WHERE source_message_id = 0
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reactions_received (
                    chat_id INTEGER NOT NULL,
                    source_message_id INTEGER NOT NULL,
                    author_user_id INTEGER NOT NULL,
                    author_display_name TEXT NOT NULL,
                    reactor_user_id INTEGER NOT NULL,
                    emoji TEXT NOT NULL,
                    reacted_at REAL NOT NULL,
                    PRIMARY KEY (
                        chat_id, source_message_id, reactor_user_id, emoji
                    )
                )
                """
            )
            self._ensure_column(
                conn,
                "reactions_received",
                "source_message_id",
                "INTEGER NOT NULL DEFAULT 0",
            )
            self._migrate_reactions_primary_key(conn)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_reactions_chat_time "
                "ON reactions_received (chat_id, reacted_at)"
            )

    def _ensure_column(
        self, conn: sqlite3.Connection, table: str, column: str, definition: str
    ) -> None:
        columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _migrate_reactions_primary_key(self, conn: sqlite3.Connection) -> None:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'reactions_received'"
        ).fetchone()
        if row is None or "source_message_id" in row["sql"]:
            return
        conn.execute(
            """
            CREATE TABLE reactions_received_new (
                chat_id INTEGER NOT NULL,
                source_message_id INTEGER NOT NULL,
                author_user_id INTEGER NOT NULL,
                author_display_name TEXT NOT NULL,
                reactor_user_id INTEGER NOT NULL,
                emoji TEXT NOT NULL,
                reacted_at REAL NOT NULL,
                PRIMARY KEY (chat_id, source_message_id, reactor_user_id, emoji)
            )
            """
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO reactions_received_new (
                chat_id,
                source_message_id,
                author_user_id,
                author_display_name,
                reactor_user_id,
                emoji,
                reacted_at
            )
            SELECT
                chat_id,
                target_message_id,
                author_user_id,
                author_display_name,
                reactor_user_id,
                emoji,
                reacted_at
            FROM reactions_received
            """
        )
        conn.execute("DROP TABLE reactions_received")
        conn.execute("ALTER TABLE reactions_received_new RENAME TO reactions_received")

    async def register_message(
        self,
        chat_id: int,
        message_id: int,
        author_user_id: int,
        author_display_name: str,
        now: float | None = None,
        source_message_id: int | None = None,
    ) -> None:
        ts = now if now is not None else time.time()
        source_id = source_message_id if source_message_id is not None else message_id
        await asyncio.to_thread(
            self._register_message_sync,
            chat_id,
            message_id,
            author_user_id,
            author_display_name,
            source_id,
            ts,
        )

    def _register_message_sync(
        self,
        chat_id: int,
        message_id: int,
        author_user_id: int,
        author_display_name: str,
        source_message_id: int,
        ts: float,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tracked_messages (
                    chat_id,
                    message_id,
                    author_user_id,
                    author_display_name,
                    source_message_id,
                    registered_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (chat_id, message_id) DO UPDATE SET
                    author_user_id = excluded.author_user_id,
                    author_display_name = excluded.author_display_name,
                    source_message_id = excluded.source_message_id
                """,
                (
                    chat_id,
                    message_id,
                    author_user_id,
                    author_display_name,
                    source_message_id,
                    ts,
                ),
            )

    async def lookup_author(self, chat_id: int, message_id: int) -> MessageAuthor | None:
        row = await asyncio.to_thread(self._lookup_author_sync, chat_id, message_id)
        if row is None:
            return None
        return MessageAuthor(
            user_id=row["author_user_id"],
            display_name=row["author_display_name"],
        )

    def _lookup_author_sync(self, chat_id: int, message_id: int) -> sqlite3.Row | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT author_user_id, author_display_name FROM tracked_messages "
                "WHERE chat_id = ? AND message_id = ?",
                (chat_id, message_id),
            ).fetchone()
            return cast(sqlite3.Row | None, row)

    async def apply_reaction_delta(
        self,
        chat_id: int,
        message_id: int,
        reactor_user_id: int,
        old_reactions: Sequence[object],
        new_reactions: Sequence[object],
        now: float | None = None,
    ) -> None:
        ts = now if now is not None else time.time()
        old_keys = reaction_keys(old_reactions)
        new_keys = reaction_keys(new_reactions)
        added = new_keys - old_keys
        removed = old_keys - new_keys
        if not added and not removed:
            return
        await asyncio.to_thread(
            self._apply_reaction_delta_sync,
            chat_id,
            message_id,
            reactor_user_id,
            added,
            removed,
            ts,
        )

    def _apply_reaction_delta_sync(
        self,
        chat_id: int,
        message_id: int,
        reactor_user_id: int,
        added: set[str],
        removed: set[str],
        ts: float,
    ) -> None:
        with self._connect() as conn:
            author = conn.execute(
                "SELECT author_user_id, author_display_name, source_message_id "
                "FROM tracked_messages WHERE chat_id = ? AND message_id = ?",
                (chat_id, message_id),
            ).fetchone()
            if author is None:
                return
            author_user_id = author["author_user_id"]
            author_display_name = author["author_display_name"]
            source_message_id = author["source_message_id"]
            for emoji in removed:
                conn.execute(
                    """
                    DELETE FROM reactions_received
                    WHERE chat_id = ? AND source_message_id = ?
                      AND reactor_user_id = ? AND emoji = ?
                    """,
                    (chat_id, source_message_id, reactor_user_id, emoji),
                )
            for emoji in added:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO reactions_received (
                        chat_id,
                        source_message_id,
                        author_user_id,
                        author_display_name,
                        reactor_user_id,
                        emoji,
                        reacted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chat_id,
                        source_message_id,
                        author_user_id,
                        author_display_name,
                        reactor_user_id,
                        emoji,
                        ts,
                    ),
                )

    async def recipient_counts(self, chat_id: int, since: float) -> dict[int, int]:
        rows = await asyncio.to_thread(self._recipient_counts_sync, chat_id, since)
        return {r["author_user_id"]: r["cnt"] for r in rows}

    def _recipient_counts_sync(self, chat_id: int, since: float) -> list[sqlite3.Row]:
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT author_user_id, COUNT(*) AS cnt
                FROM reactions_received
                WHERE chat_id = ? AND reacted_at >= ?
                GROUP BY author_user_id
                """,
                (chat_id, since),
            )
            return list(cur.fetchall())

    async def top_recipients(
        self, chat_id: int, since: float, limit: int = TOP_N
    ) -> list[TopRecipient]:
        rows = await asyncio.to_thread(self._top_recipients_sync, chat_id, since, limit)
        return [
            TopRecipient(
                user_id=r["author_user_id"],
                display_name=r["author_display_name"],
                count=r["cnt"],
            )
            for r in rows
        ]

    def _top_recipients_sync(self, chat_id: int, since: float, limit: int) -> list[sqlite3.Row]:
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT author_user_id, author_display_name, cnt FROM (
                    SELECT
                        author_user_id,
                        author_display_name,
                        COUNT(*) OVER (PARTITION BY author_user_id) AS cnt,
                        ROW_NUMBER() OVER (
                            PARTITION BY author_user_id
                            ORDER BY reacted_at DESC
                        ) AS rn
                    FROM reactions_received
                    WHERE chat_id = ? AND reacted_at >= ?
                )
                WHERE rn = 1
                ORDER BY cnt DESC, author_user_id
                LIMIT ?
                """,
                (chat_id, since, limit),
            )
            return list(cur.fetchall())
