from abc import ABC, abstractmethod

from meme_nova.types import BotApplication


class Handler(ABC):
    @abstractmethod
    def register(self, app: BotApplication) -> None:
        """Register this handler with the Telegram application."""
