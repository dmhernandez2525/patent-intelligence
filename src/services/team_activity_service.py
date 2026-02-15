"""Team activity feed aggregation service."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.organization import OrganizationMember
from src.models.user import UserActivityLog


class TeamActivityService:
    """Aggregate activity across a user's team."""

    async def get_feed(self, session: AsyncSession, user_id: int, limit: int = 50) -> list[dict]:
        team_user_ids = await self._resolve_team_user_ids(session, user_id)
        result = await session.execute(
            select(UserActivityLog)
            .where(UserActivityLog.user_id.in_(team_user_ids))
            .order_by(UserActivityLog.created_at.desc())
            .limit(limit)
        )
        events = result.scalars().all()
        return [
            {
                "id": event.id,
                "user_id": event.user_id,
                "event_type": event.event_type,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "event_metadata": event.event_metadata or {},
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in events
        ]

    async def _resolve_team_user_ids(self, session: AsyncSession, user_id: int) -> set[int]:
        org_ids_query = select(OrganizationMember.organization_id).where(
            OrganizationMember.user_id == user_id
        )
        teammates_result = await session.execute(
            select(OrganizationMember.user_id).where(OrganizationMember.organization_id.in_(org_ids_query))
        )
        team_ids = {row[0] for row in teammates_result.all()}
        team_ids.add(user_id)
        return team_ids


team_activity_service = TeamActivityService()
