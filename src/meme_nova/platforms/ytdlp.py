import asyncio
import logging
import tempfile
from io import BytesIO
from pathlib import Path

from telegram import Message
from telegram.constants import ChatAction
from yt_dlp import YoutubeDL
from yt_dlp.utils import match_filter_func

from .base import (
    DEFAULT_MAX_DURATION_SECONDS,
    TELEGRAM_BOT_UPLOAD_LIMIT_BYTES,
    Platform,
    host_matches,
    safe_chat_action,
)

logger = logging.getLogger(__name__)


class YtDlpHandler:
    platform: Platform = Platform.UNKNOWN
    hosts: tuple[str, ...] = ()

    def __init__(
        self,
        max_duration_seconds: int = DEFAULT_MAX_DURATION_SECONDS,
        max_filesize_bytes: int = TELEGRAM_BOT_UPLOAD_LIMIT_BYTES,
    ) -> None:
        self._max_duration = max_duration_seconds
        self._max_filesize = max_filesize_bytes

    def matches(self, url: str) -> bool:
        return host_matches(url, self.hosts)

    async def process(self, url: str, message: Message) -> bool:
        try:
            data = await asyncio.to_thread(self._download, url)
        except Exception:
            logger.exception("yt-dlp download failed for %s", url)
            return False
        if not data:
            return True
        try:
            await safe_chat_action(message, ChatAction.UPLOAD_VIDEO)
            await message.reply_video(video=BytesIO(data))
        except Exception:
            logger.exception("yt-dlp send failed for %s", url)
            return False
        return True

    def _download(self, url: str) -> bytes | None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            opts = {
                "format": "b[height<=720][ext=mp4]/b[ext=mp4]/b",
                "outtmpl": str(tmp / "%(id)s.%(ext)s"),
                "quiet": True,
                "no_warnings": True,
                "noprogress": True,
                "noplaylist": True,
                "max_filesize": self._max_filesize,
                "match_filter": match_filter_func(f"duration <=? {self._max_duration}"),
            }
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
            if info is None:
                return None
            files = [p for p in tmp.iterdir() if p.is_file()]
            if not files:
                return None
            file_path = files[0]
            if file_path.stat().st_size > self._max_filesize:
                return None
            return file_path.read_bytes()
