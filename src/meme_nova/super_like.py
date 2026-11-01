from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from meme_nova.constants import SUPER_LIKE_CALLBACK


def super_like_markup(count: int) -> InlineKeyboardMarkup:
    button = InlineKeyboardButton(
        f"Потужний лайк · {count}", callback_data=SUPER_LIKE_CALLBACK
    )
    return InlineKeyboardMarkup([[button]])
