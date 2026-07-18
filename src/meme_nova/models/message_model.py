from datetime import datetime
from typing import ClassVar

from sqlmodel import Field, SQLModel


class MessageModel(SQLModel, table=True):
    __tablename__: ClassVar[str] = "messages"  # pyright: ignore[reportIncompatibleVariableOverride]

    chat_id: int = Field(primary_key=True)
    message_id: int = Field(primary_key=True)

    user_id: int = Field(index=True)
    reaction_count: int = Field(default=0)
    posted_at: datetime = Field(default_factory=lambda: datetime.now())
