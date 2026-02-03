"""Unit tests for database connection URL normalization."""

import pytest

from src.database.connection import _normalize_database_url


class TestNormalizeDatabaseUrl:
    """Tests for _normalize_database_url function."""

    def test_empty_url_raises_value_error(self) -> None:
        """Empty URL should raise ValueError with clear message."""
        with pytest.raises(ValueError, match="DATABASE_URL is not set"):
            _normalize_database_url("")

    def test_none_url_raises_value_error(self) -> None:
        """None URL should raise ValueError with clear message."""
        with pytest.raises(ValueError, match="DATABASE_URL is not set"):
            _normalize_database_url(None)  # type: ignore[arg-type]

    def test_postgres_url_converted(self) -> None:
        """postgres:// URLs should be converted to postgresql+asyncpg://."""
        url = "postgres://user:pass@host:5432/db"
        result = _normalize_database_url(url)
        assert result == "postgresql+asyncpg://user:pass@host:5432/db"

    def test_postgresql_url_converted(self) -> None:
        """postgresql:// URLs should be converted to postgresql+asyncpg://."""
        url = "postgresql://user:pass@host:5432/db"
        result = _normalize_database_url(url)
        assert result == "postgresql+asyncpg://user:pass@host:5432/db"

    def test_asyncpg_url_unchanged(self) -> None:
        """postgresql+asyncpg:// URLs should be returned unchanged."""
        url = "postgresql+asyncpg://user:pass@host:5432/db"
        result = _normalize_database_url(url)
        assert result == url

    def test_other_url_unchanged(self) -> None:
        """Other URL schemes should be returned unchanged."""
        url = "sqlite:///test.db"
        result = _normalize_database_url(url)
        assert result == url
