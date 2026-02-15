"""API routes for watchlist and alerts management."""

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import RequestUserContext, get_optional_request_user, resolve_user_id
from src.api.schemas.watchlist import (
    AlertListResponse,
    AlertResponse,
    AlertSummaryResponse,
    WatchlistAddRequest,
    WatchlistItemResponse,
    WatchlistResponse,
    WatchlistUpdateRequest,
)
from src.config import settings
from src.database.connection import get_session
from src.services.activity_service import activity_service
from src.services.watchlist_service import watchlist_service
from src.utils.logger import logger


async def verify_admin_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> None:
    """Verify the admin API key for protected endpoints."""
    if not settings.admin_api_key:
        raise HTTPException(
            status_code=503,
            detail="Admin API key not configured",
        )
    if not hmac.compare_digest(x_api_key, settings.admin_api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )


router = APIRouter()


@router.get("", response_model=WatchlistResponse)
async def get_watchlist(
    item_type: str | None = Query(None, pattern="^(patent|cpc_code|assignee|inventor)$"),
    include_inactive: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    request_user: RequestUserContext | None = Depends(get_optional_request_user),
    session: AsyncSession = Depends(get_session),
) -> WatchlistResponse:
    """Get user's watchlist items."""
    user_id = resolve_user_id(request_user)
    logger.info("watchlist.get", user_id=user_id, item_type=item_type, page=page)

    items, total = await watchlist_service.get_watchlist(
        session,
        user_id=user_id,
        item_type=item_type,
        include_inactive=include_inactive,
        page=page,
        per_page=per_page,
    )

    return WatchlistResponse(
        items=[WatchlistItemResponse(**item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("", response_model=WatchlistItemResponse)
async def add_to_watchlist(
    payload: WatchlistAddRequest,
    request: Request,
    request_user: RequestUserContext | None = Depends(get_optional_request_user),
    session: AsyncSession = Depends(get_session),
) -> WatchlistItemResponse:
    """Add an item to the watchlist."""
    user_id = resolve_user_id(request_user)
    logger.info(
        "watchlist.add", user_id=user_id, item_type=payload.item_type, item_value=payload.item_value
    )

    try:
        item = await watchlist_service.add_to_watchlist(
            session,
            item_type=payload.item_type,
            item_value=payload.item_value,
            user_id=user_id,
            name=payload.name,
            notes=payload.notes,
            notify_expiration=payload.notify_expiration,
            notify_maintenance=payload.notify_maintenance,
            notify_citations=payload.notify_citations,
            notify_new_patents=payload.notify_new_patents,
            expiration_lead_days=payload.expiration_lead_days,
            maintenance_lead_days=payload.maintenance_lead_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("watchlist.add_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to add to watchlist")

    await activity_service.log_event(
        session,
        event_type="watchlist.added",
        user_id=request_user.user_id if request_user else None,
        resource_type="watchlist_item",
        resource_id=str(item["id"]),
        event_metadata={"item_type": payload.item_type, "item_value": payload.item_value},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    return WatchlistItemResponse(**item)


@router.patch("/{item_id}", response_model=WatchlistItemResponse)
async def update_watchlist_item(
    item_id: int,
    payload: WatchlistUpdateRequest,
    request_user: RequestUserContext | None = Depends(get_optional_request_user),
    session: AsyncSession = Depends(get_session),
) -> WatchlistItemResponse:
    """Update a watchlist item."""
    user_id = resolve_user_id(request_user)
    logger.info("watchlist.update", user_id=user_id, item_id=item_id)

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    item = await watchlist_service.update_watchlist_item(
        session,
        item_id=item_id,
        user_id=user_id,
        **updates,
    )

    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    await activity_service.log_event(
        session,
        event_type="watchlist.updated",
        user_id=request_user.user_id if request_user else None,
        resource_type="watchlist_item",
        resource_id=str(item_id),
        event_metadata={"fields": sorted(updates.keys())},
    )
    await session.commit()
    return WatchlistItemResponse(**item)


@router.delete("/{item_id}")
async def remove_from_watchlist(
    item_id: int,
    request_user: RequestUserContext | None = Depends(get_optional_request_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str | bool]:
    """Remove an item from the watchlist."""
    user_id = resolve_user_id(request_user)
    logger.info("watchlist.remove", user_id=user_id, item_id=item_id)

    deleted = await watchlist_service.remove_from_watchlist(
        session, item_id=item_id, user_id=user_id
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    await activity_service.log_event(
        session,
        event_type="watchlist.removed",
        user_id=request_user.user_id if request_user else None,
        resource_type="watchlist_item",
        resource_id=str(item_id),
    )
    await session.commit()
    return {"success": True, "message": "Item removed from watchlist"}


@router.get("/alerts", response_model=AlertListResponse)
async def get_alerts(
    unread_only: bool = Query(False),
    alert_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    request_user: RequestUserContext | None = Depends(get_optional_request_user),
    session: AsyncSession = Depends(get_session),
) -> AlertListResponse:
    """Get alerts for watched items."""
    user_id = resolve_user_id(request_user)
    logger.info("watchlist.alerts", user_id=user_id, unread_only=unread_only, alert_type=alert_type)

    alerts, total = await watchlist_service.get_alerts(
        session,
        user_id=user_id,
        unread_only=unread_only,
        alert_type=alert_type,
        page=page,
        per_page=per_page,
    )

    return AlertListResponse(
        alerts=[AlertResponse(**alert) for alert in alerts],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/alerts/summary", response_model=AlertSummaryResponse)
async def get_alert_summary(
    request_user: RequestUserContext | None = Depends(get_optional_request_user),
    session: AsyncSession = Depends(get_session),
) -> AlertSummaryResponse:
    """Get summary of alerts for dashboard."""
    user_id = resolve_user_id(request_user)
    logger.info("watchlist.alert_summary", user_id=user_id)

    summary = await watchlist_service.get_alert_summary(session, user_id=user_id)
    return AlertSummaryResponse(**summary)


@router.post("/alerts/{alert_id}/read")
async def mark_alert_read(
    alert_id: int,
    request_user: RequestUserContext | None = Depends(get_optional_request_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    """Mark an alert as read."""
    user_id = resolve_user_id(request_user)
    success = await watchlist_service.mark_alert_read(session, alert_id=alert_id, user_id=user_id)

    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")

    await session.commit()
    return {"success": True}


@router.post("/alerts/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: int,
    request_user: RequestUserContext | None = Depends(get_optional_request_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    """Dismiss an alert."""
    user_id = resolve_user_id(request_user)
    success = await watchlist_service.dismiss_alert(session, alert_id=alert_id, user_id=user_id)

    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")

    await session.commit()
    return {"success": True}


@router.post("/generate-alerts", dependencies=[Depends(verify_admin_api_key)])
async def generate_alerts(
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool | int]:
    """Generate alerts for watchlist items (admin/cron endpoint)."""
    logger.info("watchlist.generate_alerts")
    count = await watchlist_service.generate_alerts_for_all_users(session)
    await session.commit()
    return {"success": True, "alerts_created": count}
