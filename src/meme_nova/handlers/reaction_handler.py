import logging

from telegram import ReactionCount, Update
from telegram.ext import ContextTypes, MessageReactionHandler

from meme_nova.handlers.base import Handler
from meme_nova.repositories.message_repo import MessageRepo
from meme_nova.types import BotApplication

logger = logging.getLogger(__name__)


def _count_total_reactions(reactions: tuple[ReactionCount, ...]) -> int:
    return sum(reaction.total_count for reaction in reactions)


class ReactionHandler(Handler):
    def __init__(self, message_repo: MessageRepo) -> None:
        self._message_repo = message_repo

    async def handle(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        event = update.message_reaction_count
        if not event:
            return

        total = _count_total_reactions(event.reactions)
        updated = await self._message_repo.update_reaction_count(
            event.chat.id,
            event.message_id,
            total,
        )
        if not updated:
            logger.debug(
                "ignoring reaction count for untracked message chat_id=%s message_id=%s",
                event.chat.id,
                event.message_id,
            )

    def register(self, app: BotApplication) -> None:
        app.add_handler(
            MessageReactionHandler(
                self.handle,
                message_reaction_types=MessageReactionHandler.MESSAGE_REACTION_COUNT_UPDATED,
            )
        )
