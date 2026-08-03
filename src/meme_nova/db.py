from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def create_db_engine(db_path: str) -> AsyncEngine:
    return create_async_engine(f"sqlite+aiosqlite:///{db_path}")
