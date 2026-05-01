from .base import Platform
from .ytdlp import YtDlpHandler


class YouTubeHandler(YtDlpHandler):
    platform = Platform.YOUTUBE
    hosts = ("youtube.com", "youtu.be")
