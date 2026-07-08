import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from urllib.parse import urlparse

from telegram import Message

logger = logging.getLogger(__name__)

TELEGRAM_BOT_UPLOAD_LIMIT_BYTES = 50 * 1024 * 1024
DEFAULT_MAX_DURATION_SECONDS = 600
DOWNLOAD_TIMEOUT_SECONDS = 30
MEDIA_GROUP_LIMIT = 10


class Platform(StrEnum):
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    REDDIT = "reddit"
    FACEBOOK = "facebook"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProcessResult:
    ok: bool
    bot_message_ids: tuple[int, ...] = ()

    @classmethod
    def success(cls, *message_ids: int) -> "ProcessResult":
        return cls(ok=True, bot_message_ids=message_ids)

    @classmethod
    def skipped(cls) -> "ProcessResult":
        return cls(ok=True)

    @classmethod
    def failure(cls) -> "ProcessResult":
        return cls(ok=False)


class PlatformHandler(Protocol):
    @property
    def platform(self) -> Platform: ...

    def matches(self, url: str) -> bool: ...

    async def process(self, url: str, message: Message) -> ProcessResult:
        """ok=True handled/skipped; ok=False transient failure (retry)."""
        ...


async def safe_chat_action(message: Message, action: str) -> None:
    try:
        await message.reply_chat_action(action)
    except Exception:
        logger.debug("chat action failed", exc_info=True)


def host_matches(url: str, hosts: tuple[str, ...]) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    return any(host == h or host.endswith("." + h) for h in hosts)
