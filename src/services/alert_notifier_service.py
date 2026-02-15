"""Alert notification delivery and channel management service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.alert_channel import (
    AlertDelivery,
    AlertSchedule,
    NotificationChannel,
)
from src.models.watchlist import Alert

logger = structlog.get_logger(__name__)
MAX_RETRIES = 3
RETRY_DELAY_MINUTES = 5


class AlertNotifierService:
    """Orchestrate alert delivery through notification channels."""

    async def list_channels(
        self, session: AsyncSession, user_id: int,
    ) -> list[NotificationChannel]:
        result = await session.execute(
            select(NotificationChannel)
            .where(NotificationChannel.user_id == user_id)
            .order_by(NotificationChannel.created_at.desc()))
        return list(result.scalars().all())

    async def create_channel(
        self, session: AsyncSession, user_id: int,
        channel_type: str, name: str,
        config: dict | None = None,
    ) -> NotificationChannel:
        channel = NotificationChannel(
            user_id=user_id, channel_type=channel_type,
            name=name, config=config or {}, is_active=True)
        session.add(channel)
        await session.flush()
        await session.refresh(channel)
        return channel

    async def update_channel(
        self, session: AsyncSession, channel_id: int,
        user_id: int, name: str | None = None,
        config: dict | None = None,
        is_active: bool | None = None,
    ) -> NotificationChannel:
        channel = await self._get_user_channel(
            session, channel_id, user_id)
        if name is not None:
            channel.name = name
        if config is not None:
            channel.config = config
        if is_active is not None:
            channel.is_active = is_active
        await session.flush()
        await session.refresh(channel)
        return channel

    async def delete_channel(
        self, session: AsyncSession, channel_id: int, user_id: int,
    ) -> bool:
        ch = await self._get_user_channel(session, channel_id, user_id)
        await session.delete(ch)
        return True

    async def get_schedules(
        self, session: AsyncSession, user_id: int,
    ) -> list[AlertSchedule]:
        result = await session.execute(
            select(AlertSchedule)
            .where(AlertSchedule.user_id == user_id)
            .order_by(AlertSchedule.id))
        return list(result.scalars().all())

    async def create_schedule(
        self, session: AsyncSession, user_id: int,
        channel_id: int, frequency: str = "immediate",
        delivery_hour: int = 9, delivery_day: int = 1,
        alert_types: list[str] | None = None,
        min_priority: str = "low",
    ) -> AlertSchedule:
        await self._get_user_channel(
            session, channel_id, user_id)
        schedule = AlertSchedule(
            user_id=user_id, channel_id=channel_id,
            frequency=frequency,
            delivery_hour=delivery_hour,
            delivery_day=delivery_day,
            alert_types=alert_types or [],
            min_priority=min_priority, is_active=True)
        session.add(schedule)
        await session.flush()
        await session.refresh(schedule)
        return schedule

    async def update_schedule(
        self, session: AsyncSession, schedule_id: int,
        user_id: int, frequency: str | None = None,
        delivery_hour: int | None = None,
        delivery_day: int | None = None,
        alert_types: list[str] | None = None,
        min_priority: str | None = None,
        is_active: bool | None = None,
    ) -> AlertSchedule:
        schedule = await self._get_user_schedule(
            session, schedule_id, user_id)
        if frequency is not None:
            schedule.frequency = frequency
        if delivery_hour is not None:
            schedule.delivery_hour = delivery_hour
        if delivery_day is not None:
            schedule.delivery_day = delivery_day
        if alert_types is not None:
            schedule.alert_types = alert_types
        if min_priority is not None:
            schedule.min_priority = min_priority
        if is_active is not None:
            schedule.is_active = is_active
        await session.flush()
        await session.refresh(schedule)
        return schedule

    async def delete_schedule(
        self, session: AsyncSession, schedule_id: int, user_id: int,
    ) -> bool:
        s = await self._get_user_schedule(session, schedule_id, user_id)
        await session.delete(s)
        return True

    async def dispatch_alert(
        self, session: AsyncSession,
        alert_id: int, user_id: int,
    ) -> list[AlertDelivery]:
        alert = await self._get_alert(session, alert_id)
        channels = await session.execute(
            select(NotificationChannel).where(and_(
                NotificationChannel.user_id == user_id,
                NotificationChannel.is_active.is_(True))))
        active = list(channels.scalars().all())
        if not active:
            logger.info("no_active_channels",
                        user_id=user_id, alert_id=alert_id)
            return []
        deliveries: list[AlertDelivery] = []
        for ch in active:
            d = AlertDelivery(
                alert_id=alert.id, channel_id=ch.id,
                status="pending", attempt_count=0,
                max_retries=MAX_RETRIES)
            session.add(d)
            deliveries.append(d)
        await session.flush()
        for d in deliveries:
            await session.refresh(d)
        return deliveries

    async def process_pending_deliveries(
        self, session: AsyncSession, batch_size: int = 50,
    ) -> int:
        now = datetime.now(UTC)
        result = await session.execute(
            select(AlertDelivery).where(and_(
                AlertDelivery.status.in_(
                    ["pending", "retrying"]),
                AlertDelivery.attempt_count < MAX_RETRIES,
                (AlertDelivery.next_retry_at.is_(None)
                 | (AlertDelivery.next_retry_at <= now)),
            )).limit(batch_size))
        deliveries = list(result.scalars().all())
        processed = 0
        for delivery in deliveries:
            channel = await session.get(
                NotificationChannel, delivery.channel_id)
            if channel is None or not channel.is_active:
                self._mark_failed(
                    delivery, "Channel inactive or deleted")
                processed += 1
                continue
            alert = await session.get(
                Alert, delivery.alert_id)
            if alert is None:
                self._mark_failed(delivery, "Alert not found")
                processed += 1
                continue
            delivery.attempt_count += 1
            ok = await self._send_to_channel(channel, alert)
            if ok:
                self._mark_delivered(delivery)
            else:
                msg = f"Failed attempt {delivery.attempt_count}"
                self._mark_failed(delivery, msg)
            processed += 1
        await session.flush()
        logger.info("deliveries_processed",
                     count=processed, batch_size=batch_size)
        return processed

    async def _send_to_channel(
        self, channel: NotificationChannel, alert: Alert,
    ) -> bool:
        senders = {
            "email": self._send_email,
            "webhook": self._send_webhook,
            "slack": self._send_slack,
            "teams": self._send_teams,
        }
        sender = senders.get(channel.channel_type)
        if sender is None:
            logger.warning("unknown_channel_type",
                           channel_type=channel.channel_type)
            return False
        return await sender(channel.config, alert)

    async def _send_email(self, cfg: dict, alert: Alert) -> bool:
        logger.info("email_send_attempt",
                     recipient=cfg.get("email"), alert_id=alert.id)
        return True

    async def _send_webhook(self, cfg: dict, alert: Alert) -> bool:
        # Production: use httpx.AsyncClient to POST payload
        logger.info("webhook_send_attempt",
                     url=cfg.get("url"), alert_id=alert.id)
        return True

    async def _send_slack(self, cfg: dict, alert: Alert) -> bool:
        logger.info("slack_send_attempt",
                     channel=cfg.get("channel"), alert_id=alert.id)
        return True

    async def _send_teams(self, cfg: dict, alert: Alert) -> bool:
        logger.info("teams_send_attempt",
                     webhook=cfg.get("webhook_url"), alert_id=alert.id)
        return True

    def _mark_delivered(self, delivery: AlertDelivery) -> None:
        delivery.status = "sent"
        delivery.sent_at = datetime.now(UTC)
        delivery.last_error = None

    def _mark_failed(self, delivery: AlertDelivery, error: str) -> None:
        delivery.last_error = error
        if delivery.attempt_count >= delivery.max_retries:
            delivery.status = "failed"
            return
        delivery.status = "retrying"
        delay = RETRY_DELAY_MINUTES * delivery.attempt_count
        delivery.next_retry_at = (
            datetime.now(UTC) + timedelta(minutes=delay))

    async def _get_user_channel(
        self, session: AsyncSession, channel_id: int, user_id: int,
    ) -> NotificationChannel:
        r = await session.execute(
            select(NotificationChannel).where(and_(
                NotificationChannel.id == channel_id,
                NotificationChannel.user_id == user_id)))
        ch = r.scalar_one_or_none()
        if ch is None:
            raise ValueError("Notification channel not found")
        return ch

    async def _get_user_schedule(
        self, session: AsyncSession, schedule_id: int, user_id: int,
    ) -> AlertSchedule:
        r = await session.execute(
            select(AlertSchedule).where(and_(
                AlertSchedule.id == schedule_id,
                AlertSchedule.user_id == user_id)))
        sched = r.scalar_one_or_none()
        if sched is None:
            raise ValueError("Alert schedule not found")
        return sched

    async def _get_alert(self, session: AsyncSession, alert_id: int) -> Alert:
        r = await session.execute(
            select(Alert).where(Alert.id == alert_id))
        alert = r.scalar_one_or_none()
        if alert is None:
            raise ValueError("Alert not found")
        return alert


alert_notifier_service = AlertNotifierService()
