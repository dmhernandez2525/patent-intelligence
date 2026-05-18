from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import ssl
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import settings

_LIBPQ_SSL_QUERY_PARAMS = {"sslmode", "sslcert", "sslkey", "sslrootcert"}


def _libpq_sslmode(url: str) -> str | None:
    query = dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))
    sslmode = query.get("sslmode")
    return sslmode.lower() if sslmode else None


def _strip_libpq_ssl_query_params(url: str) -> str:
    parts = urlsplit(url)
    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key.lower() not in _LIBPQ_SSL_QUERY_PARAMS
        ],
        doseq=True,
    )
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


def _normalize_database_url(url: str) -> str:
    if not url:
        raise ValueError("DATABASE_URL is not set")
    if url.startswith("postgresql+asyncpg://"):
        return _strip_libpq_ssl_query_params(url)
    if url.startswith("postgres://"):
        return _strip_libpq_ssl_query_params(
            f"postgresql+asyncpg://{url[len('postgres://') :]}"
        )
    if url.startswith("postgresql://"):
        return _strip_libpq_ssl_query_params(
            f"postgresql+asyncpg://{url[len('postgresql://') :]}"
        )
    return _strip_libpq_ssl_query_params(url)


def _asyncpg_connect_args(url: str) -> dict[str, object]:
    sslmode = _libpq_sslmode(url)
    if sslmode == "disable" or not sslmode:
        return {}
    if sslmode in {"allow", "prefer", "require"}:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return {"ssl": ssl_context}
    return {"ssl": ssl.create_default_context()}


engine = create_async_engine(
    _normalize_database_url(settings.database_url),
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.debug,
    connect_args=_asyncpg_connect_args(settings.database_url),
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
