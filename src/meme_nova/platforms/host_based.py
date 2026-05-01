import logging
from dataclasses import dataclass

from telegram import Message

from .base import Platform, host_matches

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HostBasedHandler:
    platform: Platform
    hosts: tuple[str, ...]

    def matches(self, url: str) -> bool:
        return host_matches(url, self.hosts)

    async def process(self, url: str, message: Message) -> None:
        logger.info("platform=%s url=%s (no handler implementation)", self.platform.value, url)
