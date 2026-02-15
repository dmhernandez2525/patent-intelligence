"""Tests for auth context middleware behavior."""

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from src.api.middleware.auth_context import AuthContextMiddleware
from src.config import settings
from src.utils.security import create_access_token
from src.utils.user_rate_limiter import user_rate_limiter


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(AuthContextMiddleware)

    @app.get("/context")
    async def context(request: Request) -> dict:
        user_context = getattr(request.state, "user_context", None)
        if user_context is None:
            return {"user_id": None, "email": None, "role": None}
        return {
            "user_id": user_context.user_id,
            "email": user_context.email,
            "role": user_context.role,
        }

    return app


@pytest.mark.asyncio
async def test_middleware_sets_context_from_valid_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_test_app()
    monkeypatch.setattr(settings, "secret_key", "test-secret-key")
    token = create_access_token(user_id=9, email="valid@example.com", role="admin")
    monkeypatch.setattr(user_rate_limiter, "allow_request", AsyncMock(return_value=True))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/context", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"user_id": 9, "email": "valid@example.com", "role": "admin"}


@pytest.mark.asyncio
async def test_middleware_ignores_invalid_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_test_app()
    monkeypatch.setattr(settings, "secret_key", "test-secret-key")
    monkeypatch.setattr(user_rate_limiter, "allow_request", AsyncMock(return_value=True))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/context", headers={"Authorization": "Bearer bad.token"})

    assert response.status_code == 200
    assert response.json() == {"user_id": None, "email": None, "role": None}
