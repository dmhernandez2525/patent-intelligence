from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import settings


def _normalize_database_url(url: str) -> str:
    if not url:
        raise ValueError("DATABASE_URL is not set")
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgres://"):
        return f"postgresql+asyncpg://{url[len('postgres://') :]}"
    if url.startswith("postgresql://"):
        return f"postgresql+asyncpg://{url[len('postgresql://') :]}"
    return url


engine = create_async_engine(
    _normalize_database_url(settings.database_url),
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.debug,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with get_db_session() as session:
        yield session
