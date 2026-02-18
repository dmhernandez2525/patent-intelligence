"""Competitive intelligence and portfolio analysis service."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.competitive import (
    AcquisitionTarget,
    CompetitorMonitor,
    PortfolioComparison,
)

logger = structlog.get_logger(__name__)


class CompetitiveService:
    """Manage competitor monitoring, portfolio comparisons, and M&A targets."""

    # ---- Competitor Monitors ----

    async def list_monitors(
        self, session: AsyncSession, user_id: int,
        status: str | None = None,
    ) -> list[CompetitorMonitor]:
        stmt = select(CompetitorMonitor).where(
            CompetitorMonitor.user_id == user_id)
        if status is not None:
            stmt = stmt.where(CompetitorMonitor.status == status)
        stmt = stmt.order_by(CompetitorMonitor.created_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def create_monitor(
        self, session: AsyncSession, user_id: int,
        competitor_name: str, aliases: list[str] | None = None,
        cpc_focus: list[str] | None = None, notes: str | None = None,
    ) -> CompetitorMonitor:
        monitor = CompetitorMonitor(
            user_id=user_id, competitor_name=competitor_name,
            aliases=aliases or [], cpc_focus=cpc_focus or [],
            status="active", notes=notes)
        session.add(monitor)
        await session.flush()
        await session.refresh(monitor)
        return monitor

    async def update_monitor(
        self, session: AsyncSession, monitor_id: int, user_id: int,
        competitor_name: str | None = None, aliases: list[str] | None = None,
        cpc_focus: list[str] | None = None, notes: str | None = None,
        status: str | None = None,
    ) -> CompetitorMonitor:
        monitor = await self._get_user_monitor(session, monitor_id, user_id)
        if competitor_name is not None:
            monitor.competitor_name = competitor_name
        if aliases is not None:
            monitor.aliases = aliases
        if cpc_focus is not None:
            monitor.cpc_focus = cpc_focus
        if notes is not None:
            monitor.notes = notes
        if status is not None:
            monitor.status = status
        await session.flush()
        return monitor

    async def delete_monitor(
        self, session: AsyncSession, monitor_id: int, user_id: int,
    ) -> bool:
        monitor = await self._get_user_monitor(session, monitor_id, user_id)
        await session.delete(monitor)
        return True

    # ---- Portfolio Comparisons ----

    async def list_comparisons(
        self, session: AsyncSession, user_id: int,
    ) -> list[PortfolioComparison]:
        result = await session.execute(
            select(PortfolioComparison)
            .where(PortfolioComparison.user_id == user_id)
            .order_by(PortfolioComparison.created_at.desc()))
        return list(result.scalars().all())

    async def create_comparison(
        self, session: AsyncSession, user_id: int,
        entity_a: str, entity_b: str,
    ) -> PortfolioComparison:
        comp = PortfolioComparison(
            user_id=user_id, entity_a=entity_a,
            entity_b=entity_b, status="pending",
            comparison_data={})
        session.add(comp)
        await session.flush()
        await session.refresh(comp)
        return comp

    async def compute_comparison(
        self, session: AsyncSession, comparison_id: int, user_id: int,
    ) -> PortfolioComparison:
        comp = await self._get_user_comparison(session, comparison_id, user_id)
        comp.status = "computing"
        await session.flush()
        try:
            result = await self._run_comparison(comp.entity_a, comp.entity_b)
            comp.status = "completed"
            comp.comparison_data = result["comparison_data"]
            comp.overlap_score = result["overlap_score"]
            comp.summary = result["summary"]
            comp.computed_at = datetime.now(UTC)
        except Exception as exc:
            comp.status = "failed"
            comp.error_message = str(exc)
            logger.error("comparison.failed", error=str(exc))
        await session.flush()
        return comp

    async def delete_comparison(
        self, session: AsyncSession, comparison_id: int, user_id: int,
    ) -> bool:
        comp = await self._get_user_comparison(session, comparison_id, user_id)
        await session.delete(comp)
        return True

    # ---- Acquisition Targets ----

    async def list_targets(
        self, session: AsyncSession, user_id: int,
        starred_only: bool = False,
    ) -> list[AcquisitionTarget]:
        stmt = select(AcquisitionTarget).where(
            AcquisitionTarget.user_id == user_id)
        if starred_only:
            stmt = stmt.where(AcquisitionTarget.is_starred.is_(True))
        stmt = stmt.order_by(AcquisitionTarget.relevance_score.desc().nullslast())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def create_target(
        self, session: AsyncSession, user_id: int,
        target_name: str, rationale: str | None = None,
        patent_count: int = 0, relevance_score: float | None = None,
        cpc_overlap: list[str] | None = None,
    ) -> AcquisitionTarget:
        target = AcquisitionTarget(
            user_id=user_id, target_name=target_name,
            rationale=rationale, patent_count=patent_count,
            relevance_score=relevance_score,
            cpc_overlap=cpc_overlap or [], analysis_data={})
        session.add(target)
        await session.flush()
        await session.refresh(target)
        return target

    async def update_target(
        self, session: AsyncSession, target_id: int, user_id: int,
        target_name: str | None = None, rationale: str | None = None,
        patent_count: int | None = None,
        relevance_score: float | None = None,
        is_starred: bool | None = None,
    ) -> AcquisitionTarget:
        target = await self._get_user_target(session, target_id, user_id)
        if target_name is not None:
            target.target_name = target_name
        if rationale is not None:
            target.rationale = rationale
        if patent_count is not None:
            target.patent_count = patent_count
        if relevance_score is not None:
            target.relevance_score = relevance_score
        if is_starred is not None:
            target.is_starred = is_starred
        await session.flush()
        return target

    async def delete_target(
        self, session: AsyncSession, target_id: int, user_id: int,
    ) -> bool:
        target = await self._get_user_target(session, target_id, user_id)
        await session.delete(target)
        return True

    # ---- Stubs ----

    async def _run_comparison(self, entity_a: str, entity_b: str) -> dict:
        logger.info("portfolio.compare", entity_a=entity_a, entity_b=entity_b)
        return {
            "comparison_data": {
                "entity_a_count": 0, "entity_b_count": 0,
                "shared_cpc": [], "unique_a_cpc": [], "unique_b_cpc": [],
            },
            "overlap_score": 0.0,
            "summary": f"Comparison of {entity_a} vs {entity_b} pending full analysis.",
        }

    # ---- Internal helpers ----

    async def _get_user_monitor(
        self, session: AsyncSession, monitor_id: int, user_id: int,
    ) -> CompetitorMonitor:
        r = await session.execute(
            select(CompetitorMonitor).where(and_(
                CompetitorMonitor.id == monitor_id,
                CompetitorMonitor.user_id == user_id)))
        m = r.scalar_one_or_none()
        if m is None:
            raise ValueError("Competitor monitor not found")
        return m

    async def _get_user_comparison(
        self, session: AsyncSession, comparison_id: int, user_id: int,
    ) -> PortfolioComparison:
        r = await session.execute(
            select(PortfolioComparison).where(and_(
                PortfolioComparison.id == comparison_id,
                PortfolioComparison.user_id == user_id)))
        c = r.scalar_one_or_none()
        if c is None:
            raise ValueError("Portfolio comparison not found")
        return c

    async def _get_user_target(
        self, session: AsyncSession, target_id: int, user_id: int,
    ) -> AcquisitionTarget:
        r = await session.execute(
            select(AcquisitionTarget).where(and_(
                AcquisitionTarget.id == target_id,
                AcquisitionTarget.user_id == user_id)))
        t = r.scalar_one_or_none()
        if t is None:
            raise ValueError("Acquisition target not found")
        return t


competitive_service = CompetitiveService()
