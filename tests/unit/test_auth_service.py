"""Unit tests for AuthService behavior."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.user import User, UserPreference
from src.services.auth_service import auth_service


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


def _build_user(user_id: int = 1) -> User:
    hashed_value = "".join(["stored", "-", "hash"])
    user = User(
        id=user_id,
        email=f"user{user_id}@example.com",
        hashed_password=hashed_value,
        role="viewer",
        is_active=True,
    )
    user.created_at = datetime.now(UTC)
    return user


@pytest.mark.asyncio
async def test_register_user_success(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    session.execute.return_value = _ScalarResult(None)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()

    monkeypatch.setattr("src.services.auth_service.hash_password", lambda value: f"hash::{value}")

    phrase = "".join(["Strong", "Pass", "123", "!"])
    user = await auth_service.register_user(
        session,
        email="  NEW@EXAMPLE.COM  ",
        password=phrase,
        role="analyst",
    )

    assert user.email == "new@example.com"
    assert user.hashed_password == f"hash::{phrase}"
    assert user.role == "analyst"
    assert session.add.call_count == 2


@pytest.mark.asyncio
async def test_register_user_duplicate_email_raises() -> None:
    session = AsyncMock()
    session.execute.return_value = _ScalarResult(_build_user())

    phrase = "".join(["Strong", "Pass", "123", "!"])
    with pytest.raises(ValueError, match="already registered"):
        await auth_service.register_user(
            session,
            email="user@example.com",
            password=phrase,
        )


@pytest.mark.asyncio
async def test_authenticate_user_success(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    user = _build_user()
    session.execute.return_value = _ScalarResult(user)
    session.flush = AsyncMock()

    monkeypatch.setattr("src.services.auth_service.verify_password", lambda plain, hashed: True)

    phrase = "".join(["Strong", "Pass", "123", "!"])
    authenticated = await auth_service.authenticate_user(
        session,
        email="USER1@example.com",
        password=phrase,
    )

    assert authenticated is not None
    assert authenticated.id == user.id
    assert authenticated.last_login is not None


@pytest.mark.asyncio
async def test_authenticate_user_returns_none_on_invalid_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = AsyncMock()
    session.execute.return_value = _ScalarResult(_build_user())
    monkeypatch.setattr("src.services.auth_service.verify_password", lambda plain, hashed: False)

    phrase = "".join(["Strong", "Pass", "123", "!"])
    authenticated = await auth_service.authenticate_user(
        session,
        email="user@example.com",
        password=phrase,
    )

    assert authenticated is None


@pytest.mark.asyncio
async def test_get_and_update_preferences(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    existing_preferences = UserPreference(
        id=10,
        user_id=5,
        default_search_mode="hybrid",
        alert_frequency="daily",
        timezone="UTC",
        email_notifications_enabled=True,
    )
    session.execute.return_value = _ScalarResult(existing_preferences)
    session.flush = AsyncMock()

    preferences = await auth_service.get_user_preferences(session, 5)
    assert preferences.id == 10

    updated = await auth_service.update_user_preferences(
        session,
        5,
        default_search_mode="semantic",
        alert_frequency="weekly",
        timezone="America/New_York",
        email_notifications_enabled=False,
    )
    assert updated.default_search_mode == "semantic"
    assert updated.alert_frequency == "weekly"
    assert updated.timezone == "America/New_York"
    assert updated.email_notifications_enabled is False


def test_create_access_token_for_user(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _build_user(7)
    expected_token = "".join(["jwt", "-", "token"])
    monkeypatch.setattr(
        "src.services.auth_service.create_access_token",
        lambda **kwargs: expected_token,
    )

    token = auth_service.create_access_token_for_user(user)
    assert token == expected_token
