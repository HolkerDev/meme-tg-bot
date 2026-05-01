import pytest

from meme_nova.settings import Settings


def test_load_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setattr("meme_nova.settings.load_dotenv", lambda: None)
    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
        Settings.load()


def test_load_uses_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "abc")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.delenv("INSTAGRAM_USERNAME", raising=False)
    monkeypatch.delenv("INSTAGRAM_PASSWORD", raising=False)
    monkeypatch.delenv("INSTAGRAM_SESSION_FILE", raising=False)
    monkeypatch.setattr("meme_nova.settings.load_dotenv", lambda: None)
    s = Settings.load()
    assert s.telegram_bot_token == "abc"
    assert s.log_level == "DEBUG"
    assert s.instagram_username is None
    assert s.instagram_password is None
    assert s.instagram_session_file is None


def test_load_reads_instagram_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "abc")
    monkeypatch.setenv("INSTAGRAM_USERNAME", "memebot")
    monkeypatch.setenv("INSTAGRAM_PASSWORD", "hunter2")
    monkeypatch.setenv("INSTAGRAM_SESSION_FILE", "/tmp/session-memebot")
    monkeypatch.setattr("meme_nova.settings.load_dotenv", lambda: None)
    s = Settings.load()
    assert s.instagram_username == "memebot"
    assert s.instagram_password == "hunter2"
    assert s.instagram_session_file == "/tmp/session-memebot"
