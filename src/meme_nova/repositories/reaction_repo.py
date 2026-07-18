import logging

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from meme_nova.models.reaction_model import ReactionModel


class ReactionRepo:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def add_reaction(self, chat_id: int, user_id: int) -> None:
        logging.log(
            logging.INFO, msg=f"adding reaction for chat: [{chat_id}] for user: [{user_id}]"
        )
        async with AsyncSession(self._engine) as session:
            reaction_model = ReactionModel(user_id=user_id, chat_id=chat_id)
            session.add(reaction_model)
            await session.commit()
