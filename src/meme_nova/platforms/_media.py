from io import BytesIO

from telegram import InputMediaPhoto, InputMediaVideo, Message
from telegram.constants import ChatAction

from .base import MEDIA_GROUP_LIMIT, safe_chat_action


async def send_media_bytes(message: Message, items: list[tuple[bytes, bool]]) -> tuple[int, ...]:
    if not items:
        return ()
    if len(items) == 1:
        data, is_video = items[0]
        action = ChatAction.UPLOAD_VIDEO if is_video else ChatAction.UPLOAD_PHOTO
        await safe_chat_action(message, action)
        if is_video:
            single = await message.reply_video(video=BytesIO(data))
        else:
            single = await message.reply_photo(photo=BytesIO(data))
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
    return tuple(msg.message_id for msg in sent)
