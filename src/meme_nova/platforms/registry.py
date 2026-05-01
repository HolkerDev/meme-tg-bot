from . import facebook, reddit
from .base import Platform, PlatformHandler
from .instagram import InstagramHandler
from .tiktok import TikTokHandler
from .twitter import TwitterHandler
from .youtube import YouTubeHandler


def build_handlers(
    instagram_username: str | None = None,
    instagram_password: str | None = None,
    instagram_session_file: str | None = None,
) -> tuple[PlatformHandler, ...]:
    return (
        InstagramHandler(
            username=instagram_username,
            password=instagram_password,
            session_file=instagram_session_file,
        ),
        TikTokHandler(),
        YouTubeHandler(),
        TwitterHandler(),
        reddit.handler,
        facebook.handler,
    )


def find_handler(handlers: tuple[PlatformHandler, ...], url: str) -> PlatformHandler | None:
    for handler in handlers:
        if handler.matches(url):
            return handler
    return None


def detect_platform(handlers: tuple[PlatformHandler, ...], url: str) -> Platform:
    handler = find_handler(handlers, url)
    return handler.platform if handler else Platform.UNKNOWN
