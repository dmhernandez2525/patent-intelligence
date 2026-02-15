"""Unit tests for shared watchlist collaboration service."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.models.collaboration_watchlist import (
    SharedPermission,
    SharedWatchlist,
    SharedWatchlistInvite,
    SharedWatchlistItem,
    SharedWatchlistMember,
)
from src.models.user import User
from src.services.shared_watchlist_service import shared_watchlist_service


class _Result:
    def __init__(self, scalar_value=None, rows=None):
        self._scalar_value = scalar_value
        self._rows = rows or []

    def scalar_one_or_none(self):
        return self._scalar_value

    def scalars(self):
        return SimpleNamespace(all=lambda: self._rows)


def _watchlist() -> SharedWatchlist:
    watchlist = SharedWatchlist(id=3, name="Energy", description="Desc", owner_id=1)
    watchlist.members = [SharedWatchlistMember(user_id=1, permission="owner")]
    watchlist.items = [SharedWatchlistItem(id=4, item_type="patent", item_value="US1", added_by_user_id=1)]
    watchlist.created_at = datetime.now(UTC)
    return watchlist


@pytest.mark.asyncio
async def test_list_for_user_returns_serialized_watchlists() -> None:
    session = AsyncMock()
    session.execute.return_value = _Result(rows=[_watchlist()])

    rows = await shared_watchlist_service.list_for_user(session, user_id=1)

    assert len(rows) == 1
    assert rows[0]["name"] == "Energy"
    assert rows[0]["member_count"] == 1


@pytest.mark.asyncio
async def test_add_item_duplicate_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    monkeypatch.setattr(
        shared_watchlist_service,
        "_require_permission",
        AsyncMock(return_value=SharedPermission.OWNER.value),
    )
    session.execute.return_value = _Result(
        scalar_value=SharedWatchlistItem(id=1, watchlist_id=1, item_type="patent", item_value="US1", added_by_user_id=1)
    )

    with pytest.raises(ValueError, match="already exists"):
        await shared_watchlist_service.add_item(
            session,
            watchlist_id=1,
            actor_user_id=1,
            item_type="patent",
            item_value="US1",
        )


@pytest.mark.asyncio
async def test_invite_and_revoke_member_permission_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    monkeypatch.setattr(
        shared_watchlist_service,
        "_require_permission",
        AsyncMock(side_effect=[SharedPermission.OWNER.value, SharedPermission.EDITOR.value]),
    )
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    invite = await shared_watchlist_service.invite_collaborator(
        session,
        watchlist_id=9,
        actor_user_id=1,
        invited_email="viewer@example.com",
        permission="viewer",
    )
    assert invite.watchlist_id == 9
    assert invite.status == "pending"

    target_member = SharedWatchlistMember(
        watchlist_id=9,
        user_id=55,
        permission=SharedPermission.EDITOR.value,
    )
    session.execute.return_value = _Result(scalar_value=target_member)

    with pytest.raises(PermissionError, match="only revoke viewer"):
        await shared_watchlist_service.revoke_member(
            session,
            watchlist_id=9,
            actor_user_id=2,
            target_user_id=55,
        )


@pytest.mark.asyncio
async def test_accept_invite_validates_email_match(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    invite = SharedWatchlistInvite(
        id=5,
        watchlist_id=1,
        invited_email="target@example.com",
        invited_by_user_id=1,
        invite_token="".join(["tok", "en"]),
        permission="viewer",
        status="pending",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    user = User(
        id=2,
        email="different@example.com",
        hashed_password="".join(["h", "x"]),
        role="viewer",
        is_active=True,
    )
    monkeypatch.setattr(shared_watchlist_service, "_load_invite", AsyncMock(return_value=invite))
    monkeypatch.setattr(shared_watchlist_service, "_load_user", AsyncMock(return_value=user))

    with pytest.raises(PermissionError, match="does not match"):
        await shared_watchlist_service.accept_invite(session, "token", current_user_id=2)
