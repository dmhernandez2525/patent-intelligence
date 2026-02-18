"""Additional unit tests for shared watchlist service."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.collaboration_watchlist import (
    SharedPermission,
    SharedWatchlist,
    SharedWatchlistInvite,
)
from src.models.user import User
from src.services.shared_watchlist_service import SharedWatchlistService

_OWN = SharedPermission.OWNER.value
_EDIT = SharedPermission.EDITOR.value
_VIEW = SharedPermission.VIEWER.value


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


def _session(add=True):
    s = AsyncMock()
    if add:
        s.add = MagicMock()
    s.flush = AsyncMock()
    s.refresh = AsyncMock()
    return s


def _invite(email="a@example.com", status="pending", days=3, **kw):
    defaults = {
        "id": 10, "watchlist_id": 3, "invited_email": email,
        "invited_by_user_id": 1, "invite_token": "".join(["to", "k"]),
        "permission": "editor", "status": status,
        "expires_at": datetime.now(UTC) + timedelta(days=days),
    }
    defaults.update(kw)
    return SharedWatchlistInvite(**defaults)


def _user(uid=5, email="A@Example.com"):
    return User(
        id=uid, email=email, hashed_password="".join(["h", "x"]),
        role="viewer", is_active=True,
    )


def _patch_perm(mp, svc, val):
    mp.setattr(svc, "_require_permission", AsyncMock(return_value=val))


# ---- create_watchlist ----

@pytest.mark.asyncio
async def test_create_watchlist_owner_and_member():
    svc, s = _svc(), _session()
    wl = await svc.create_watchlist(s, 7, "Biotech", "desc")
    assert wl.name == "Biotech" and wl.owner_id == 7
    assert s.add.call_count == 2 and s.flush.call_count == 2

@pytest.mark.asyncio
async def test_create_watchlist_no_description():
    svc, s = _svc(), _session()
    wl = await svc.create_watchlist(s, 1, "Minimal")
    assert wl.description is None

# ---- get_watchlist ----

@pytest.mark.asyncio
async def test_get_watchlist_success(monkeypatch):
    svc, s = _svc(), AsyncMock()
    wl = SharedWatchlist(id=5, name="Solar", owner_id=1)
    wl.items, wl.members, wl.invites = [], [], []
    monkeypatch.setattr(svc, "_get_watchlist", AsyncMock(return_value=wl))
    _patch_perm(monkeypatch, svc, _VIEW)
    r = await svc.get_watchlist(s, 5, 2)
    assert r.id == 5 and r.name == "Solar"

@pytest.mark.asyncio
async def test_get_watchlist_not_found(monkeypatch):
    svc, s = _svc(), AsyncMock()
    monkeypatch.setattr(
        svc, "_get_watchlist",
        AsyncMock(side_effect=ValueError("Shared watchlist not found")),
    )
    with pytest.raises(ValueError, match="not found"):
        await svc.get_watchlist(s, 999, 1)

@pytest.mark.asyncio
async def test_get_watchlist_no_permission(monkeypatch):
    svc, s = _svc(), AsyncMock()
    wl = SharedWatchlist(id=5, name="X", owner_id=1)
    wl.items, wl.members, wl.invites = [], [], []
    monkeypatch.setattr(svc, "_get_watchlist", AsyncMock(return_value=wl))
    monkeypatch.setattr(
        svc, "_require_permission",
        AsyncMock(side_effect=PermissionError("Insufficient")),
    )
    with pytest.raises(PermissionError, match="Insufficient"):
        await svc.get_watchlist(s, 5, 99)

# ---- add_item (success paths) ----

@pytest.mark.asyncio
async def test_add_item_patent_type(monkeypatch):
    svc, s = _svc(), _session()
    _patch_perm(monkeypatch, svc, _EDIT)
    s.execute.side_effect = [_R(val=None), _R(val=42)]
    item = await svc.add_item(s, 1, 2, "patent", " US999 ")
    assert item.item_value == "US999" and item.patent_id == 42
    s.add.assert_called_once()

@pytest.mark.asyncio
async def test_add_item_non_patent_type(monkeypatch):
    svc, s = _svc(), _session()
    _patch_perm(monkeypatch, svc, _OWN)
    s.execute.return_value = _R(val=None)
    item = await svc.add_item(s, 3, 1, "assignee", "Acme Corp")
    assert item.item_type == "assignee" and item.patent_id is None

# ---- accept_invite (success) ----

@pytest.mark.asyncio
async def test_accept_invite_creates_member(monkeypatch):
    svc, s = _svc(), _session()
    inv = _invite(email="alice@example.com")
    monkeypatch.setattr(svc, "_load_invite", AsyncMock(return_value=inv))
    monkeypatch.setattr(
        svc, "_load_user",
        AsyncMock(return_value=_user(5, "Alice@Example.com")),
    )
    s.execute.return_value = _R(val=None)
    m = await svc.accept_invite(s, "tok", 5)
    assert m.watchlist_id == 3 and m.permission == "editor"
    assert inv.status == "accepted"
    s.add.assert_called_once()

# ---- decline_invite ----

@pytest.mark.asyncio
async def test_decline_invite_success(monkeypatch):
    svc, s = _svc(), _session(add=False)
    inv = _invite(email="bob@example.com")
    monkeypatch.setattr(svc, "_load_invite", AsyncMock(return_value=inv))
    monkeypatch.setattr(
        svc, "_load_user",
        AsyncMock(return_value=_user(8, "Bob@Example.com")),
    )
    r = await svc.decline_invite(s, "tok", 8)
    assert r.status == "declined" and r.responded_at is not None

@pytest.mark.asyncio
async def test_decline_invite_not_pending(monkeypatch):
    svc, s = _svc(), AsyncMock()
    inv = _invite(email="bob@example.com", status="accepted")
    monkeypatch.setattr(svc, "_load_invite", AsyncMock(return_value=inv))
    monkeypatch.setattr(
        svc, "_load_user",
        AsyncMock(return_value=_user(8, "Bob@Example.com")),
    )
    with pytest.raises(ValueError, match="no longer pending"):
        await svc.decline_invite(s, "tok", 8)

# ---- revoke_invite ----

@pytest.mark.asyncio
async def test_revoke_invite_success(monkeypatch):
    svc, s = _svc(), _session(add=False)
    inv = _invite(email="t@example.com", invite_token="".join(["r", "ev"]))
    s.execute.return_value = _R(val=inv)
    _patch_perm(monkeypatch, svc, _OWN)
    r = await svc.revoke_invite(s, invite_id=11, actor_user_id=1)
    assert r.status == "revoked" and r.responded_at is not None

@pytest.mark.asyncio
async def test_revoke_invite_not_found():
    svc, s = _svc(), AsyncMock()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="Invite not found"):
        await svc.revoke_invite(s, invite_id=999, actor_user_id=1)
