"""Dashboard statistics service."""

from datetime import date, timedelta

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.patent import Patent, MaintenanceFee
from src.models.watchlist import WatchlistItem, Alert
from src.models.ingestion import IngestionJob
from src.utils.logger import logger


class StatsService:
    """Service for gathering dashboard statistics."""

    async def get_dashboard_stats(
        self,
        session: AsyncSession,
        user_id: str = "default",
    ) -> dict:
        """Get comprehensive dashboard statistics."""
        today = date.today()

        # Patent counts
        total_patents = await self._count_patents(session)
        expiring_90_days = await self._count_expiring(session, today, 90)

        # CPC activity
        top_cpc = await self._get_top_cpc(session)

        # Watchlist stats
        watchlist_count = await self._count_watchlist(session, user_id)
        unread_alerts = await self._count_unread_alerts(session, user_id)

        # Ingestion status
        last_ingestion = await self._get_last_ingestion(session)

        return {
            "patents": {
                "total": total_patents,
                "expiring_90_days": expiring_90_days,
            },
            "trends": {
                "top_cpc": top_cpc,
            },
            "watchlist": {
                "count": watchlist_count,
                "unread_alerts": unread_alerts,
            },
            "ingestion": {
                "last_run": last_ingestion.get("completed_at") if last_ingestion else None,
                "last_source": last_ingestion.get("source") if last_ingestion else None,
                "last_status": last_ingestion.get("status") if last_ingestion else None,
            },
        }

    async def get_system_status(self, session: AsyncSession) -> dict:
        """Get system health/status information."""
        status = {
            "api_server": "operational",
            "database": "unknown",
            "uspto_ingestion": "pending",
            "epo_integration": "pending",
            "embedding_service": "pending",
        }

        # Check database
        try:
            await session.execute(select(func.now()))
            status["database"] = "operational"
        except Exception:
            status["database"] = "error"

        # Check if any patents exist (indicates ingestion ran)
        patent_count = await self._count_patents(session)
        if patent_count > 0:
            # Check for USPTO patents
            uspto_count = await session.execute(
                select(func.count(Patent.id)).where(Patent.source == "uspto")
            )
            if (uspto_count.scalar() or 0) > 0:
                status["uspto_ingestion"] = "operational"

            # Check for EPO patents
            epo_count = await session.execute(
                select(func.count(Patent.id)).where(Patent.source == "epo")
            )
            if (epo_count.scalar() or 0) > 0:
                status["epo_integration"] = "operational"

            # Check if any embeddings exist
            embedding_count = await session.execute(
                select(func.count(Patent.id)).where(Patent.embedding.isnot(None))
            )
            if (embedding_count.scalar() or 0) > 0:
                status["embedding_service"] = "operational"

        return status

    async def _count_patents(self, session: AsyncSession) -> int:
        """Count total patents."""
        result = await session.execute(select(func.count(Patent.id)))
        return result.scalar() or 0

    async def _count_expiring(
        self, session: AsyncSession, today: date, days: int
    ) -> int:
        """Count patents expiring within days."""
        end_date = today + timedelta(days=days)
        result = await session.execute(
            select(func.count(Patent.id)).where(
                and_(
                    Patent.expiration_date >= today,
                    Patent.expiration_date <= end_date,
                    Patent.status == "active",
                )
            )
        )
        return result.scalar() or 0

    async def _get_top_cpc(self, session: AsyncSession, limit: int = 5) -> list[dict]:
        """Get top CPC codes by patent count."""
        today = date.today()
        start_date = today - timedelta(days=365 * 3)

        result = await session.execute(
            select(
                func.substr(func.unnest(Patent.cpc_codes), 1, 4).label("cpc"),
                func.count(func.distinct(Patent.id)).label("count"),
            )
            .where(
                and_(
                    Patent.cpc_codes.isnot(None),
                    Patent.filing_date >= start_date,
                )
            )
            .group_by("cpc")
            .order_by(func.count(func.distinct(Patent.id)).desc())
            .limit(limit)
        )

        return [{"cpc_code": row[0], "count": row[1]} for row in result.all()]

    async def _count_watchlist(self, session: AsyncSession, user_id: str) -> int:
        """Count active watchlist items."""
        result = await session.execute(
            select(func.count(WatchlistItem.id)).where(
                and_(
                    WatchlistItem.user_id == user_id,
                    WatchlistItem.is_active == True,
                )
            )
        )
        return result.scalar() or 0

    async def _count_unread_alerts(self, session: AsyncSession, user_id: str) -> int:
        """Count unread alerts for user."""
        watchlist_ids = select(WatchlistItem.id).where(
            WatchlistItem.user_id == user_id
        )

        result = await session.execute(
            select(func.count(Alert.id)).where(
                and_(
                    Alert.watchlist_item_id.in_(watchlist_ids),
                    Alert.is_read == False,
                    Alert.is_dismissed == False,
                )
            )
        )
        return result.scalar() or 0

    async def _get_last_ingestion(self, session: AsyncSession) -> dict | None:
        """Get info about the last ingestion job."""
        result = await session.execute(
            select(IngestionJob)
            .order_by(IngestionJob.created_at.desc())
            .limit(1)
        )
        job = result.scalar_one_or_none()

        if not job:
            return None

        return {
            "source": job.source,
            "status": job.status,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "patents_processed": job.patents_processed,
        }


stats_service = StatsService()
