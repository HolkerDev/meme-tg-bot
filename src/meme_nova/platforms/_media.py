import logging
from io import BytesIO

from telegram import (
    InputMediaPhoto,
    InputMediaVideo,
    Message,
)
from telegram.constants import ChatAction

from meme_nova.constants import MAIN_CHAT_ID
from meme_nova.super_like import super_like_markup

from .base import MEDIA_GROUP_LIMIT, safe_chat_action

logger = logging.getLogger(__name__)


async def send_media_bytes(message: Message, items: list[tuple[bytes, bool]]) -> tuple[int, ...]:
    if not items:
        return ()
    if len(items) == 1:
        data, is_video = items[0]
        action = ChatAction.UPLOAD_VIDEO if is_video else ChatAction.UPLOAD_PHOTO
        await safe_chat_action(message, action)
        markup = super_like_markup(0) if message.chat.id == MAIN_CHAT_ID else None
        if is_video:
            single = await message.reply_video(video=BytesIO(data), reply_markup=markup)
        else:
            single = await message.reply_photo(photo=BytesIO(data), reply_markup=markup)
        return (single.message_id,)
    items = items[:MEDIA_GROUP_LIMIT]
    media_group: list[InputMediaPhoto | InputMediaVideo] = []
    for data, is_video in items:
        if is_video:
            media_group.append(InputMediaVideo(media=BytesIO(data)))
        else:
            media_group.append(InputMediaPhoto(media=BytesIO(data)))
    has_video = any(is_video for _, is_video in items)
    action = ChatAction.UPLOAD_VIDEO if has_video else ChatAction.UPLOAD_PHOTO
    await safe_chat_action(message, action)
    sent = await message.reply_media_group(media=media_group)
    message_ids = tuple(msg.message_id for msg in sent)
    if message.chat.id == MAIN_CHAT_ID:
        try:
            button_message = await sent[-1].reply_text(
                "Потужний лайк для галереї", reply_markup=super_like_markup(0)
            )
        except Exception:
            logger.exception("failed to send album super like button")
        else:
            message_ids += (button_message.message_id,)
    return message_ids
