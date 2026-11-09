from pathlib import Path

from .base import Platform
from .ytdlp import YtDlpHandler


class YouTubeHandler(YtDlpHandler):
    platform = Platform.YOUTUBE
    hosts = ("youtube.com", "youtu.be")

    def _ydl_opts(self, tmp: Path) -> dict[str, object]:
        opts = super()._ydl_opts(tmp)
        opts["format"] = (
            "bv[height<=720][ext=mp4][vcodec^=avc1]+ba[ext=m4a]/"
            "bv[height<=720][ext=mp4]+ba[ext=m4a]/"
            "bv[height<=720]+ba/"
            "b[height<=720][ext=mp4]/b[ext=mp4]/b"
        )
        opts["merge_output_format"] = "mp4"
        return opts
