import subprocess
from pathlib import Path

from pytest import MonkeyPatch

from meme_nova.platforms import gallery_dl


def test_gallery_images_follow_numeric_filename_order(monkeypatch: MonkeyPatch) -> None:
    def fake_run(
        cmd: list[str], *, check: bool, capture_output: bool, timeout: int
    ) -> subprocess.CompletedProcess[bytes]:
        destination = Path(cmd[cmd.index("--dest") + 1])
        assert cmd[cmd.index("--filename") + 1] == "{num}_{media_id}.{extension}"
        for number, media_id in ((10, 500), (2, 900), (1, 700), (11, 100), (3, 800)):
            (destination / f"{number}_{media_id}.jpg").write_bytes(str(number).encode())
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert gallery_dl.download_media("https://www.instagram.com/p/example/") == [
        (str(number).encode(), False) for number in (1, 2, 3, 10, 11)
    ]
