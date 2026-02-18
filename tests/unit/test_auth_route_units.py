"""Direct unit tests for auth route handlers."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.api.routes import auth as auth_routes
from src.api.schemas.auth import (
    OrganizationCreateRequest,
    OrganizationInviteRequest,
    PreferencesUpdateRequest,
)
from src.models.organization import Organization, OrganizationInvite, OrganizationMember
from src.models.user import User, UserPreference


def _build_user(user_id: int = 1, role: str = "viewer") -> User:
    hashed_value = "".join(["stored", "-", "hash"])
    user = User(
        id=user_id,
        email=f"user{user_id}@example.com",
        hashed_password=hashed_value,
        role=role,
        is_active=True,
    )
    user.created_at = datetime.now(UTC)
    return user


@pytest.mark.asyncio
async def test_me_returns_user_response() -> None:
    user = _build_user()
    response = await auth_routes.me(current_user=user)
    assert response.id == user.id
    assert response.email == user.email


@pytest.mark.asyncio
async def test_get_preferences_returns_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _build_user()
    session = AsyncMock()
    preferences = UserPreference(
        id=1,
        user_id=user.id,
        default_search_mode="hybrid",
        alert_frequency="daily",
        timezone="UTC",
        email_notifications_enabled=True,
    )
    monkeypatch.setattr(
        auth_routes.auth_service, "get_user_preferences", AsyncMock(return_value=preferences)
    )

    response = await auth_routes.get_preferences(current_user=user, session=session)
    assert response.default_search_mode == "hybrid"


@pytest.mark.asyncio
async def test_update_preferences_requires_input() -> None:
    user = _build_user()
    session = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await auth_routes.update_preferences(
            payload=PreferencesUpdateRequest(),
            current_user=user,
            session=session,
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_update_preferences_success(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _build_user()
    session = AsyncMock()
    session.commit = AsyncMock()
    preferences = UserPreference(
        id=2,
        user_id=user.id,
        default_search_mode="semantic",
        alert_frequency="weekly",
        timezone="America/New_York",
        email_notifications_enabled=False,
    )
    monkeypatch.setattr(
        auth_routes.auth_service,
        "update_user_preferences",
        AsyncMock(return_value=preferences),
    )
    monkeypatch.setattr(auth_routes.activity_service, "log_event", AsyncMock())

    response = await auth_routes.update_preferences(
        payload=PreferencesUpdateRequest(default_search_mode="semantic"),
        current_user=user,
        session=session,
    )

    assert response.default_search_mode == "semantic"
    assert response.alert_frequency == "weekly"
    assert response.email_notifications_enabled is False


@pytest.mark.asyncio
async def test_admin_ping_returns_ok() -> None:
    user = _build_user(role="admin")
    response = await auth_routes.admin_ping(current_user=user)
    assert response["status"] == "ok"


@pytest.mark.asyncio
async def test_create_organization_success(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _build_user(role="admin")
    session = AsyncMock()
    session.commit = AsyncMock()
    organization = Organization(id=7, name="Team", owner_id=user.id, invite_code="abc")
    organization.created_at = datetime.now(UTC)

    monkeypatch.setattr(
        auth_routes.organization_service,
        "create_organization",
        AsyncMock(return_value=organization),
    )
    monkeypatch.setattr(auth_routes.activity_service, "log_event", AsyncMock())

    response = await auth_routes.create_organization(
        payload=OrganizationCreateRequest(name="Team"),
        current_user=user,
        session=session,
    )
    assert response.id == 7
    assert response.owner_id == user.id


@pytest.mark.asyncio
async def test_invite_to_organization_permission_error(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _build_user(role="admin")
    session = AsyncMock()
    monkeypatch.setattr(
        auth_routes.organization_service,
        "invite_user",
        AsyncMock(side_effect=PermissionError("Only owner or admin can invite collaborators")),
    )

    with pytest.raises(HTTPException) as exc_info:
        await auth_routes.invite_to_organization(
            organization_id=4,
            payload=OrganizationInviteRequest(email="invite@example.com"),
            current_user=user,
            session=session,
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_invite_to_organization_success(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _build_user(role="admin")
    session = AsyncMock()
    session.commit = AsyncMock()
    token_value = "".join(["token", "-", "value"])
    invite = OrganizationInvite(
        id=3,
        organization_id=4,
        invited_email="invite@example.com",
        invited_by_user_id=user.id,
        invite_token=token_value,
        invite_code="code",
        status="pending",
        expires_at=datetime.now(UTC),
    )
    monkeypatch.setattr(
        auth_routes.organization_service, "invite_user", AsyncMock(return_value=invite)
    )
    monkeypatch.setattr(auth_routes.activity_service, "log_event", AsyncMock())

    response = await auth_routes.invite_to_organization(
        organization_id=4,
        payload=OrganizationInviteRequest(email="invite@example.com"),
        current_user=user,
        session=session,
    )
    assert response.organization_id == 4
    assert response.status == "pending"


@pytest.mark.asyncio
async def test_accept_invite_handles_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _build_user()
    session = AsyncMock()
    monkeypatch.setattr(
        auth_routes.organization_service,
        "accept_invite",
        AsyncMock(side_effect=ValueError("Invite not found")),
    )

    with pytest.raises(HTTPException) as exc_info:
        await auth_routes.accept_invite("bad-token", current_user=user, session=session)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_accept_invite_success(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _build_user()
    session = AsyncMock()
    session.commit = AsyncMock()
    membership = OrganizationMember(id=5, organization_id=2, user_id=user.id, role="member")
    monkeypatch.setattr(
        auth_routes.organization_service,
        "accept_invite",
        AsyncMock(return_value=membership),
    )
    monkeypatch.setattr(auth_routes.activity_service, "log_event", AsyncMock())

    response = await auth_routes.accept_invite("token", current_user=user, session=session)
    assert response.organization_id == 2
    assert response.user_id == user.id


@pytest.mark.asyncio
async def test_sso_start_and_callback_success() -> None:
    start_response = await auth_routes.sso_start(provider="google", state="state")
    callback_response = await auth_routes.sso_callback(
        provider="google", code="code", state="state"
    )

    assert start_response.provider == "google"
    assert callback_response.status == "stub"


@pytest.mark.asyncio
async def test_sso_invalid_provider_raises() -> None:
    with pytest.raises(HTTPException) as start_exc:
        await auth_routes.sso_start(provider="unknown", state="state")
    assert start_exc.value.status_code == 404

    with pytest.raises(HTTPException) as callback_exc:
        await auth_routes.sso_callback(provider="unknown", code="code", state="state")
    assert callback_exc.value.status_code == 404
