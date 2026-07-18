from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import SQLModel

from meme_nova.db import create_db_engine
from meme_nova.models import MessageModel  # noqa: F401
from meme_nova.repositories.message_repo import MessageRepo


@pytest.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    db_engine = create_db_engine(str(tmp_path / "test.db"))
    async with db_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield db_engine
    await db_engine.dispose()


@pytest.fixture
def message_repo(engine: AsyncEngine) -> MessageRepo:
    return MessageRepo(engine)
