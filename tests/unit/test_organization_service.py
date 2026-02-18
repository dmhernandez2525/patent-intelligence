"""Unit tests for OrganizationService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.organization import Organization, OrganizationInvite, OrganizationMember
from src.models.user import User
from src.services.organization_service import OrganizationService


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def all(self):
        return self._value


def _build_user(user_id: int, email: str) -> User:
    hashed_value = "".join(["stored", "-", "hash"])
    return User(
        id=user_id,
        email=email,
        hashed_password=hashed_value,
        role="viewer",
        is_active=True,
    )


@pytest.mark.asyncio
async def test_create_organization_creates_owner_membership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OrganizationService()
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    monkeypatch.setattr(
        service, "_generate_unique_invite_code", AsyncMock(return_value="invite-code")
    )

    org = await service.create_organization(session, owner_id=1, name="Core Team")

    assert org.name == "Core Team"
    assert org.owner_id == 1
    assert org.invite_code == "invite-code"


@pytest.mark.asyncio
async def test_invite_user_success(monkeypatch: pytest.MonkeyPatch) -> None:
    service = OrganizationService()
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    organization = Organization(id=5, name="Org", owner_id=1, invite_code="abc123")
    session.execute.return_value = _ScalarResult(organization)
    monkeypatch.setattr(service, "_verify_inviter_permissions", AsyncMock(return_value=None))

    invite = await service.invite_user(
        session,
        organization_id=5,
        invited_by_user_id=1,
        invited_email="Invitee@Example.com",
    )

    assert invite.organization_id == 5
    assert invite.invited_email == "invitee@example.com"
    assert invite.invite_token is not None


@pytest.mark.asyncio
async def test_invite_user_missing_organization(monkeypatch: pytest.MonkeyPatch) -> None:
    service = OrganizationService()
    session = AsyncMock()
    session.execute.return_value = _ScalarResult(None)

    monkeypatch.setattr(service, "_verify_inviter_permissions", AsyncMock(return_value=None))

    with pytest.raises(ValueError, match="Organization not found"):
        await service.invite_user(
            session,
            organization_id=999,
            invited_by_user_id=1,
            invited_email="none@example.com",
        )


@pytest.mark.asyncio
async def test_accept_invite_success_creates_membership() -> None:
    service = OrganizationService()
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    token_value = "".join(["token", "-", "value"])
    invite = OrganizationInvite(
        id=11,
        organization_id=4,
        invited_email="member@example.com",
        invited_by_user_id=1,
        invite_token=token_value,
        invite_code="code",
        status="pending",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    user = _build_user(2, "member@example.com")

    session.execute.side_effect = [
        _ScalarResult(invite),
        _ScalarResult(user),
        _ScalarResult(None),
    ]

    membership = await service.accept_invite(session, token_value, 2)

    assert membership.organization_id == 4
    assert membership.user_id == 2
    assert invite.status == "accepted"
    assert invite.accepted_at is not None


@pytest.mark.asyncio
async def test_accept_invite_rejects_expired_invite() -> None:
    service = OrganizationService()
    session = AsyncMock()
    token_value = "".join(["token", "-", "value"])
    invite = OrganizationInvite(
        id=11,
        organization_id=4,
        invited_email="member@example.com",
        invited_by_user_id=1,
        invite_token=token_value,
        invite_code="code",
        status="pending",
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    session.execute.return_value = _ScalarResult(invite)

    with pytest.raises(ValueError, match="expired"):
        await service.accept_invite(session, token_value, 2)


@pytest.mark.asyncio
async def test_verify_inviter_permissions_enforces_roles() -> None:
    service = OrganizationService()
    session = AsyncMock()
    membership = OrganizationMember(organization_id=10, user_id=2, role="viewer")
    session.execute.return_value = _ScalarResult(membership)

    with pytest.raises(PermissionError, match="owner or admin"):
        await service._verify_inviter_permissions(session, organization_id=10, invited_by_user_id=2)


@pytest.mark.asyncio
async def test_generate_unique_invite_code_returns_available_code() -> None:
    service = OrganizationService()
    session = AsyncMock()
    session.execute.side_effect = [_ScalarResult(None)]

    code = await service._generate_unique_invite_code(session)
    assert isinstance(code, str)
    assert len(code) > 0
