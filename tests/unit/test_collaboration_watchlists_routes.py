"""Unit tests for collaboration watchlist routes."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from src.api.routes import collaboration_watchlists
from src.models.collaboration_watchlist import (
    SharedWatchlist,
    SharedWatchlistInvite,
    SharedWatchlistItem,
    SharedWatchlistMember,
)
from src.models.user import User


def _request() -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [],
        "client": ("127.0.0.1", 7777),
    }
    return Request(scope)


def _user() -> User:
    return User(id=1, email="owner@example.com", hashed_password="".join(["h", "x"]), role="analyst", is_active=True)


@pytest.mark.asyncio
async def test_list_and_create_watchlists(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    monkeypatch.setattr(
        collaboration_watchlists.shared_watchlist_service,
        "list_for_user",
        AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "name": "Shared",
                    "description": None,
                    "owner_id": 1,
                    "member_count": 1,
                    "item_count": 0,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ]
        ),
    )
    listing = await collaboration_watchlists.list_shared_watchlists(current_user=_user(), session=session)
    assert listing.watchlists[0].name == "Shared"

    watchlist = SharedWatchlist(id=5, name="New", description=None, owner_id=1)
    monkeypatch.setattr(
        collaboration_watchlists.shared_watchlist_service,
        "create_watchlist",
        AsyncMock(return_value=watchlist),
    )
    monkeypatch.setattr(
        collaboration_watchlists.activity_service,
        "log_event",
        AsyncMock(),
    )
    session.commit = AsyncMock()
    payload = collaboration_watchlists.SharedWatchlistCreateRequest(name="New")
    created = await collaboration_watchlists.create_shared_watchlist(
        payload=payload,
        request=_request(),
        current_user=_user(),
        session=session,
    )
    assert created.id == 5
    assert created.members[0].permission == "owner"


@pytest.mark.asyncio
async def test_get_shared_watchlist_maps_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    monkeypatch.setattr(
        collaboration_watchlists.shared_watchlist_service,
        "get_watchlist",
        AsyncMock(side_effect=ValueError("missing")),
    )
    with pytest.raises(HTTPException) as missing:
        await collaboration_watchlists.get_shared_watchlist(1, current_user=_user(), session=session)
    assert missing.value.status_code == 404

    monkeypatch.setattr(
        collaboration_watchlists.shared_watchlist_service,
        "get_watchlist",
        AsyncMock(side_effect=PermissionError("forbidden")),
    )
    with pytest.raises(HTTPException) as forbidden:
        await collaboration_watchlists.get_shared_watchlist(1, current_user=_user(), session=session)
    assert forbidden.value.status_code == 403


@pytest.mark.asyncio
async def test_add_item_and_invite_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    session.commit = AsyncMock()
    monkeypatch.setattr(collaboration_watchlists.activity_service, "log_event", AsyncMock())

    item = SharedWatchlistItem(
        id=3,
        watchlist_id=1,
        item_type="patent",
        item_value="US1",
        patent_id=22,
        added_by_user_id=1,
    )
    monkeypatch.setattr(
        collaboration_watchlists.shared_watchlist_service,
        "add_item",
        AsyncMock(return_value=item),
    )
    item_payload = collaboration_watchlists.SharedWatchlistAddItemRequest(
        item_type="patent",
        item_value="US1",
    )
    added = await collaboration_watchlists.add_shared_watchlist_item(
        watchlist_id=1,
        payload=item_payload,
        request=_request(),
        current_user=_user(),
        session=session,
    )
    assert added.id == 3

    invite = SharedWatchlistInvite(
        id=6,
        watchlist_id=1,
        invited_email="new@example.com",
        invited_by_user_id=1,
        permission="viewer",
        invite_token="".join(["a", "bc"]),
        status="pending",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    monkeypatch.setattr(
        collaboration_watchlists.shared_watchlist_service,
        "invite_collaborator",
        AsyncMock(return_value=invite),
    )
    invite_payload = collaboration_watchlists.SharedWatchlistInviteRequest(
        email="new@example.com",
        permission="viewer",
    )
    invited = await collaboration_watchlists.invite_watchlist_collaborator(
        watchlist_id=1,
        payload=invite_payload,
        request=_request(),
        current_user=_user(),
        session=session,
    )
    assert invited.id == 6


@pytest.mark.asyncio
async def test_invite_action_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    session.commit = AsyncMock()
    monkeypatch.setattr(collaboration_watchlists.activity_service, "log_event", AsyncMock())
    monkeypatch.setattr(
        collaboration_watchlists.shared_watchlist_service,
        "accept_invite",
        AsyncMock(return_value=SharedWatchlistMember(watchlist_id=1, user_id=2, permission="viewer")),
    )
    accepted = await collaboration_watchlists.accept_watchlist_invite(
        invite_token="".join(["to", "k"]),
        current_user=_user(),
        session=session,
    )
    assert accepted.status == "accepted"

    monkeypatch.setattr(
        collaboration_watchlists.shared_watchlist_service,
        "decline_invite",
        AsyncMock(return_value=True),
    )
    declined = await collaboration_watchlists.decline_watchlist_invite(
        invite_token="".join(["to", "k"]),
        current_user=_user(),
        session=session,
    )
    assert declined.status == "declined"

    monkeypatch.setattr(
        collaboration_watchlists.shared_watchlist_service,
        "revoke_member",
        AsyncMock(return_value=True),
    )
    revoked = await collaboration_watchlists.revoke_watchlist_member(
        watchlist_id=1,
        member_user_id=2,
        current_user=_user(),
        session=session,
    )
    assert revoked.success is True

    monkeypatch.setattr(
        collaboration_watchlists.shared_watchlist_service,
        "revoke_invite",
        AsyncMock(return_value=True),
    )
    invite_revoked = await collaboration_watchlists.revoke_watchlist_invite(
        invite_id=7,
        current_user=_user(),
        session=session,
    )
    assert invite_revoked.status == "revoked"
