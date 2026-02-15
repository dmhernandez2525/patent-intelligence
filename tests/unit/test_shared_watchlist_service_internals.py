"""Tests for shared watchlist service internal methods and edge cases."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.models.collaboration_watchlist import (
    SharedPermission,
    SharedWatchlist,
    SharedWatchlistInvite,
    SharedWatchlistMember,
)
from src.models.user import User
from src.services.shared_watchlist_service import SharedWatchlistService


class _R:
    def __init__(self, val=None, rows=None):
        self._v = val
        self._rows = rows or []

    def scalar_one_or_none(self):
        return self._v

    def scalars(self):
        return SimpleNamespace(all=lambda: self._rows)


def _svc():
    return SharedWatchlistService()


@pytest.mark.asyncio
async def test_require_permission_success():
    svc, s = _svc(), AsyncMock()
    member = SharedWatchlistMember(watchlist_id=1, user_id=5, permission="owner")
    s.execute.return_value = _R(val=member)
    perm = await svc._require_permission(s, 1, 5, {"owner"})
    assert perm == "owner"


@pytest.mark.asyncio
async def test_require_permission_denied_no_member():
    svc, s = _svc(), AsyncMock()
    s.execute.return_value = _R(val=None)
    with pytest.raises(PermissionError, match="Insufficient"):
        await svc._require_permission(s, 1, 99, {"owner"})


@pytest.mark.asyncio
async def test_require_permission_denied_wrong_role():
    svc, s = _svc(), AsyncMock()
    member = SharedWatchlistMember(watchlist_id=1, user_id=5, permission="viewer")
    s.execute.return_value = _R(val=member)
    with pytest.raises(PermissionError, match="Insufficient"):
        await svc._require_permission(s, 1, 5, {"owner", "editor"})


@pytest.mark.asyncio
async def test_get_watchlist_found():
    svc, s = _svc(), AsyncMock()
    wl = SharedWatchlist(id=5, name="Test", owner_id=1)
    wl.items, wl.members, wl.invites = [], [], []
    s.execute.return_value = _R(val=wl)
    result = await svc._get_watchlist(s, 5)
    assert result.id == 5


@pytest.mark.asyncio
async def test_get_watchlist_not_found():
    svc, s = _svc(), AsyncMock()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="not found"):
        await svc._get_watchlist(s, 999)


@pytest.mark.asyncio
async def test_load_invite_found():
    svc, s = _svc(), AsyncMock()
    inv = SharedWatchlistInvite(
        id=1, watchlist_id=1, invited_email="a@b.com",
        invited_by_user_id=1, invite_token="".join(["t", "ok"]),
        permission="viewer", status="pending",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    s.execute.return_value = _R(val=inv)
    result = await svc._load_invite(s, "tok")
    assert result.id == 1


@pytest.mark.asyncio
async def test_load_invite_not_found():
    svc, s = _svc(), AsyncMock()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="Invite not found"):
        await svc._load_invite(s, "bad")


@pytest.mark.asyncio
async def test_load_user_found():
    svc, s = _svc(), AsyncMock()
    user = User(
        id=5, email="a@b.com", hashed_password="".join(["h", "x"]),
        role="viewer", is_active=True,
    )
    s.execute.return_value = _R(val=user)
    result = await svc._load_user(s, 5)
    assert result.id == 5


@pytest.mark.asyncio
async def test_load_user_not_found():
    svc, s = _svc(), AsyncMock()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="User not found"):
        await svc._load_user(s, 999)


@pytest.mark.asyncio
async def test_revoke_member_owner_cannot_be_revoked(monkeypatch):
    svc, s = _svc(), AsyncMock()
    monkeypatch.setattr(
        svc, "_require_permission",
        AsyncMock(return_value=SharedPermission.OWNER.value),
    )
    target = SharedWatchlistMember(
        watchlist_id=1, user_id=2, permission="owner",
    )
    s.execute.return_value = _R(val=target)
    with pytest.raises(PermissionError, match="Owner membership"):
        await svc.revoke_member(s, 1, 1, 2)


@pytest.mark.asyncio
async def test_revoke_member_success_deletes(monkeypatch):
    svc, s = _svc(), AsyncMock()
    s.delete = AsyncMock()
    monkeypatch.setattr(
        svc, "_require_permission",
        AsyncMock(return_value=SharedPermission.OWNER.value),
    )
    target = SharedWatchlistMember(
        watchlist_id=1, user_id=3, permission="viewer",
    )
    s.execute.return_value = _R(val=target)
    result = await svc.revoke_member(s, 1, 1, 3)
    assert result is True
    s.delete.assert_called_once_with(target)


@pytest.mark.asyncio
async def test_revoke_member_not_found(monkeypatch):
    svc, s = _svc(), AsyncMock()
    monkeypatch.setattr(
        svc, "_require_permission",
        AsyncMock(return_value=SharedPermission.OWNER.value),
    )
    s.execute.return_value = _R(val=None)
    result = await svc.revoke_member(s, 1, 1, 999)
    assert result is False


@pytest.mark.asyncio
async def test_invite_invalid_permission(monkeypatch):
    svc, s = _svc(), AsyncMock()
    monkeypatch.setattr(
        svc, "_require_permission",
        AsyncMock(return_value=SharedPermission.OWNER.value),
    )
    with pytest.raises(ValueError, match="editor or viewer"):
        await svc.invite_collaborator(s, 1, 1, "a@b.com", "owner")


@pytest.mark.asyncio
async def test_accept_invite_expired(monkeypatch):
    svc, s = _svc(), AsyncMock()
    inv = SharedWatchlistInvite(
        id=1, watchlist_id=1, invited_email="a@b.com",
        invited_by_user_id=1, invite_token="".join(["t", "ok"]),
        permission="viewer", status="pending",
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    user = User(
        id=5, email="a@b.com", hashed_password="".join(["h", "x"]),
        role="viewer", is_active=True,
    )
    monkeypatch.setattr(svc, "_load_invite", AsyncMock(return_value=inv))
    monkeypatch.setattr(svc, "_load_user", AsyncMock(return_value=user))
    with pytest.raises(ValueError, match="expired"):
        await svc.accept_invite(s, "tok", 5)


@pytest.mark.asyncio
async def test_accept_invite_already_accepted(monkeypatch):
    svc, s = _svc(), AsyncMock()
    inv = SharedWatchlistInvite(
        id=1, watchlist_id=1, invited_email="a@b.com",
        invited_by_user_id=1, invite_token="".join(["t", "ok"]),
        permission="viewer", status="accepted",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    user = User(
        id=5, email="a@b.com", hashed_password="".join(["h", "x"]),
        role="viewer", is_active=True,
    )
    monkeypatch.setattr(svc, "_load_invite", AsyncMock(return_value=inv))
    monkeypatch.setattr(svc, "_load_user", AsyncMock(return_value=user))
    with pytest.raises(ValueError, match="no longer pending"):
        await svc.accept_invite(s, "tok", 5)


@pytest.mark.asyncio
async def test_accept_invite_upgrades_existing_member(monkeypatch):
    from unittest.mock import MagicMock

    svc, s = _svc(), AsyncMock()
    s.add = MagicMock()
    s.flush = AsyncMock()
    s.refresh = AsyncMock()
    inv = SharedWatchlistInvite(
        id=1, watchlist_id=1, invited_email="a@b.com",
        invited_by_user_id=1, invite_token="".join(["t", "ok"]),
        permission="editor", status="pending",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    user = User(
        id=5, email="a@b.com", hashed_password="".join(["h", "x"]),
        role="viewer", is_active=True,
    )
    existing = SharedWatchlistMember(watchlist_id=1, user_id=5, permission="viewer")
    monkeypatch.setattr(svc, "_load_invite", AsyncMock(return_value=inv))
    monkeypatch.setattr(svc, "_load_user", AsyncMock(return_value=user))
    s.execute.return_value = _R(val=existing)
    result = await svc.accept_invite(s, "tok", 5)
    assert result.permission == "editor"
    s.add.assert_not_called()


@pytest.mark.asyncio
async def test_decline_invite_email_mismatch(monkeypatch):
    svc, s = _svc(), AsyncMock()
    inv = SharedWatchlistInvite(
        id=1, watchlist_id=1, invited_email="a@b.com",
        invited_by_user_id=1, invite_token="".join(["t", "ok"]),
        permission="viewer", status="pending",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    user = User(
        id=5, email="wrong@b.com", hashed_password="".join(["h", "x"]),
        role="viewer", is_active=True,
    )
    monkeypatch.setattr(svc, "_load_invite", AsyncMock(return_value=inv))
    monkeypatch.setattr(svc, "_load_user", AsyncMock(return_value=user))
    with pytest.raises(PermissionError, match="does not match"):
        await svc.decline_invite(s, "tok", 5)
