import asyncio
import logging
import re
import tempfile
from pathlib import Path

from telegram import Message
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from . import gallery_dl
from ._media import send_media_bytes
from .base import (
    DEFAULT_MAX_DURATION_SECONDS,
    TELEGRAM_BOT_UPLOAD_LIMIT_BYTES,
    Platform,
    host_matches,
)

logger = logging.getLogger(__name__)

INSTAGRAM_SHORTCODE_RE = re.compile(r"instagram\.com/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)")


def _extract_instagram_shortcode(url: str) -> str | None:
    match = INSTAGRAM_SHORTCODE_RE.search(url)
    return match.group(1) if match else None


class InstagramHandler:
    platform = Platform.INSTAGRAM
    hosts = ("instagram.com", "instagr.am")

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        session_file: str | None = None,
        cookies_file: str | None = None,
    ) -> None:
        self._username = username
        self._password = password
        self._cookies_file = cookies_file
        self._max_duration = DEFAULT_MAX_DURATION_SECONDS
        self._max_filesize = TELEGRAM_BOT_UPLOAD_LIMIT_BYTES

    def matches(self, url: str) -> bool:
        return host_matches(url, self.hosts)

    async def process(self, url: str, message: Message) -> bool:
        shortcode = _extract_instagram_shortcode(url)
        if not shortcode:
            logger.info("instagram link is not a post: %s", url)
            return True

        try:
            items = await asyncio.to_thread(self._download, url)
        except DownloadError:
            logger.exception("yt-dlp failed for instagram %s, trying gallery-dl", shortcode)
            return await self._fallback_gallery_dl(url, message)
        except Exception:
            logger.exception("failed to fetch instagram post %s", shortcode)
            return False

        if items is None:
            return await self._fallback_gallery_dl(url, message)

        if not items:
            logger.info("instagram post %s has no media", shortcode)
            return True

        try:
            await send_media_bytes(message, items)
        except Exception:
            logger.exception("failed to send instagram media for %s", shortcode)
            return False
        return True

    async def _fallback_gallery_dl(self, url: str, message: Message) -> bool:
        logger.info("trying gallery-dl for instagram url=%s", url)
        items = await asyncio.to_thread(
            gallery_dl.download_media, url, self._max_filesize, self._cookies_file
        )
        if not items:
            logger.info("gallery-dl found no media url=%s", url)
            return True
        try:
            await send_media_bytes(message, items)
        except Exception:
            logger.exception("gallery-dl send failed url=%s", url)
            return False
        return True

    def _build_ydl_opts(self, tmpdir: str) -> dict[str, object]:
        opts: dict[str, object] = {
            "format": "b[height<=720][ext=mp4]/b[ext=mp4]/b",
            "outtmpl": str(Path(tmpdir) / "%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "noplaylist": True,
            "max_filesize": self._max_filesize,
        }
        if self._cookies_file:
            opts["cookiefile"] = self._cookies_file
        elif self._username and self._password:
            opts["username"] = self._username
            opts["password"] = self._password
        return opts

    def _download(self, url: str) -> list[tuple[bytes, bool]] | None:
        with tempfile.TemporaryDirectory() as tmpdir:
            opts = self._build_ydl_opts(tmpdir)
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
            if info is None:
                return None
            files = sorted(Path(tmpdir).iterdir())
            items: list[tuple[bytes, bool]] = []
            for f in files:
                if not f.is_file():
                    continue
                if f.stat().st_size > self._max_filesize:
                    continue
                ext = f.suffix.lower()
                is_video = ext in {".mp4", ".mov", ".webm", ".mkv"}
                items.append((f.read_bytes(), is_video))
            return items
