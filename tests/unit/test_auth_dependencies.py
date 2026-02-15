"""Tests for auth dependency helpers and RBAC."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.api.dependencies.auth import (
    RequestUserContext,
    get_current_user,
    require_roles,
    resolve_user_id,
)
from src.models.user import User


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


def _build_user(*, user_id: int, role: str) -> User:
    hashed_value = "".join(["hashed", "-", str(user_id)])
    user = User(
        id=user_id,
        email=f"{role}@example.com",
        hashed_password=hashed_value,
        role=role,
        is_active=True,
    )
    user.created_at = datetime.now(UTC)
    return user


@pytest.mark.asyncio
async def test_require_roles_allows_authorized_user() -> None:
    dependency = require_roles("admin")
    admin_user = _build_user(user_id=1, role="admin")

    result = await dependency(current_user=admin_user)
    assert result.id == 1


@pytest.mark.asyncio
async def test_require_roles_blocks_unauthorized_user() -> None:
    dependency = require_roles("admin")
    viewer_user = _build_user(user_id=2, role="viewer")

    with pytest.raises(HTTPException) as exc_info:
        await dependency(current_user=viewer_user)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_current_user_requires_authentication() -> None:
    session = AsyncMock()
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request_user=None, session=session)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_success() -> None:
    session = AsyncMock()
    user = _build_user(user_id=3, role="analyst")
    session.execute.return_value = _ScalarResult(user)
    context = RequestUserContext(user_id=3, email=user.email, role=user.role)

    current_user = await get_current_user(request_user=context, session=session)
    assert current_user.id == 3


def test_resolve_user_id_fallback() -> None:
    assert resolve_user_id(None) == "default"
    context = RequestUserContext(user_id=4, email="a@example.com", role="viewer")
    assert resolve_user_id(context) == "4"
