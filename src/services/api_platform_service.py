"""API platform service for key management, webhooks, and delivery tracking."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.api_platform import (
    _TIER_RATE_LIMITS,
    ApiKey,
    WebhookDelivery,
    WebhookEndpoint,
)

logger = structlog.get_logger(__name__)

_MAX_RETRIES = 3
_RETRY_DELAY_MINUTES = 5


class ApiPlatformService:
    """Manage API keys, webhook endpoints, and delivery tracking."""

    # ---- API Keys ----

    async def list_api_keys(
        self, session: AsyncSession, user_id: int,
        active_only: bool = False,
    ) -> list[ApiKey]:
        stmt = select(ApiKey).where(ApiKey.user_id == user_id)
        if active_only:
            stmt = stmt.where(ApiKey.is_active.is_(True))
        stmt = stmt.order_by(ApiKey.created_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def create_api_key(
        self, session: AsyncSession, user_id: int,
        name: str, tier: str = "free",
        scopes: dict | None = None,
        expires_in_days: int | None = None,
    ) -> tuple[ApiKey, str]:
        raw_key = f"pi_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        rate_limit = _TIER_RATE_LIMITS.get(tier, 100)
        expires_at = None
        if expires_in_days is not None:
            expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)
        api_key = ApiKey(
            user_id=user_id, name=name, key_hash=key_hash,
            key_prefix=raw_key[:12], tier=tier,
            scopes=scopes or {}, rate_limit_per_minute=rate_limit,
            is_active=True, expires_at=expires_at)
        session.add(api_key)
        await session.flush()
        await session.refresh(api_key)
        return api_key, raw_key

    async def validate_api_key(
        self, session: AsyncSession, raw_key: str,
    ) -> ApiKey | None:
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[:12]
        r = await session.execute(
            select(ApiKey).where(and_(
                ApiKey.key_prefix == prefix,
                ApiKey.is_active.is_(True))))
        api_key = r.scalar_one_or_none()
        if api_key is None:
            return None
        if not secrets.compare_digest(api_key.key_hash, key_hash):
            return None
        if api_key.expires_at and api_key.expires_at < datetime.now(UTC):
            return None
        api_key.last_used_at = datetime.now(UTC)
        await session.flush()
        return api_key

    async def revoke_api_key(
        self, session: AsyncSession, key_id: int, user_id: int,
    ) -> bool:
        api_key = await self._get_user_key(session, key_id, user_id)
        api_key.is_active = False
        await session.flush()
        return True

    async def delete_api_key(
        self, session: AsyncSession, key_id: int, user_id: int,
    ) -> bool:
        api_key = await self._get_user_key(session, key_id, user_id)
        await session.delete(api_key)
        return True

    # ---- Webhook Endpoints ----

    async def list_webhooks(
        self, session: AsyncSession, user_id: int,
        active_only: bool = False,
    ) -> list[WebhookEndpoint]:
        stmt = select(WebhookEndpoint).where(
            WebhookEndpoint.user_id == user_id)
        if active_only:
            stmt = stmt.where(WebhookEndpoint.is_active.is_(True))
        stmt = stmt.order_by(WebhookEndpoint.created_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def create_webhook(
        self, session: AsyncSession, user_id: int,
        url: str, events: dict | None = None,
        description: str | None = None,
    ) -> WebhookEndpoint:
        secret = secrets.token_urlsafe(32)
        webhook = WebhookEndpoint(
            user_id=user_id, url=url, secret=secret,
            events=events or {}, is_active=True,
            description=description, failure_count=0)
        session.add(webhook)
        await session.flush()
        await session.refresh(webhook)
        return webhook

    async def update_webhook(
        self, session: AsyncSession, webhook_id: int, user_id: int,
        url: str | None = None, events: dict | None = None,
        description: str | None = None, is_active: bool | None = None,
    ) -> WebhookEndpoint:
        wh = await self._get_user_webhook(session, webhook_id, user_id)
        if url is not None:
            wh.url = url
        if events is not None:
            wh.events = events
        if description is not None:
            wh.description = description
        if is_active is not None:
            wh.is_active = is_active
        await session.flush()
        return wh

    async def delete_webhook(
        self, session: AsyncSession, webhook_id: int, user_id: int,
    ) -> bool:
        wh = await self._get_user_webhook(session, webhook_id, user_id)
        await session.delete(wh)
        return True

    # ---- Webhook Delivery ----

    async def trigger_webhook(
        self, session: AsyncSession, endpoint_id: int,
        event_type: str, payload: dict,
    ) -> WebhookDelivery:
        result = await self._deliver_payload(endpoint_id, event_type, payload)
        delivery = WebhookDelivery(
            endpoint_id=endpoint_id, event_type=event_type,
            payload=payload, response_status=result["status"],
            response_body=result.get("body"),
            success=result["success"], attempt_count=1)
        if not result["success"]:
            delivery.next_retry_at = (
                datetime.now(UTC) + timedelta(minutes=_RETRY_DELAY_MINUTES))
        session.add(delivery)
        await session.flush()
        await session.refresh(delivery)
        return delivery

    async def list_deliveries(
        self, session: AsyncSession, endpoint_id: int,
        limit: int = 50,
    ) -> list[WebhookDelivery]:
        result = await session.execute(
            select(WebhookDelivery)
            .where(WebhookDelivery.endpoint_id == endpoint_id)
            .order_by(WebhookDelivery.created_at.desc())
            .limit(limit))
        return list(result.scalars().all())

    async def retry_failed_deliveries(
        self, session: AsyncSession,
    ) -> int:
        now = datetime.now(UTC)
        result = await session.execute(
            select(WebhookDelivery).where(and_(
                WebhookDelivery.success.is_(False),
                WebhookDelivery.next_retry_at <= now,
                WebhookDelivery.attempt_count < _MAX_RETRIES)))
        deliveries = list(result.scalars().all())
        retried = 0
        for d in deliveries:
            r = await self._deliver_payload(
                d.endpoint_id, d.event_type, d.payload)
            d.attempt_count += 1
            d.response_status = r["status"]
            d.success = r["success"]
            if not r["success"] and d.attempt_count < _MAX_RETRIES:
                d.next_retry_at = now + timedelta(
                    minutes=_RETRY_DELAY_MINUTES * d.attempt_count)
            else:
                d.next_retry_at = None
            retried += 1
        await session.flush()
        return retried

    async def get_usage_stats(
        self, session: AsyncSession, user_id: int,
    ) -> dict:
        key_count = await session.execute(
            select(func.count(ApiKey.id)).where(
                ApiKey.user_id == user_id))
        webhook_count = await session.execute(
            select(func.count(WebhookEndpoint.id)).where(
                WebhookEndpoint.user_id == user_id))
        return {
            "api_key_count": key_count.scalar_one(),
            "webhook_count": webhook_count.scalar_one(),
        }

    # ---- Stubs ----

    async def _deliver_payload(
        self, endpoint_id: int, event_type: str, payload: dict,
    ) -> dict:
        logger.info(
            "webhook.deliver", endpoint_id=endpoint_id,
            event_type=event_type)
        return {"status": 200, "body": "OK", "success": True}

    # ---- Internal helpers ----

    async def _get_user_key(
        self, session: AsyncSession, key_id: int, user_id: int,
    ) -> ApiKey:
        r = await session.execute(
            select(ApiKey).where(and_(
                ApiKey.id == key_id,
                ApiKey.user_id == user_id)))
        k = r.scalar_one_or_none()
        if k is None:
            raise ValueError("API key not found")
        return k

    async def _get_user_webhook(
        self, session: AsyncSession, webhook_id: int, user_id: int,
    ) -> WebhookEndpoint:
        r = await session.execute(
            select(WebhookEndpoint).where(and_(
                WebhookEndpoint.id == webhook_id,
                WebhookEndpoint.user_id == user_id)))
        w = r.scalar_one_or_none()
        if w is None:
            raise ValueError("Webhook endpoint not found")
        return w


api_platform_service = ApiPlatformService()
