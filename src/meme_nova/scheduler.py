import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from meme_nova.reports.weekly_reaction_job import publish_weekly_reaction_reports
from meme_nova.repositories.message_repo import MessageRepo
from meme_nova.types import BotApplication

logger = logging.getLogger(__name__)


def start_scheduler(app: BotApplication, message_repo: MessageRepo) -> AsyncIOScheduler:
    async def friday_job() -> None:
        await publish_weekly_reaction_reports(app.bot, message_repo)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        friday_job,
        CronTrigger(day_of_week="fri", hour=18, minute=0),
        id="friday_job",
    )
    scheduler.start()
    logger.info("Scheduler started (friday_job at 18:00 every Friday)")
    return scheduler
