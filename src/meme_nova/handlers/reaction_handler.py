import logging
from collections.abc import Sequence

from telegram import (
    ReactionCount,
    ReactionType,
    ReactionTypeCustomEmoji,
    ReactionTypeEmoji,
    ReactionTypePaid,
    Update,
)
from telegram.ext import ContextTypes, MessageReactionHandler

from meme_nova.handlers.base import Handler
from meme_nova.repositories.message_repo import MessageRepo
from meme_nova.types import BotApplication

logger = logging.getLogger(__name__)


def reaction_keys(reactions: Sequence[ReactionType]) -> set[str]:
    keys: set[str] = set()
    for reaction in reactions:
        if isinstance(reaction, ReactionTypeEmoji):
            keys.add(reaction.emoji)
        elif isinstance(reaction, ReactionTypeCustomEmoji):
            keys.add(f"custom:{reaction.custom_emoji_id}")
        elif isinstance(reaction, ReactionTypePaid):
            keys.add("paid")
    return keys


def _count_total_reactions(reactions: tuple[ReactionCount, ...]) -> int:
    return sum(reaction.total_count for reaction in reactions)


class ReactionHandler(Handler):
    def __init__(self, message_repo: MessageRepo) -> None:
        self._message_repo = message_repo

    async def handle(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message_reaction_count:
            await self._handle_reaction_count(update)
            return
        if update.message_reaction:
            await self._handle_reaction(update)

    async def _handle_reaction_count(self, update: Update) -> None:
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

    async def _handle_reaction(self, update: Update) -> None:
        event = update.message_reaction
        if not event:
            return

        old = reaction_keys(event.old_reaction)
        new = reaction_keys(event.new_reaction)
        delta = len(new - old) - len(old - new)
        updated = await self._message_repo.apply_reaction_delta(
            event.chat.id,
            event.message_id,
            delta,
        )
        if not updated:
            logger.debug(
                "ignoring reaction for untracked message chat_id=%s message_id=%s",
                event.chat.id,
                event.message_id,
            )

    def register(self, app: BotApplication) -> None:
        # MESSAGE_REACTION (default) accepts both message_reaction and
        # message_reaction_count updates.
        app.add_handler(MessageReactionHandler(self.handle))
