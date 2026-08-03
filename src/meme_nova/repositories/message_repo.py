import logging
from datetime import UTC, datetime
from typing import NamedTuple

from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from meme_nova.models import MessageModel


class WeeklyReactionCount(NamedTuple):
    user_id: int
    reaction_count: int
    username: str | None
    display_name: str | None


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
            return [
                WeeklyReactionCount(
                    user_id=user_id,
                    reaction_count=int(total),
                    username=username,
                    display_name=display_name,
                )
                for user_id, total, username, display_name in rows
            ]

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
