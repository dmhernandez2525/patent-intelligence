"""API routes for watchlist and alerts management."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session
from src.services.watchlist_service import watchlist_service
from src.utils.logger import logger

router = APIRouter()


class WatchlistAddRequest(BaseModel):
    """Request to add item to watchlist."""

    item_type: str = Field(..., pattern="^(patent|cpc_code|assignee|inventor)$")
    item_value: str = Field(..., min_length=1, max_length=255)
    name: str | None = Field(None, max_length=255)
    notes: str | None = Field(None, max_length=1000)
    notify_expiration: bool = True
    notify_maintenance: bool = True
    expiration_lead_days: int = Field(default=90, ge=1, le=365)


class WatchlistUpdateRequest(BaseModel):
    """Request to update watchlist item."""

    name: str | None = None
    notes: str | None = None
    notify_expiration: bool | None = None
    notify_maintenance: bool | None = None
    notify_citations: bool | None = None
    notify_new_patents: bool | None = None
    expiration_lead_days: int | None = Field(None, ge=1, le=365)
    maintenance_lead_days: int | None = Field(None, ge=1, le=180)
    is_active: bool | None = None


class WatchlistItemResponse(BaseModel):
    """Response for a watchlist item."""

    id: int
    item_type: str
    item_value: str
    patent_id: int | None
    name: str | None
    notes: str | None
    notify_expiration: bool
    notify_maintenance: bool
    notify_citations: bool
    notify_new_patents: bool
    expiration_lead_days: int
    maintenance_lead_days: int
    is_active: bool
    unread_alerts: int
    created_at: str | None


class WatchlistResponse(BaseModel):
    """Response for watchlist listing."""

    items: list[WatchlistItemResponse]
    total: int
    page: int
    per_page: int


class AlertResponse(BaseModel):
    """Response for an alert."""

    id: int
    watchlist_item_id: int
    alert_type: str
    priority: str
    title: str
    message: str
    related_patent_number: str | None
    related_data: dict | None
    trigger_date: str | None
    due_date: str | None
    is_read: bool
    is_dismissed: bool
    created_at: str | None


class AlertListResponse(BaseModel):
    """Response for alert listing."""

    alerts: list[AlertResponse]
    total: int
    page: int
    per_page: int


class AlertSummaryResponse(BaseModel):
    """Response for alert summary."""

    total_unread: int
    by_type: dict[str, int]
    by_priority: dict[str, int]
    critical_count: int
    high_count: int


@router.get("", response_model=WatchlistResponse)
async def get_watchlist(
    item_type: str | None = Query(None, pattern="^(patent|cpc_code|assignee|inventor)$"),
    include_inactive: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> WatchlistResponse:
    """Get user's watchlist items."""
    logger.info("watchlist.get", item_type=item_type, page=page)

    items, total = await watchlist_service.get_watchlist(
        session,
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
    request: WatchlistAddRequest,
    session: AsyncSession = Depends(get_session),
) -> WatchlistItemResponse:
    """Add an item to the watchlist."""
    logger.info(
        "watchlist.add",
        item_type=request.item_type,
        item_value=request.item_value,
    )

    try:
        item = await watchlist_service.add_to_watchlist(
            session,
            item_type=request.item_type,
            item_value=request.item_value,
            name=request.name,
            notes=request.notes,
            notify_expiration=request.notify_expiration,
            notify_maintenance=request.notify_maintenance,
            expiration_lead_days=request.expiration_lead_days,
        )
        await session.commit()
        return WatchlistItemResponse(**item)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("watchlist.add_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to add to watchlist")


@router.patch("/{item_id}", response_model=WatchlistItemResponse)
async def update_watchlist_item(
    item_id: int,
    request: WatchlistUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> WatchlistItemResponse:
    """Update a watchlist item."""
    logger.info("watchlist.update", item_id=item_id)

    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    item = await watchlist_service.update_watchlist_item(session, item_id=item_id, **updates)

    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    await session.commit()
    return WatchlistItemResponse(**item)


@router.delete("/{item_id}")
async def remove_from_watchlist(
    item_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Remove an item from the watchlist."""
    logger.info("watchlist.remove", item_id=item_id)

    deleted = await watchlist_service.remove_from_watchlist(session, item_id=item_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    await session.commit()
    return {"success": True, "message": "Item removed from watchlist"}


@router.get("/alerts", response_model=AlertListResponse)
async def get_alerts(
    unread_only: bool = Query(False),
    alert_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> AlertListResponse:
    """Get alerts for watched items."""
    logger.info("watchlist.alerts", unread_only=unread_only, alert_type=alert_type)

    alerts, total = await watchlist_service.get_alerts(
        session,
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
    session: AsyncSession = Depends(get_session),
) -> AlertSummaryResponse:
    """Get summary of alerts for dashboard."""
    logger.info("watchlist.alert_summary")

    summary = await watchlist_service.get_alert_summary(session)
    return AlertSummaryResponse(**summary)


@router.post("/alerts/{alert_id}/read")
async def mark_alert_read(
    alert_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Mark an alert as read."""
    success = await watchlist_service.mark_alert_read(session, alert_id=alert_id)

    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")

    await session.commit()
    return {"success": True}


@router.post("/alerts/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Dismiss an alert."""
    success = await watchlist_service.dismiss_alert(session, alert_id=alert_id)

    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")

    await session.commit()
    return {"success": True}


@router.post("/generate-alerts")
async def generate_alerts(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Generate alerts for watchlist items (admin/cron endpoint)."""
    logger.info("watchlist.generate_alerts")

    count = await watchlist_service.generate_alerts(session)
    await session.commit()

    return {"success": True, "alerts_created": count}
