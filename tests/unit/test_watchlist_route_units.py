"""Direct unit tests for watchlist route handlers."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.api.dependencies.auth import RequestUserContext
from src.api.routes import watchlist as watchlist_routes
from src.api.schemas.watchlist import WatchlistAddRequest, WatchlistUpdateRequest


def _request_stub() -> SimpleNamespace:
    return SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"), headers={"User-Agent": "test"})


@pytest.mark.asyncio
async def test_get_watchlist_success(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    request_user = RequestUserContext(user_id=1, email="u@example.com", role="viewer")
    monkeypatch.setattr(
        watchlist_routes.watchlist_service,
        "get_watchlist",
        AsyncMock(
            return_value=(
                [
                    {
                        "id": 1,
                        "item_type": "patent",
                        "item_value": "US1",
                        "patent_id": None,
                        "name": "US1",
                        "notes": None,
                        "notify_expiration": True,
                        "notify_maintenance": True,
                        "notify_citations": False,
                        "notify_new_patents": False,
                        "expiration_lead_days": 90,
                        "maintenance_lead_days": 30,
                        "is_active": True,
                        "unread_alerts": 0,
                        "created_at": None,
                    }
                ],
                1,
            )
        ),
    )

    response = await watchlist_routes.get_watchlist(
        item_type=None,
        include_inactive=False,
        page=1,
        per_page=20,
        request_user=request_user,
        session=session,
    )
    assert response.total == 1
    assert len(response.items) == 1


@pytest.mark.asyncio
async def test_add_to_watchlist_success(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    session.commit = AsyncMock()
    request_user = RequestUserContext(user_id=1, email="u@example.com", role="viewer")

    item_dict = {
        "id": 1,
        "item_type": "patent",
        "item_value": "US1",
        "patent_id": None,
        "name": "US1",
        "notes": None,
        "notify_expiration": True,
        "notify_maintenance": True,
        "notify_citations": False,
        "notify_new_patents": False,
        "expiration_lead_days": 90,
        "maintenance_lead_days": 30,
        "is_active": True,
        "unread_alerts": 0,
        "created_at": None,
    }
    monkeypatch.setattr(
        watchlist_routes.watchlist_service,
        "add_to_watchlist",
        AsyncMock(return_value=item_dict),
    )
    monkeypatch.setattr(watchlist_routes.activity_service, "log_event", AsyncMock())

    payload = WatchlistAddRequest(item_type="patent", item_value="US1")
    response = await watchlist_routes.add_to_watchlist(
        payload=payload,
        request=_request_stub(),
        request_user=request_user,
        session=session,
    )
    assert response.id == 1


@pytest.mark.asyncio
async def test_add_to_watchlist_handles_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    monkeypatch.setattr(
        watchlist_routes.watchlist_service,
        "add_to_watchlist",
        AsyncMock(side_effect=ValueError("duplicate")),
    )

    with pytest.raises(HTTPException) as exc_info:
        await watchlist_routes.add_to_watchlist(
            payload=WatchlistAddRequest(item_type="patent", item_value="US1"),
            request=_request_stub(),
            request_user=None,
            session=session,
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_update_watchlist_item_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    session.commit = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await watchlist_routes.update_watchlist_item(
            item_id=1,
            payload=WatchlistUpdateRequest(),
            request_user=None,
            session=session,
        )
    assert exc_info.value.status_code == 400

    monkeypatch.setattr(
        watchlist_routes.watchlist_service,
        "update_watchlist_item",
        AsyncMock(return_value=None),
    )
    with pytest.raises(HTTPException) as exc_not_found:
        await watchlist_routes.update_watchlist_item(
            item_id=1,
            payload=WatchlistUpdateRequest(name="next"),
            request_user=None,
            session=session,
        )
    assert exc_not_found.value.status_code == 404


@pytest.mark.asyncio
async def test_remove_and_alert_operations(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    session.commit = AsyncMock()

    monkeypatch.setattr(
        watchlist_routes.watchlist_service,
        "remove_from_watchlist",
        AsyncMock(return_value=False),
    )
    with pytest.raises(HTTPException) as remove_exc:
        await watchlist_routes.remove_from_watchlist(1, request_user=None, session=session)
    assert remove_exc.value.status_code == 404

    monkeypatch.setattr(
        watchlist_routes.watchlist_service,
        "remove_from_watchlist",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(watchlist_routes.activity_service, "log_event", AsyncMock())
    removed = await watchlist_routes.remove_from_watchlist(1, request_user=None, session=session)
    assert removed["success"] is True

    monkeypatch.setattr(
        watchlist_routes.watchlist_service,
        "get_alerts",
        AsyncMock(
            return_value=(
                [
                    {
                        "id": 1,
                        "watchlist_item_id": 1,
                        "alert_type": "expiration",
                        "priority": "high",
                        "title": "t",
                        "message": "m",
                        "related_patent_number": None,
                        "related_data": None,
                        "trigger_date": None,
                        "due_date": None,
                        "is_read": False,
                        "is_dismissed": False,
                        "created_at": None,
                    }
                ],
                1,
            )
        ),
    )
    alerts = await watchlist_routes.get_alerts(
        unread_only=False,
        alert_type=None,
        page=1,
        per_page=20,
        request_user=None,
        session=session,
    )
    assert alerts.total == 1

    monkeypatch.setattr(
        watchlist_routes.watchlist_service,
        "get_alert_summary",
        AsyncMock(
            return_value={
                "total_unread": 1,
                "by_type": {"expiration": 1},
                "by_priority": {"high": 1},
                "critical_count": 0,
                "high_count": 1,
            }
        ),
    )
    summary = await watchlist_routes.get_alert_summary(request_user=None, session=session)
    assert summary.total_unread == 1

    monkeypatch.setattr(
        watchlist_routes.watchlist_service,
        "mark_alert_read",
        AsyncMock(return_value=False),
    )
    with pytest.raises(HTTPException):
        await watchlist_routes.mark_alert_read(1, request_user=None, session=session)

    monkeypatch.setattr(
        watchlist_routes.watchlist_service,
        "mark_alert_read",
        AsyncMock(return_value=True),
    )
    mark = await watchlist_routes.mark_alert_read(1, request_user=None, session=session)
    assert mark["success"] is True

    monkeypatch.setattr(
        watchlist_routes.watchlist_service,
        "dismiss_alert",
        AsyncMock(return_value=True),
    )
    dismiss = await watchlist_routes.dismiss_alert(1, request_user=None, session=session)
    assert dismiss["success"] is True


@pytest.mark.asyncio
async def test_generate_alerts_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    session.commit = AsyncMock()
    monkeypatch.setattr(
        watchlist_routes.watchlist_service,
        "generate_alerts_for_all_users",
        AsyncMock(return_value=5),
    )

    response = await watchlist_routes.generate_alerts(session=session)
    assert response["alerts_created"] == 5
