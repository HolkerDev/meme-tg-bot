import logging
from datetime import UTC, datetime
from typing import Literal, NamedTuple
from zoneinfo import ZoneInfo

from sqlalchemy import and_
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from meme_nova.models import MessageModel, SuperLikeModel

type SuperLikeResult = Literal["added", "already_today", "self", "unknown"]

SUPER_LIKE_TIMEZONE = ZoneInfo("Europe/Berlin")


class WeeklyReactionCount(NamedTuple):
    user_id: int
    reaction_count: int
    username: str | None
    display_name: str | None
    super_like_count: int = 0


class MessageRepo:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def register_message(
        self,
        chat_id: int,
        message_id: int,
        user_id: int,
        *,
        username: str | None = None,
        display_name: str | None = None,
        posted_at: datetime | None = None,
    ) -> None:
        async with AsyncSession(self._engine) as session:
            statement = insert(MessageModel).values(
                chat_id=chat_id,
                message_id=message_id,
                user_id=user_id,
                username=username,
                display_name=display_name,
                reaction_count=0,
                posted_at=posted_at or datetime.now(UTC),
            )
            statement = statement.on_conflict_do_update(
                index_elements=["chat_id", "message_id"],
                set_={
                    "user_id": statement.excluded.user_id,
                    "username": statement.excluded.username,
                    "display_name": statement.excluded.display_name,
                },
            )
            await session.exec(statement)
            await session.commit()

    async def weekly_reaction_counts(
        self, chat_id: int, since: datetime
    ) -> list[WeeklyReactionCount]:
        async with AsyncSession(self._engine) as session:
            statement = (
                select(
                    MessageModel.user_id,
                    func.sum(MessageModel.reaction_count),
                    func.max(MessageModel.username),
                    func.max(MessageModel.display_name),
                )
                .where(MessageModel.chat_id == chat_id)
                .where(MessageModel.posted_at >= since)
                .group_by(col(MessageModel.user_id))
            )
            rows = (await session.exec(statement)).all()
            super_like_statement = (
                select(MessageModel.user_id, func.count(col(SuperLikeModel.voter_user_id)))
                .join(
                    SuperLikeModel,
                    and_(
                        col(MessageModel.chat_id) == col(SuperLikeModel.chat_id),
                        col(MessageModel.message_id) == col(SuperLikeModel.message_id),
                    ),
                )
                .where(MessageModel.chat_id == chat_id)
                .where(MessageModel.posted_at >= since)
                .group_by(col(MessageModel.user_id))
            )
            super_like_counts = dict((await session.exec(super_like_statement)).all())
            return [
                WeeklyReactionCount(
                    user_id=user_id,
                    reaction_count=int(total),
                    username=username,
                    display_name=display_name,
                    super_like_count=int(super_like_counts.get(user_id, 0)),
                )
                for user_id, total, username, display_name in rows
            ]

    async def add_super_like(
        self, chat_id: int, message_id: int, voter_user_id: int, *, now: datetime | None = None
    ) -> SuperLikeResult:
        async with AsyncSession(self._engine) as session:
            message = await session.get(MessageModel, (chat_id, message_id))
            if message is None:
                return "unknown"
            if message.user_id == voter_user_id:
                return "self"
            created_at = now or datetime.now(UTC)
            statement = (
                insert(SuperLikeModel)
                .values(
                    chat_id=chat_id,
                    message_id=message_id,
                    voter_user_id=voter_user_id,
                    vote_day=created_at.astimezone(SUPER_LIKE_TIMEZONE).date(),
                    created_at=created_at,
                )
                .on_conflict_do_nothing()
            )
            result = await session.exec(statement)
            await session.commit()
            return "added" if result.rowcount else "already_today"

    async def super_like_count(self, chat_id: int, message_id: int) -> int:
        async with AsyncSession(self._engine) as session:
            statement = select(func.count()).where(
                col(SuperLikeModel.chat_id) == chat_id,
                col(SuperLikeModel.message_id) == message_id,
            )
            return int((await session.exec(statement)).one())

    async def distinct_chat_ids(self) -> list[int]:
        async with AsyncSession(self._engine) as session:
            statement = select(MessageModel.chat_id).distinct()
            rows = (await session.exec(statement)).all()
            return list(rows)

    async def update_reaction_count(self, chat_id: int, message_id: int, count: int) -> bool:
        async with AsyncSession(self._engine) as session:
            message = await session.get(MessageModel, (chat_id, message_id))
            if message is None:
                return False
            message.reaction_count = count
            session.add(message)
            await session.commit()
            return True

    async def apply_reaction_delta(self, chat_id: int, message_id: int, delta: int) -> bool:
        if delta == 0:
            return True
        async with AsyncSession(self._engine) as session:
            message = await session.get(MessageModel, (chat_id, message_id))
            if message is None:
                logging.log(logging.WARNING, "could not find message to apply delta to")
                return False
            message.reaction_count = max(0, message.reaction_count + delta)
            session.add(message)
            await session.commit()
            return True
