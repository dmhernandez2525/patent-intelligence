"""User activity logging service."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import UserActivityLog
from src.utils.logger import logger


class ActivityService:
    """Persists user activity events for auditing and analytics."""

    async def log_event(
        self,
        session: AsyncSession,
        event_type: str,
        user_id: int | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        event_metadata: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        success: bool = True,
    ) -> None:
        if not hasattr(session, "add"):
            logger.warning("activity.skipped", reason="session_missing_add", event_type=event_type)
            return

        activity = UserActivityLog(
            user_id=user_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            event_metadata=event_metadata,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
        )
        session.add(activity)
        logger.info(
            "activity.logged",
            event_type=event_type,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            success=success,
        )


activity_service = ActivityService()
