"""API routes for AI-powered patent insights."""

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
from src.api.schemas.insight import (
    InsightCreateRequest,
    InsightListResponse,
    InsightResponse,
    TemplateListResponse,
    TemplateResponse,
)
from src.database.connection import get_session
from src.models.user import User
from src.services.activity_service import activity_service
from src.services.insight_service import insight_service

router = APIRouter()


def _insight_response(i) -> InsightResponse:
    return InsightResponse(
        id=i.id, user_id=i.user_id, patent_id=i.patent_id,
        insight_type=i.insight_type,
        status=i.status,
        query_text=i.query_text,
        result_text=i.result_text,
        result_data=i.result_data if i.result_data else {},
        model_used=i.model_used,
        token_count=i.token_count,
        error_message=i.error_message,
        completed_at=i.completed_at.isoformat() if i.completed_at else None,
        created_at=i.created_at.isoformat() if i.created_at else None,
    )


def _template_response(t) -> TemplateResponse:
    return TemplateResponse(
        id=t.id, name=t.name,
        insight_type=t.insight_type,
        prompt_template=t.prompt_template,
        description=t.description,
        is_default=t.is_default,
    )


# ---- Insights ----

@router.get("", response_model=InsightListResponse)
async def list_insights(
    insight_type: str | None = Query(default=None),
    patent_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InsightListResponse:
    """List insights for the current user, optionally filtered."""
    insights = await insight_service.list_insights(
        session, user_id=current_user.id,
        insight_type=insight_type,
        patent_id=patent_id,
    )
    return InsightListResponse(
        insights=[_insight_response(i) for i in insights],
        total=len(insights),
    )


@router.post(
    "", response_model=InsightResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_insight(
    payload: InsightCreateRequest, request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InsightResponse:
    """Create a new insight record."""
    insight = await insight_service.create_insight(
        session, user_id=current_user.id,
        insight_type=payload.insight_type,
        query_text=payload.query_text,
        patent_id=payload.patent_id,
    )
    await activity_service.log_event(
        session, event_type="insight.created",
        user_id=current_user.id, resource_type="insight",
        resource_id=str(insight.id),
        event_metadata={
            "insight_type": payload.insight_type,
            "patent_id": payload.patent_id,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    return _insight_response(insight)


@router.get("/{insight_id}", response_model=InsightResponse)
async def get_insight(
    insight_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InsightResponse:
    """Retrieve a single insight by ID."""
    try:
        insight = await insight_service.get_insight(
            session, insight_id=insight_id, user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _insight_response(insight)


@router.post(
    "/{insight_id}/generate", response_model=InsightResponse,
)
async def generate_insight(
    insight_id: int, request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InsightResponse:
    """Trigger AI generation for an existing insight."""
    try:
        insight = await insight_service.generate_insight(
            session, insight_id=insight_id, user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await activity_service.log_event(
        session, event_type="insight.generated",
        user_id=current_user.id, resource_type="insight",
        resource_id=str(insight_id),
        event_metadata={"insight_type": insight.insight_type},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    return _insight_response(insight)


@router.delete("/{insight_id}")
async def delete_insight(
    insight_id: int, request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    """Delete an insight by ID."""
    try:
        await insight_service.delete_insight(
            session, insight_id=insight_id, user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await activity_service.log_event(
        session, event_type="insight.deleted",
        user_id=current_user.id, resource_type="insight",
        resource_id=str(insight_id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    return {"success": True}


# ---- Templates ----

@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    insight_type: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TemplateListResponse:
    """List available prompt templates, optionally filtered by type."""
    templates = await insight_service.list_templates(
        session, insight_type=insight_type,
    )
    return TemplateListResponse(
        templates=[_template_response(t) for t in templates],
    )
