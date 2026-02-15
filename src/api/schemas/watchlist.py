"""Watchlist and alert request/response schemas."""

from pydantic import BaseModel, Field


class WatchlistAddRequest(BaseModel):
    """Request to add item to watchlist."""

    item_type: str = Field(..., pattern="^(patent|cpc_code|assignee|inventor)$")
    item_value: str = Field(..., min_length=1, max_length=255)
    name: str | None = Field(None, max_length=255)
    notes: str | None = Field(None, max_length=1000)
    notify_expiration: bool = True
    notify_maintenance: bool = True
    notify_citations: bool = False
    notify_new_patents: bool = False
    expiration_lead_days: int = Field(default=90, ge=1, le=365)
    maintenance_lead_days: int = Field(default=30, ge=1, le=180)


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
