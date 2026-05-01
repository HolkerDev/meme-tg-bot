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
    monkeypatch.setattr("meme_nova.settings.load_dotenv", lambda: None)
    s = Settings.load()
    assert s.telegram_bot_token == "abc"
    assert s.log_level == "DEBUG"
