from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

from meme_nova.constants import MAIN_CHAT_ID, SUPER_LIKE_CALLBACK
from meme_nova.platforms._media import send_media_bytes


async def test_video_button_is_only_in_main_chat() -> None:
    for chat_id in (MAIN_CHAT_ID, 100):
        message = SimpleNamespace(
            chat=SimpleNamespace(id=chat_id),
            reply_chat_action=AsyncMock(),
            reply_video=AsyncMock(return_value=SimpleNamespace(message_id=42)),
        )

        await send_media_bytes(cast(Any, message), [(b"video", True)])

        markup = message.reply_video.await_args.kwargs["reply_markup"]
        if chat_id == MAIN_CHAT_ID:
            assert markup.inline_keyboard[0][0].callback_data == SUPER_LIKE_CALLBACK
            assert markup.inline_keyboard[0][0].text == "Потужний лайк · 0"
        else:
            assert markup is None


async def test_photo_button_is_only_in_main_chat() -> None:
    for chat_id in (MAIN_CHAT_ID, 100):
        message = SimpleNamespace(
            chat=SimpleNamespace(id=chat_id),
            reply_chat_action=AsyncMock(),
            reply_photo=AsyncMock(return_value=SimpleNamespace(message_id=42)),
        )

        assert await send_media_bytes(cast(Any, message), [(b"photo", False)]) == (42,)

        markup = message.reply_photo.await_args.kwargs["reply_markup"]
        if chat_id == MAIN_CHAT_ID:
            assert markup.inline_keyboard[0][0].callback_data == SUPER_LIKE_CALLBACK
        else:
            assert markup is None


async def test_album_gets_one_button_message_in_main_chat() -> None:
    for chat_id in (MAIN_CHAT_ID, 100):
        album = [
            SimpleNamespace(message_id=42, reply_text=AsyncMock()),
            SimpleNamespace(
                message_id=43,
                reply_text=AsyncMock(return_value=SimpleNamespace(message_id=44)),
            ),
        ]
        message = SimpleNamespace(
            chat=SimpleNamespace(id=chat_id),
            reply_chat_action=AsyncMock(),
            reply_media_group=AsyncMock(return_value=album),
        )

        ids = await send_media_bytes(cast(Any, message), [(b"photo", False)] * 2)

        if chat_id == MAIN_CHAT_ID:
            assert ids == (42, 43, 44)
            album[-1].reply_text.assert_awaited_once()
            markup = album[-1].reply_text.await_args.kwargs["reply_markup"]
            assert markup.inline_keyboard[0][0].callback_data == SUPER_LIKE_CALLBACK
        else:
            assert ids == (42, 43)
            album[-1].reply_text.assert_not_awaited()
        album[0].reply_text.assert_not_awaited()
