from datetime import UTC, datetime
from typing import ClassVar

from sqlmodel import Field, SQLModel


class MessageModel(SQLModel, table=True):
    __tablename__: ClassVar[str] = "messages"  # pyright: ignore[reportIncompatibleVariableOverride]

    chat_id: int = Field(primary_key=True)
    message_id: int = Field(primary_key=True)

    user_id: int = Field(index=True)
    username: str | None = Field(default=None)
    display_name: str | None = Field(default=None)
    reaction_count: int = Field(default=0)
    posted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
