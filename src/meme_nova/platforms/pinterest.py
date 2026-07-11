from .base import Platform
from .ytdlp import YtDlpHandler


class PinterestHandler(YtDlpHandler):
    platform = Platform.PINTEREST
    hosts = ("pinterest.com", "pin.it")
