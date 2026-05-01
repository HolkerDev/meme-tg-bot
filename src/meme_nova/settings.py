import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    log_level: str

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv()
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN missing. Copy .env.example to .env.")
        return cls(
            telegram_bot_token=token,
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )
