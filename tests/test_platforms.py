import pytest

from meme_nova.platforms import (
    Platform,
    _extract_instagram_shortcode,
    build_handlers,
    detect_platform,
    find_handler,
)

HANDLERS = build_handlers()


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.instagram.com/p/abc/", Platform.INSTAGRAM),
        ("https://instagram.com/reel/xyz", Platform.INSTAGRAM),
        ("https://www.instagram.com/reels/DXuotVMDZ-F/", Platform.INSTAGRAM),
        ("https://instagr.am/p/abc", Platform.INSTAGRAM),
        ("https://www.tiktok.com/@user/video/123", Platform.TIKTOK),
        ("https://vm.tiktok.com/abc", Platform.TIKTOK),
        ("https://www.youtube.com/watch?v=abc", Platform.YOUTUBE),
        ("https://youtu.be/abc", Platform.YOUTUBE),
        ("https://m.youtube.com/shorts/abc", Platform.YOUTUBE),
        ("https://x.com/user/status/1", Platform.TWITTER),
        ("https://twitter.com/user/status/1", Platform.TWITTER),
        ("https://t.co/abc", Platform.TWITTER),
        ("https://www.reddit.com/r/x/comments/", Platform.REDDIT),
        ("https://redd.it/abc", Platform.REDDIT),
        ("https://www.facebook.com/p/abc", Platform.FACEBOOK),
        ("https://fb.watch/abc", Platform.FACEBOOK),
        ("https://example.com/foo", Platform.UNKNOWN),
        ("not-a-url", Platform.UNKNOWN),
        ("", Platform.UNKNOWN),
    ],
)
def test_detect_platform(url: str, expected: Platform) -> None:
    assert detect_platform(HANDLERS, url) == expected


def test_find_handler_returns_none_for_unknown() -> None:
    assert find_handler(HANDLERS, "https://example.com") is None


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.instagram.com/p/abc123/", "abc123"),
        ("https://www.instagram.com/reel/DX-uotV/", "DX-uotV"),
        ("https://www.instagram.com/reels/DXuotVMDZ-F/", "DXuotVMDZ-F"),
        ("https://www.instagram.com/tv/Abc_42/", "Abc_42"),
        ("https://www.instagram.com/u/holkeres/", None),
        ("https://example.com/p/abc/", None),
    ],
)
def test_extract_instagram_shortcode(url: str, expected: str | None) -> None:
    assert _extract_instagram_shortcode(url) == expected


async def test_default_handler_process_logs_only() -> None:
    handler = find_handler(HANDLERS, "https://www.youtube.com/watch?v=abc")
    assert handler is not None
    assert handler.platform == Platform.YOUTUBE
    await handler.process("https://www.youtube.com/watch?v=abc", message=None)  # type: ignore[arg-type]
