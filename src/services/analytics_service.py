"""Custom analytics engine service for saved queries, metrics, and schedules."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.analytics import AnalyticsSchedule, CustomMetric, SavedQuery

logger = structlog.get_logger(__name__)

_FREQUENCY_DELTAS = {
    "hourly": timedelta(hours=1),
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
    "monthly": timedelta(days=30),
}


class AnalyticsService:
    """Manage saved queries, custom metrics, and analytics schedules."""

    # ---- Saved Queries ----

    async def list_queries(
        self, session: AsyncSession, user_id: int,
        status: str | None = None, public_only: bool = False,
    ) -> list[SavedQuery]:
        stmt = select(SavedQuery).where(SavedQuery.user_id == user_id)
        if status is not None:
            stmt = stmt.where(SavedQuery.status == status)
        if public_only:
            stmt = stmt.where(SavedQuery.is_public.is_(True))
        stmt = stmt.order_by(SavedQuery.created_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def create_query(
        self, session: AsyncSession, user_id: int,
        name: str, description: str | None = None,
        query_config: dict | None = None, filters: dict | None = None,
        is_public: bool = False,
    ) -> SavedQuery:
        query = SavedQuery(
            user_id=user_id, name=name, description=description,
            query_config=query_config or {}, filters=filters or {},
            status="saved", is_public=is_public, run_count=0)
        session.add(query)
        await session.flush()
        await session.refresh(query)
        return query

    async def update_query(
        self, session: AsyncSession, query_id: int, user_id: int,
        name: str | None = None, description: str | None = None,
        query_config: dict | None = None, filters: dict | None = None,
        status: str | None = None, is_public: bool | None = None,
    ) -> SavedQuery:
        query = await self._get_user_query(session, query_id, user_id)
        if name is not None:
            query.name = name
        if description is not None:
            query.description = description
        if query_config is not None:
            query.query_config = query_config
        if filters is not None:
            query.filters = filters
        if status is not None:
            query.status = status
        if is_public is not None:
            query.is_public = is_public
        await session.flush()
        return query

    async def delete_query(
        self, session: AsyncSession, query_id: int, user_id: int,
    ) -> bool:
        query = await self._get_user_query(session, query_id, user_id)
        await session.delete(query)
        return True

    async def run_query(
        self, session: AsyncSession, query_id: int, user_id: int,
    ) -> SavedQuery:
        query = await self._get_user_query(session, query_id, user_id)
        try:
            result = await self._execute_query(query.query_config, query.filters)
        except Exception:
            logger.exception("query.execute_failed", query_id=query_id)
            result = {"error": "Query execution failed", "patents": []}
        query.last_run_at = datetime.now(UTC)
        query.run_count = (query.run_count or 0) + 1
        query.query_config = {**query.query_config, "last_result": result}
        await session.flush()
        return query

    # ---- Custom Metrics ----

    async def list_metrics(
        self, session: AsyncSession, user_id: int,
        metric_type: str | None = None,
    ) -> list[CustomMetric]:
        stmt = select(CustomMetric).where(CustomMetric.user_id == user_id)
        if metric_type is not None:
            stmt = stmt.where(CustomMetric.metric_type == metric_type)
        stmt = stmt.order_by(CustomMetric.created_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def create_metric(
        self, session: AsyncSession, user_id: int,
        name: str, metric_type: str,
        definition: dict | None = None,
    ) -> CustomMetric:
        metric = CustomMetric(
            user_id=user_id, name=name, metric_type=metric_type,
            definition=definition or {})
        session.add(metric)
        await session.flush()
        await session.refresh(metric)
        return metric

    async def update_metric(
        self, session: AsyncSession, metric_id: int, user_id: int,
        name: str | None = None, metric_type: str | None = None,
        definition: dict | None = None,
    ) -> CustomMetric:
        metric = await self._get_user_metric(session, metric_id, user_id)
        if name is not None:
            metric.name = name
        if metric_type is not None:
            metric.metric_type = metric_type
        if definition is not None:
            metric.definition = definition
        await session.flush()
        return metric

    async def delete_metric(
        self, session: AsyncSession, metric_id: int, user_id: int,
    ) -> bool:
        metric = await self._get_user_metric(session, metric_id, user_id)
        await session.delete(metric)
        return True

    async def compute_metric(
        self, session: AsyncSession, metric_id: int, user_id: int,
    ) -> CustomMetric:
        metric = await self._get_user_metric(session, metric_id, user_id)
        result = await self._compute_metric_value(
            metric.metric_type, metric.definition)
        metric.current_value = result
        metric.last_computed_at = datetime.now(UTC)
        await session.flush()
        return metric

    # ---- Schedules ----

    async def list_schedules(
        self, session: AsyncSession, user_id: int,
        active_only: bool = False,
    ) -> list[AnalyticsSchedule]:
        stmt = select(AnalyticsSchedule).where(
            AnalyticsSchedule.user_id == user_id)
        if active_only:
            stmt = stmt.where(AnalyticsSchedule.is_active.is_(True))
        stmt = stmt.order_by(AnalyticsSchedule.next_run_at.asc().nullslast())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def create_schedule(
        self, session: AsyncSession, user_id: int,
        frequency: str = "daily",
        query_id: int | None = None, metric_id: int | None = None,
    ) -> AnalyticsSchedule:
        delta = _FREQUENCY_DELTAS.get(frequency, timedelta(days=1))
        schedule = AnalyticsSchedule(
            user_id=user_id, query_id=query_id, metric_id=metric_id,
            frequency=frequency, is_active=True,
            next_run_at=datetime.now(UTC) + delta)
        session.add(schedule)
        await session.flush()
        await session.refresh(schedule)
        return schedule

    async def update_schedule(
        self, session: AsyncSession, schedule_id: int, user_id: int,
        frequency: str | None = None, is_active: bool | None = None,
    ) -> AnalyticsSchedule:
        schedule = await self._get_user_schedule(session, schedule_id, user_id)
        if frequency is not None:
            schedule.frequency = frequency
        if is_active is not None:
            schedule.is_active = is_active
        await session.flush()
        return schedule

    async def delete_schedule(
        self, session: AsyncSession, schedule_id: int, user_id: int,
    ) -> bool:
        schedule = await self._get_user_schedule(session, schedule_id, user_id)
        await session.delete(schedule)
        return True

    async def process_due_schedules(self, session: AsyncSession) -> int:
        now = datetime.now(UTC)
        result = await session.execute(
            select(AnalyticsSchedule).where(and_(
                AnalyticsSchedule.is_active.is_(True),
                AnalyticsSchedule.next_run_at <= now)))
        schedules = list(result.scalars().all())
        processed = 0
        for sched in schedules:
            delta = _FREQUENCY_DELTAS.get(sched.frequency, timedelta(days=1))
            sched.next_run_at = now + delta
            processed += 1
            logger.info(
                "schedule.processed", schedule_id=sched.id,
                frequency=sched.frequency)
        await session.flush()
        return processed

    # ---- Stubs ----

    async def _execute_query(
        self, query_config: dict, filters: dict,
    ) -> dict:
        logger.info("query.execute", config=query_config, filters=filters)
        return {"total_results": 0, "patents": [], "executed_at": datetime.now(UTC).isoformat()}

    async def _compute_metric_value(
        self, metric_type: str, definition: dict,
    ) -> dict:
        logger.info("metric.compute", metric_type=metric_type)
        defaults: dict[str, dict] = {
            "count": {"value": 0},
            "sum": {"value": 0.0},
            "average": {"value": 0.0},
            "trend": {"values": [], "direction": "flat"},
            "distribution": {"buckets": {}},
        }
        if metric_type in defaults:
            return defaults[metric_type]
        return {"value": None}

    # ---- Internal helpers ----

    async def _get_user_query(
        self, session: AsyncSession, query_id: int, user_id: int,
    ) -> SavedQuery:
        r = await session.execute(
            select(SavedQuery).where(and_(
                SavedQuery.id == query_id,
                SavedQuery.user_id == user_id)))
        q = r.scalar_one_or_none()
        if q is None:
            raise ValueError("Saved query not found")
        return q

    async def _get_user_metric(
        self, session: AsyncSession, metric_id: int, user_id: int,
    ) -> CustomMetric:
        r = await session.execute(
            select(CustomMetric).where(and_(
                CustomMetric.id == metric_id,
                CustomMetric.user_id == user_id)))
        m = r.scalar_one_or_none()
        if m is None:
            raise ValueError("Custom metric not found")
        return m

    async def _get_user_schedule(
        self, session: AsyncSession, schedule_id: int, user_id: int,
    ) -> AnalyticsSchedule:
        r = await session.execute(
            select(AnalyticsSchedule).where(and_(
                AnalyticsSchedule.id == schedule_id,
                AnalyticsSchedule.user_id == user_id)))
        s = r.scalar_one_or_none()
        if s is None:
            raise ValueError("Analytics schedule not found")
        return s


analytics_service = AnalyticsService()
