import logging
import subprocess
import sys
import tempfile
from pathlib import Path

from .base import TELEGRAM_BOT_UPLOAD_LIMIT_BYTES

logger = logging.getLogger(__name__)

VIDEO_EXTS = frozenset({".mp4", ".mov", ".webm", ".mkv", ".avi"})
SKIP_EXTS = frozenset({".json", ".txt"})
GALLERY_DL_TIMEOUT_SECONDS = 60


def download_media(
    url: str, max_filesize: int = TELEGRAM_BOT_UPLOAD_LIMIT_BYTES
) -> list[tuple[bytes, bool]]:
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "gallery_dl", "--quiet", "--dest", tmpdir, url],
                check=False,
                capture_output=True,
                timeout=GALLERY_DL_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            logger.warning("gallery-dl timeout url=%s", url)
            return []
        except Exception:
            logger.exception("gallery-dl invocation failed url=%s", url)
            return []
        if result.returncode != 0:
            logger.info(
                "gallery-dl rc=%s url=%s stderr=%s",
                result.returncode,
                url,
                result.stderr.decode(errors="replace")[:500],
            )
        media: list[tuple[bytes, bool]] = []
        for path in sorted(Path(tmpdir).rglob("*")):
            if not path.is_file() or path.suffix.lower() in SKIP_EXTS:
                continue
            if path.stat().st_size > max_filesize:
                logger.info("gallery-dl file too large, skipping: %s", path.name)
                continue
            is_video = path.suffix.lower() in VIDEO_EXTS
            media.append((path.read_bytes(), is_video))
        return media
