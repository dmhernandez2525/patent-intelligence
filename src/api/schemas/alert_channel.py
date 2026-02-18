"""Schemas for alert notification channels and delivery."""

from pydantic import BaseModel, Field


class ChannelCreateRequest(BaseModel):
    """Request payload to create a notification channel."""

    channel_type: str = Field(
        pattern="^(email|webhook|slack|teams)$"
    )
    name: str = Field(min_length=1, max_length=100)
    config: dict = Field(default_factory=dict)


class ChannelUpdateRequest(BaseModel):
    """Request payload to update a notification channel."""

    name: str | None = None
    config: dict | None = None
    is_active: bool | None = None


class ChannelResponse(BaseModel):
    """Notification channel response model."""

    id: int
    channel_type: str
    name: str
    config: dict
    is_active: bool
    created_at: str | None


class ChannelListResponse(BaseModel):
    """Response for listing notification channels."""

    channels: list[ChannelResponse]


class ScheduleCreateRequest(BaseModel):
    """Request payload to create an alert schedule."""

    channel_id: int
    frequency: str = Field(
        pattern="^(immediate|daily|weekly)$",
        default="immediate",
    )
    delivery_hour: int = Field(default=9, ge=0, le=23)
    delivery_day: int = Field(default=1, ge=0, le=6)
    alert_types: list[str] = Field(default_factory=list)
    min_priority: str = Field(
        default="low",
        pattern="^(low|medium|high|critical)$",
    )


class ScheduleUpdateRequest(BaseModel):
    """Request payload to update an alert schedule."""

    frequency: str | None = None
    delivery_hour: int | None = Field(
        default=None, ge=0, le=23
    )
    delivery_day: int | None = Field(
        default=None, ge=0, le=6
    )
    alert_types: list[str] | None = None
    min_priority: str | None = None
    is_active: bool | None = None


class ScheduleResponse(BaseModel):
    """Alert schedule response model."""

    id: int
    channel_id: int
    frequency: str
    delivery_hour: int
    delivery_day: int
    alert_types: list[str]
    min_priority: str
    is_active: bool


class ScheduleListResponse(BaseModel):
    """Response for listing alert schedules."""

    schedules: list[ScheduleResponse]


class DeliveryResponse(BaseModel):
    """Alert delivery tracking response model."""

    id: int
    alert_id: int
    channel_id: int
    status: str
    attempt_count: int
    last_error: str | None
    sent_at: str | None


class DispatchResponse(BaseModel):
    """Response after dispatching an alert to channels."""

    deliveries: list[DeliveryResponse]
    total_dispatched: int
