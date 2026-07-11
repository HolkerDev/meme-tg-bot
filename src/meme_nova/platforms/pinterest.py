import asyncio
import logging

from telegram import Message

from . import gallery_dl
from ._media import send_media_bytes
from .base import (
    ProcessResult,
    TELEGRAM_BOT_UPLOAD_LIMIT_BYTES,
    Platform,
    host_matches,
)

logger = logging.getLogger(__name__)


class PinterestHandler:
    platform = Platform.PINTEREST
    hosts = ("pinterest.com", "pin.it")

    def __init__(
        self,
        max_filesize_bytes: int = TELEGRAM_BOT_UPLOAD_LIMIT_BYTES,
    ) -> None:
        self._max_filesize = max_filesize_bytes

    def matches(self, url: str) -> bool:
        return host_matches(url, self.hosts)

    async def process(self, url: str, message: Message) -> ProcessResult:
        items = await asyncio.to_thread(
            gallery_dl.download_media, url, self._max_filesize
        )
        if not items:
            logger.info("gallery-dl found no media url=%s", url)
            return ProcessResult.skipped()
        try:
            bot_message_ids = await send_media_bytes(message, items)
        except Exception:
            logger.exception("gallery-dl send failed url=%s", url)
            return ProcessResult.failure()
        return ProcessResult.success(*bot_message_ids)
