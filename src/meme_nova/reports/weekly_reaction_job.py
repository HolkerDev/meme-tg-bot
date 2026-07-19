import logging
from datetime import UTC, datetime, timedelta

from telegram import Bot

from meme_nova.reports.weekly_reaction_formatter import (
    WeeklyReactionEntry,
    WeeklyReactionReportFormatter,
)
from meme_nova.repositories.message_repo import MessageRepo

logger = logging.getLogger(__name__)

WEEKLY_REPORT_WINDOW = timedelta(days=7)


async def _resolve_display_name(bot: Bot, chat_id: int, user_id: int) -> str:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        user = member.user
        if user.username:
            return f"@{user.username}"
        if user.full_name:
            return user.full_name
    except Exception:
        logger.warning(
            "failed to resolve display name chat_id=%s user_id=%s",
            chat_id,
            user_id,
            exc_info=True,
        )
    return str(user_id)


async def publish_weekly_reaction_reports(bot: Bot, message_repo: MessageRepo) -> None:
    since = datetime.now(tz=UTC) - WEEKLY_REPORT_WINDOW
    formatter = WeeklyReactionReportFormatter()

    for chat_id in await message_repo.distinct_chat_ids():
        counts = await message_repo.weekly_reaction_counts(chat_id, since)
        counts = {user_id: count for user_id, count in counts.items() if count > 0}
        if not counts:
            continue

        entries = [
            WeeklyReactionEntry(
                display_name=await _resolve_display_name(bot, chat_id, user_id),
                reaction_count=count,
            )
            for user_id, count in counts.items()
        ]
        text = formatter.format(entries)
        await bot.send_message(chat_id=chat_id, text=text)
        logger.info("posted weekly reaction report chat_id=%s users=%s", chat_id, len(entries))
