from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from meme_nova.models import MessageModel


class MessageRepo:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def register_message(
        self,
        chat_id: int,
        message_id: int,
        user_id: int,
        posted_at: datetime | None = None,
    ) -> None:
        async with AsyncSession(self._engine) as session:
            message = MessageModel(
                chat_id=chat_id,
                message_id=message_id,
                user_id=user_id,
                posted_at=posted_at or datetime.now(),
            )
            session.add(message)
            await session.commit()

    async def weekly_reaction_counts(self, chat_id: int, since: datetime) -> dict[int, int]:
        async with AsyncSession(self._engine) as session:
            statement = (
                select(MessageModel.user_id, func.sum(MessageModel.reaction_count))
                .where(MessageModel.chat_id == chat_id)
                .where(MessageModel.posted_at >= since)
                .group_by(col(MessageModel.user_id))
            )
            rows = (await session.exec(statement)).all()
            return {user_id: int(total) for user_id, total in rows}

    async def update_reaction_count(self, chat_id: int, message_id: int, count: int) -> bool:
        async with AsyncSession(self._engine) as session:
            message = await session.get(MessageModel, (chat_id, message_id))
            if message is None:
                return False
            message.reaction_count = count
            session.add(message)
            await session.commit()
            return True
