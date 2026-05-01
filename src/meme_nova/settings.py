import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    log_level: str
    instagram_username: str | None
    instagram_password: str | None
    instagram_session_file: str | None
    retry_db_path: str

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv()
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN missing. Copy .env.example to .env.")
        return cls(
            telegram_bot_token=token,
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
            instagram_username=os.environ.get("INSTAGRAM_USERNAME") or None,
            instagram_password=os.environ.get("INSTAGRAM_PASSWORD") or None,
            instagram_session_file=os.environ.get("INSTAGRAM_SESSION_FILE") or None,
            retry_db_path=os.environ.get("RETRY_DB_PATH", "meme_nova_retry.db"),
        )
