from .base import Platform
from .ytdlp import YtDlpHandler


class TikTokHandler(YtDlpHandler):
    platform = Platform.TIKTOK
    hosts = ("tiktok.com",)
