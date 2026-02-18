"""API routes for API platform: keys, webhooks, deliveries."""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_user
from src.api.schemas.api_platform import (
    ApiKeyCreatedResponse,
    ApiKeyCreateRequest,
    ApiKeyListResponse,
    ApiKeyResponse,
    DeliveryListResponse,
    DeliveryResponse,
    UsageStatsResponse,
    WebhookCreateRequest,
    WebhookListResponse,
    WebhookResponse,
    WebhookUpdateRequest,
)
from src.database.connection import get_session
from src.models.user import User
from src.services.activity_service import activity_service
from src.services.api_platform_service import api_platform_service

router = APIRouter()


def _key_response(k) -> ApiKeyResponse:
    return ApiKeyResponse(
        id=k.id, name=k.name, key_prefix=k.key_prefix,
        tier=k.tier, scopes=k.scopes if k.scopes else {},
        rate_limit_per_minute=k.rate_limit_per_minute,
        is_active=k.is_active,
        last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
        expires_at=k.expires_at.isoformat() if k.expires_at else None,
        created_at=k.created_at.isoformat() if k.created_at else None)


def _webhook_response(w) -> WebhookResponse:
    return WebhookResponse(
        id=w.id, url=w.url, events=w.events if w.events else {},
        is_active=w.is_active, description=w.description,
        failure_count=w.failure_count,
        last_triggered_at=w.last_triggered_at.isoformat() if w.last_triggered_at else None,
        created_at=w.created_at.isoformat() if w.created_at else None)


def _delivery_response(d) -> DeliveryResponse:
    return DeliveryResponse(
        id=d.id, endpoint_id=d.endpoint_id,
        event_type=d.event_type,
        payload=d.payload if d.payload else {},
        response_status=d.response_status,
        success=d.success, attempt_count=d.attempt_count,
        next_retry_at=d.next_retry_at.isoformat() if d.next_retry_at else None,
        created_at=d.created_at.isoformat() if d.created_at else None)


# ---- API Keys ----

@router.get("/keys", response_model=ApiKeyListResponse)
async def list_api_keys(
    active: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiKeyListResponse:
    keys = await api_platform_service.list_api_keys(
        session, user_id=current_user.id, active_only=active)
    return ApiKeyListResponse(keys=[_key_response(k) for k in keys])

@router.post(
    "/keys", response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    payload: ApiKeyCreateRequest, request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiKeyCreatedResponse:
    api_key, raw_key = await api_platform_service.create_api_key(
        session, user_id=current_user.id, name=payload.name,
        tier=payload.tier, scopes=payload.scopes,
        expires_in_days=payload.expires_in_days)
    await activity_service.log_event(
        session, event_type="api.key.created",
        user_id=current_user.id, resource_type="api_key",
        resource_id=str(api_key.id),
        event_metadata={"name": payload.name, "tier": payload.tier},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"))
    await session.commit()
    resp = _key_response(api_key)
    return ApiKeyCreatedResponse(**resp.model_dump(), raw_key=raw_key)

@router.post("/keys/{key_id}/revoke")
async def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    try:
        await api_platform_service.revoke_api_key(
            session, key_id=key_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return {"success": True}

@router.delete("/keys/{key_id}")
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    try:
        await api_platform_service.delete_api_key(
            session, key_id=key_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return {"success": True}

# ---- Webhooks ----

@router.get("/webhooks", response_model=WebhookListResponse)
async def list_webhooks(
    active: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WebhookListResponse:
    webhooks = await api_platform_service.list_webhooks(
        session, user_id=current_user.id, active_only=active)
    return WebhookListResponse(
        webhooks=[_webhook_response(w) for w in webhooks])

@router.post(
    "/webhooks", response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_webhook(
    payload: WebhookCreateRequest, request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WebhookResponse:
    wh = await api_platform_service.create_webhook(
        session, user_id=current_user.id, url=payload.url,
        events=payload.events, description=payload.description)
    await activity_service.log_event(
        session, event_type="api.webhook.created",
        user_id=current_user.id, resource_type="webhook",
        resource_id=str(wh.id),
        event_metadata={"url": payload.url},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"))
    await session.commit()
    return _webhook_response(wh)

@router.patch("/webhooks/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: int, payload: WebhookUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WebhookResponse:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    try:
        wh = await api_platform_service.update_webhook(
            session, webhook_id=webhook_id,
            user_id=current_user.id, **updates)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return _webhook_response(wh)

@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    try:
        await api_platform_service.delete_webhook(
            session, webhook_id=webhook_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return {"success": True}

# ---- Deliveries ----

@router.get(
    "/webhooks/{webhook_id}/deliveries",
    response_model=DeliveryListResponse,
)
async def list_deliveries(
    webhook_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DeliveryListResponse:
    deliveries = await api_platform_service.list_deliveries(
        session, endpoint_id=webhook_id, limit=limit)
    return DeliveryListResponse(
        deliveries=[_delivery_response(d) for d in deliveries])

# ---- Usage Stats ----

@router.get("/usage", response_model=UsageStatsResponse)
async def get_usage_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UsageStatsResponse:
    stats = await api_platform_service.get_usage_stats(
        session, user_id=current_user.id)
    return UsageStatsResponse(**stats)
