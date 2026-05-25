import asyncio
import ssl
from logging.config import fileConfig
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.config import settings
from src.models import (
    alert_channel,
    analytics,
    api_platform,
    collaboration_content,
    collaboration_watchlist,
    competitive,
    enterprise,
    ingestion,
    insight,
    landscape,
    organization,
    patent,
    report,
    research_project,
    user,
    watchlist,
)
from src.models.base import Base

_MODEL_MODULES = (
    alert_channel,
    analytics,
    api_platform,
    collaboration_content,
    collaboration_watchlist,
    competitive,
    enterprise,
    ingestion,
    insight,
    landscape,
    organization,
    patent,
    report,
    research_project,
    user,
    watchlist,
)

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


config = context.config
config.set_main_option("sqlalchemy.url", _normalize_database_url(settings.database_url))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=_asyncpg_connect_args(settings.database_url),
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
