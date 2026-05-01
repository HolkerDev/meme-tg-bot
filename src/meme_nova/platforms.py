import asyncio
import logging
import re
from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO
from typing import Protocol
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import instaloader
from telegram import InputMediaPhoto, InputMediaVideo, Message

logger = logging.getLogger(__name__)

DOWNLOAD_TIMEOUT_SECONDS = 30
TELEGRAM_CAPTION_LIMIT = 1024
MEDIA_GROUP_LIMIT = 10
INSTAGRAM_SHORTCODE_RE = re.compile(r"instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)")


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


def _host_matches(url: str, hosts: tuple[str, ...]) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    return any(host == h or host.endswith("." + h) for h in hosts)


@dataclass(frozen=True)
class HostBasedHandler:
    platform: Platform
    hosts: tuple[str, ...]

    def matches(self, url: str) -> bool:
        return _host_matches(url, self.hosts)

    async def process(self, url: str, message: Message) -> None:
        logger.info("platform=%s url=%s (no handler implementation)", self.platform.value, url)


def _extract_instagram_shortcode(url: str) -> str | None:
    match = INSTAGRAM_SHORTCODE_RE.search(url)
    return match.group(1) if match else None


def _download_to_memory(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        return bytes(response.read())


def _collect_post_media(post: instaloader.Post) -> list[tuple[str, bool]]:
    media: list[tuple[str, bool]] = []
    if post.typename == "GraphSidecar":
        for node in post.get_sidecar_nodes():
            url = node.video_url if node.is_video else node.display_url
            if url:
                media.append((url, bool(node.is_video)))
        return media
    if post.is_video and post.video_url:
        return [(post.video_url, True)]
    if post.url:
        return [(post.url, False)]
    return media


class InstagramHandler:
    platform = Platform.INSTAGRAM
    hosts = ("instagram.com", "instagr.am")

    def __init__(self, username: str | None = None, session_file: str | None = None) -> None:
        self._loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
        )
        if username:
            self._load_session(username, session_file)

    def _load_session(self, username: str, session_file: str | None) -> None:
        try:
            self._loader.load_session_from_file(username, filename=session_file)
        except FileNotFoundError:
            logger.warning(
                "instagram session file not found for %s; "
                "run `instaloader -l %s` to create it. proceeding unauthenticated.",
                username,
                username,
            )
            return
        except Exception:
            logger.exception("failed to load instagram session for %s", username)
            return
        logger.info("instagram session loaded for %s", username)

    def matches(self, url: str) -> bool:
        return _host_matches(url, self.hosts)

    async def process(self, url: str, message: Message) -> None:
        shortcode = _extract_instagram_shortcode(url)
        if not shortcode:
            logger.info("instagram link is not a post: %s", url)
            return
        try:
            post = await asyncio.to_thread(
                instaloader.Post.from_shortcode, self._loader.context, shortcode
            )
        except Exception:
            logger.exception("failed to fetch instagram post %s", shortcode)
            return

        media = _collect_post_media(post)
        if not media:
            logger.info("instagram post %s has no media", shortcode)
            return

        caption = (post.caption or "")[:TELEGRAM_CAPTION_LIMIT] or None
        try:
            if len(media) == 1:
                await self._reply_single(message, media[0], caption)
            else:
                await self._reply_group(message, media[:MEDIA_GROUP_LIMIT], caption)
        except Exception:
            logger.exception("failed to send instagram media for %s", shortcode)

    async def _reply_single(
        self, message: Message, item: tuple[str, bool], caption: str | None
    ) -> None:
        url, is_video = item
        data = await asyncio.to_thread(_download_to_memory, url)
        if is_video:
            await message.reply_video(video=BytesIO(data), caption=caption)
        else:
            await message.reply_photo(photo=BytesIO(data), caption=caption)

    async def _reply_group(
        self,
        message: Message,
        items: list[tuple[str, bool]],
        caption: str | None,
    ) -> None:
        media_group: list[InputMediaPhoto | InputMediaVideo] = []
        for index, (url, is_video) in enumerate(items):
            data = await asyncio.to_thread(_download_to_memory, url)
            entry_caption = caption if index == 0 else None
            if is_video:
                media_group.append(InputMediaVideo(media=BytesIO(data), caption=entry_caption))
            else:
                media_group.append(InputMediaPhoto(media=BytesIO(data), caption=entry_caption))
        await message.reply_media_group(media=media_group)


def build_handlers(
    instagram_username: str | None = None,
    instagram_session_file: str | None = None,
) -> tuple[PlatformHandler, ...]:
    return (
        InstagramHandler(username=instagram_username, session_file=instagram_session_file),
        HostBasedHandler(Platform.TIKTOK, ("tiktok.com",)),
        HostBasedHandler(Platform.YOUTUBE, ("youtube.com", "youtu.be")),
        HostBasedHandler(Platform.TWITTER, ("twitter.com", "x.com", "t.co")),
        HostBasedHandler(Platform.REDDIT, ("reddit.com", "redd.it")),
        HostBasedHandler(Platform.FACEBOOK, ("facebook.com", "fb.com", "fb.watch")),
    )


def find_handler(handlers: tuple[PlatformHandler, ...], url: str) -> PlatformHandler | None:
    for handler in handlers:
        if handler.matches(url):
            return handler
    return None


def detect_platform(handlers: tuple[PlatformHandler, ...], url: str) -> Platform:
    handler = find_handler(handlers, url)
    return handler.platform if handler else Platform.UNKNOWN
