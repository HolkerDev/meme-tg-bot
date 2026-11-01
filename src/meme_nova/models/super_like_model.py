from datetime import UTC, date, datetime
from typing import ClassVar

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class SuperLikeModel(SQLModel, table=True):
    __tablename__: ClassVar[str] = "super_likes"  # pyright: ignore[reportIncompatibleVariableOverride]
    __table_args__ = (UniqueConstraint("voter_user_id", "vote_day"),)

    id: int | None = Field(default=None, primary_key=True)
    chat_id: int
    message_id: int
    voter_user_id: int
    vote_day: date
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
