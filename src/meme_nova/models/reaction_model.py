from datetime import datetime
from typing import ClassVar

from sqlmodel import Field, SQLModel


class ReactionModel(SQLModel, table=True):
    __tablename__: ClassVar[str] = "reactions"  # pyright: ignore[reportIncompatibleVariableOverrid

    id: int | None = Field(default=None, primary_key=True)

    user_id: int
    chat_id: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now())
