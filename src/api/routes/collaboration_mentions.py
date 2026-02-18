"""API routes for mention notifications and team activity feed."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_user
from src.api.schemas.collaboration_content import (
    MentionListResponse,
    MentionResponse,
    TeamActivityEntryResponse,
    TeamActivityFeedResponse,
)
from src.database.connection import get_session
from src.models.user import User
from src.services.collaboration_content_service import collaboration_content_service
from src.services.team_activity_service import team_activity_service

router = APIRouter()


@router.get("/mentions", response_model=MentionListResponse)
async def list_mentions(
    unread_only: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MentionListResponse:
    mentions = await collaboration_content_service.list_mentions(
        session, user_id=current_user.id, unread_only=unread_only,
    )
    return MentionListResponse(
        notifications=[
            MentionResponse(
                id=m.id, user_id=m.user_id, comment_id=m.comment_id,
                message=m.message, is_read=m.is_read,
                read_at=m.read_at.isoformat() if m.read_at else None,
                created_at=m.created_at.isoformat() if m.created_at else None,
            )
            for m in mentions
        ]
    )


@router.post("/mentions/{mention_id}/read")
async def mark_mention_read(
    mention_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    success = await collaboration_content_service.mark_mention_read(
        session, mention_id=mention_id, user_id=current_user.id,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Mention not found")
    await session.commit()
    return {"success": True}


@router.get("/activity-feed", response_model=TeamActivityFeedResponse)
async def team_activity_feed(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TeamActivityFeedResponse:
    entries = await team_activity_service.get_feed(session, current_user.id, limit=limit)
    return TeamActivityFeedResponse(
        entries=[TeamActivityEntryResponse(**entry) for entry in entries]
    )
