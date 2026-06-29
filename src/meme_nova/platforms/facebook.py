from .base import Platform
from .ytdlp import YtDlpHandler


class FacebookHandler(YtDlpHandler):
    platform = Platform.FACEBOOK
    hosts = ("facebook.com", "fb.com", "fb.watch")
