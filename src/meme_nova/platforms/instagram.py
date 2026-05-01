import asyncio
import logging
import re
from io import BytesIO
from urllib.request import Request, urlopen

import instaloader
from telegram import InputMediaPhoto, InputMediaVideo, Message

from .base import DOWNLOAD_TIMEOUT_SECONDS, MEDIA_GROUP_LIMIT, Platform, host_matches

logger = logging.getLogger(__name__)

INSTAGRAM_SHORTCODE_RE = re.compile(r"instagram\.com/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)")


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

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        session_file: str | None = None,
    ) -> None:
        self._loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
        )
        if username:
            self._authenticate(username, password, session_file)

    def _authenticate(
        self, username: str, password: str | None, session_file: str | None
    ) -> None:
        if self._try_load_session(username, session_file):
            return
        if not password:
            logger.warning(
                "instagram session file not found for %s and INSTAGRAM_PASSWORD not set; "
                "set INSTAGRAM_PASSWORD or run `instaloader -l %s`. proceeding unauthenticated.",
                username,
                username,
            )
            return
        self._login_and_save(username, password, session_file)

    def _try_load_session(self, username: str, session_file: str | None) -> bool:
        try:
            self._loader.load_session_from_file(username, filename=session_file)
        except FileNotFoundError:
            return False
        except Exception:
            logger.exception("failed to load instagram session for %s", username)
            return False
        logger.info("instagram session loaded for %s", username)
        return True

    def _login_and_save(
        self, username: str, password: str, session_file: str | None
    ) -> None:
        try:
            self._loader.login(username, password)
        except instaloader.TwoFactorAuthRequiredException:
            logger.error(
                "instagram 2FA required for %s; password login cannot handle 2FA. "
                "run `instaloader -l %s` once on this machine to seed the session.",
                username,
                username,
            )
            return
        except instaloader.BadCredentialsException:
            logger.error("instagram login rejected: bad credentials for %s", username)
            return
        except Exception:
            logger.exception(
                "instagram login failed for %s (likely a checkpoint or rate-limit; "
                "check the account in a browser, then retry)",
                username,
            )
            return
        try:
            self._loader.save_session_to_file(filename=session_file)
        except Exception:
            logger.exception("instagram login succeeded but saving session failed for %s", username)
            return
        logger.info("instagram login successful for %s; session saved", username)

    def matches(self, url: str) -> bool:
        return host_matches(url, self.hosts)

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

        try:
            if len(media) == 1:
                await self._reply_single(message, media[0])
            else:
                await self._reply_group(message, media[:MEDIA_GROUP_LIMIT])
        except Exception:
            logger.exception("failed to send instagram media for %s", shortcode)

    async def _reply_single(self, message: Message, item: tuple[str, bool]) -> None:
        url, is_video = item
        data = await asyncio.to_thread(_download_to_memory, url)
        if is_video:
            await message.reply_video(video=BytesIO(data))
        else:
            await message.reply_photo(photo=BytesIO(data))

    async def _reply_group(self, message: Message, items: list[tuple[str, bool]]) -> None:
        media_group: list[InputMediaPhoto | InputMediaVideo] = []
        for url, is_video in items:
            data = await asyncio.to_thread(_download_to_memory, url)
            if is_video:
                media_group.append(InputMediaVideo(media=BytesIO(data)))
            else:
                media_group.append(InputMediaPhoto(media=BytesIO(data)))
        await message.reply_media_group(media=media_group)
