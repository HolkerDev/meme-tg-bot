from .base import Platform
from .ytdlp import YtDlpHandler


class TwitterHandler(YtDlpHandler):
    platform = Platform.TWITTER
    hosts = ("twitter.com", "x.com", "t.co")
