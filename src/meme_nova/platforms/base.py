from enum import StrEnum
from typing import Protocol
from urllib.parse import urlparse

from telegram import Message

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


class PlatformHandler(Protocol):
    @property
    def platform(self) -> Platform: ...

    def matches(self, url: str) -> bool: ...

    async def process(self, url: str, message: Message) -> None: ...


def host_matches(url: str, hosts: tuple[str, ...]) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    return any(host == h or host.endswith("." + h) for h in hosts)
