"""Route tests for registration and login flows."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.database.connection import get_session
from src.models.user import User
from src.services.activity_service import activity_service
from src.services.auth_service import auth_service
from src.utils.user_rate_limiter import user_rate_limiter


class DummySession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def _build_user(user_id: int, role: str = "viewer") -> User:
    hashed_value = "".join(["hashed", "-", str(user_id)])
    user = User(
        id=user_id,
        email=f"user{user_id}@example.com",
        hashed_password=hashed_value,
        role=role,
        is_active=True,
    )
    user.created_at = datetime.now(UTC)
    return user


@pytest.fixture
async def auth_client(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()

    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    monkeypatch.setattr(user_rate_limiter, "allow_request", AsyncMock(return_value=True))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_success(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    user = _build_user(10)
    monkeypatch.setattr(auth_service, "register_user", AsyncMock(return_value=user))
    monkeypatch.setattr(activity_service, "log_event", AsyncMock())

    response = await auth_client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "StrongPass123!", "role": "viewer"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 10
    assert body["email"] == "user10@example.com"
    assert body["role"] == "viewer"


@pytest.mark.asyncio
async def test_login_success(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    user = _build_user(11, role="analyst")
    user.last_login = datetime.now(UTC)
    expected_token = "".join(["token", "-", "value"])

    monkeypatch.setattr(auth_service, "authenticate_user", AsyncMock(return_value=user))
    monkeypatch.setattr(
        auth_service,
        "create_access_token_for_user",
        lambda _user: expected_token,
    )
    monkeypatch.setattr(activity_service, "log_event", AsyncMock())

    response = await auth_client.post(
        "/api/auth/login",
        json={"email": "user11@example.com", "password": "StrongPass123!"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == expected_token
    assert body["user"]["id"] == 11
    assert body["user"]["role"] == "analyst"


@pytest.mark.asyncio
async def test_login_failure(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    log_event_mock = AsyncMock()
    monkeypatch.setattr(auth_service, "authenticate_user", AsyncMock(return_value=None))
    monkeypatch.setattr(activity_service, "log_event", log_event_mock)

    response = await auth_client.post(
        "/api/auth/login",
        json={"email": "missing@example.com", "password": "StrongPass123!"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"
    log_event_mock.assert_awaited()
