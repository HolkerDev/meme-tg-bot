from meme_nova.handlers.base import Handler
from meme_nova.handlers.group_message_handler import GroupMessageHandler
from meme_nova.handlers.reaction_handler import ReactionHandler
from meme_nova.platforms import build_handlers
from meme_nova.repositories.message_repo import MessageRepo
from meme_nova.settings import Settings
from meme_nova.types import BotApplication


def build_update_handlers(
    *,
    message_repo: MessageRepo,
    settings: Settings,
) -> tuple[Handler, ...]:
    platform_handlers = build_handlers(
        instagram_username=settings.instagram_username,
        instagram_password=settings.instagram_password,
        instagram_session_file=settings.instagram_session_file,
        instagram_cookies_file=settings.instagram_cookies_file,
    )
    return (
        GroupMessageHandler(platform_handlers, message_repo),
        ReactionHandler(message_repo),
    )


def register_update_handlers(
    app: BotApplication,
    handlers: tuple[Handler, ...],
) -> None:
    for handler in handlers:
        handler.register(app)
