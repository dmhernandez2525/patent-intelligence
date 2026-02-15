"""API routes for alert channel and schedule management."""

import hmac

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_user
from src.api.schemas.alert_channel import (
    ChannelCreateRequest,
    ChannelListResponse,
    ChannelResponse,
    ChannelUpdateRequest,
    DeliveryResponse,
    DispatchResponse,
    ScheduleCreateRequest,
    ScheduleListResponse,
    ScheduleResponse,
    ScheduleUpdateRequest,
)
from src.config import settings
from src.database.connection import get_session
from src.models.user import User
from src.services.activity_service import activity_service
from src.services.alert_notifier_service import alert_notifier_service

router = APIRouter()


async def _verify_admin_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> None:
    """Verify the admin API key for protected endpoints."""
    if not settings.admin_api_key:
        raise HTTPException(status_code=503, detail="Admin API key not configured")
    if not hmac.compare_digest(x_api_key, settings.admin_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")


def _channel_response(ch) -> ChannelResponse:
    return ChannelResponse(
        id=ch.id, channel_type=ch.channel_type, name=ch.name,
        config=ch.config, is_active=ch.is_active,
        created_at=ch.created_at.isoformat() if ch.created_at else None,
    )


def _schedule_response(s) -> ScheduleResponse:
    return ScheduleResponse(
        id=s.id, channel_id=s.channel_id, frequency=s.frequency,
        delivery_hour=s.delivery_hour, delivery_day=s.delivery_day,
        alert_types=s.alert_types, min_priority=s.min_priority,
        is_active=s.is_active,
    )


def _delivery_response(d) -> DeliveryResponse:
    return DeliveryResponse(
        id=d.id, alert_id=d.alert_id, channel_id=d.channel_id,
        status=d.status, attempt_count=d.attempt_count,
        last_error=d.last_error,
        sent_at=d.sent_at.isoformat() if d.sent_at else None,
    )


# ---- Notification Channels ----

@router.get("/channels", response_model=ChannelListResponse)
async def list_channels(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChannelListResponse:
    channels = await alert_notifier_service.list_channels(
        session, user_id=current_user.id,
    )
    return ChannelListResponse(
        channels=[_channel_response(ch) for ch in channels],
    )


@router.post(
    "/channels", response_model=ChannelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_channel(
    payload: ChannelCreateRequest, request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChannelResponse:
    try:
        ch = await alert_notifier_service.create_channel(
            session, user_id=current_user.id,
            channel_type=payload.channel_type,
            name=payload.name, config=payload.config,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await activity_service.log_event(
        session, event_type="alert.channel.created",
        user_id=current_user.id, resource_type="notification_channel",
        resource_id=str(ch.id),
        event_metadata={
            "channel_type": payload.channel_type, "name": payload.name,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    return _channel_response(ch)


@router.patch("/channels/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: int, payload: ChannelUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChannelResponse:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    try:
        ch = await alert_notifier_service.update_channel(
            session, channel_id=channel_id,
            user_id=current_user.id, **updates,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    await activity_service.log_event(
        session, event_type="alert.channel.updated",
        user_id=current_user.id, resource_type="notification_channel",
        resource_id=str(channel_id),
        event_metadata={"fields": sorted(updates.keys())},
    )
    await session.commit()
    return _channel_response(ch)


@router.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    try:
        await alert_notifier_service.delete_channel(
            session, channel_id=channel_id, user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    await activity_service.log_event(
        session, event_type="alert.channel.deleted",
        user_id=current_user.id, resource_type="notification_channel",
        resource_id=str(channel_id),
    )
    await session.commit()
    return {"success": True}


# ---- Alert Schedules ----

@router.get("/schedules", response_model=ScheduleListResponse)
async def list_schedules(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ScheduleListResponse:
    schedules = await alert_notifier_service.get_schedules(
        session, user_id=current_user.id,
    )
    return ScheduleListResponse(
        schedules=[_schedule_response(s) for s in schedules],
    )


@router.post(
    "/schedules", response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule(
    payload: ScheduleCreateRequest, request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ScheduleResponse:
    try:
        s = await alert_notifier_service.create_schedule(
            session, user_id=current_user.id,
            channel_id=payload.channel_id, frequency=payload.frequency,
            delivery_hour=payload.delivery_hour,
            delivery_day=payload.delivery_day,
            alert_types=payload.alert_types,
            min_priority=payload.min_priority,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await activity_service.log_event(
        session, event_type="alert.schedule.created",
        user_id=current_user.id, resource_type="alert_schedule",
        resource_id=str(s.id), event_metadata={
            "channel_id": payload.channel_id,
            "frequency": payload.frequency,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    return _schedule_response(s)


@router.patch("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int, payload: ScheduleUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ScheduleResponse:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    try:
        s = await alert_notifier_service.update_schedule(
            session, schedule_id=schedule_id,
            user_id=current_user.id, **updates,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    await activity_service.log_event(
        session, event_type="alert.schedule.updated",
        user_id=current_user.id, resource_type="alert_schedule",
        resource_id=str(schedule_id),
        event_metadata={"fields": sorted(updates.keys())},
    )
    await session.commit()
    return _schedule_response(s)


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    try:
        await alert_notifier_service.delete_schedule(
            session, schedule_id=schedule_id, user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    await activity_service.log_event(
        session, event_type="alert.schedule.deleted",
        user_id=current_user.id, resource_type="alert_schedule",
        resource_id=str(schedule_id),
    )
    await session.commit()
    return {"success": True}


# ---- Alert Dispatch & Delivery Processing ----
@router.post("/alerts/{alert_id}/dispatch", response_model=DispatchResponse)
async def dispatch_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DispatchResponse:
    try:
        deliveries = await alert_notifier_service.dispatch_alert(
            session, alert_id=alert_id, user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    await activity_service.log_event(
        session, event_type="alert.dispatched",
        user_id=current_user.id, resource_type="alert",
        resource_id=str(alert_id),
        event_metadata={"total_dispatched": len(deliveries)},
    )
    await session.commit()
    return DispatchResponse(
        deliveries=[_delivery_response(d) for d in deliveries],
        total_dispatched=len(deliveries),
    )


@router.post(
    "/process-deliveries", dependencies=[Depends(_verify_admin_api_key)],
)
async def process_deliveries(
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    processed = await alert_notifier_service.process_pending_deliveries(session)
    await session.commit()
    return {"processed": processed}
