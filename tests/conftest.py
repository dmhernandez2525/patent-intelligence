from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.api.routes import search as search_routes
from src.database.connection import get_session


class DummyResult:
    def __init__(self, scalar_value: int = 0) -> None:
        self._scalar_value = scalar_value

    def scalar(self) -> int:
        return self._scalar_value


class DummySession:
    async def execute(self, *args, **kwargs) -> DummyResult:  # type: ignore[no-untyped-def]
        return DummyResult()


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch):
    async def override_get_session():
        yield DummySession()

    app.dependency_overrides[get_session] = override_get_session
    monkeypatch.setattr(
        search_routes.search_service,
        "hybrid_search",
        AsyncMock(return_value=([], 0)),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
