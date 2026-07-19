import logging

from telegram import Update
from telegram.ext import ApplicationBuilder

from meme_nova.db import create_db_engine
from meme_nova.handlers.registry import build_update_handlers, register_update_handlers
from meme_nova.repositories.message_repo import MessageRepo
from meme_nova.scheduler import start_scheduler
from meme_nova.settings import Settings
from meme_nova.types import BotApplication

logger = logging.getLogger(__name__)


def build_app(settings: Settings) -> BotApplication:
    engine = create_db_engine(settings.db_path)
    message_repo = MessageRepo(engine=engine)

    async def post_init(_application: BotApplication) -> None:
        start_scheduler(app, message_repo)

    app = (
        ApplicationBuilder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .build()
    )
    update_handlers = build_update_handlers(
        message_repo=message_repo,
        settings=settings,
    )
    register_update_handlers(app, update_handlers)
    return app


def main() -> None:
    settings = Settings.load()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    app = build_app(settings)
    logger.info("Starting bot polling")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
