"""API routes for competitive intelligence dashboard."""

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
from src.api.schemas.competitive import (
    ComparisonCreateRequest,
    ComparisonListResponse,
    ComparisonResponse,
    MonitorCreateRequest,
    MonitorListResponse,
    MonitorResponse,
    MonitorUpdateRequest,
    TargetCreateRequest,
    TargetListResponse,
    TargetResponse,
    TargetUpdateRequest,
)
from src.database.connection import get_session
from src.models.user import User
from src.services.activity_service import activity_service
from src.services.competitive_service import competitive_service

router = APIRouter()


def _monitor_response(m) -> MonitorResponse:
    return MonitorResponse(
        id=m.id, competitor_name=m.competitor_name,
        aliases=m.aliases or [], cpc_focus=m.cpc_focus or [],
        status=m.status, notes=m.notes,
        last_checked_at=m.last_checked_at.isoformat() if m.last_checked_at else None,
        created_at=m.created_at.isoformat() if m.created_at else None)


def _comparison_response(c) -> ComparisonResponse:
    return ComparisonResponse(
        id=c.id, entity_a=c.entity_a, entity_b=c.entity_b,
        status=c.status,
        comparison_data=c.comparison_data if c.comparison_data else {},
        overlap_score=c.overlap_score, summary=c.summary,
        error_message=c.error_message,
        computed_at=c.computed_at.isoformat() if c.computed_at else None,
        created_at=c.created_at.isoformat() if c.created_at else None)


def _target_response(t) -> TargetResponse:
    return TargetResponse(
        id=t.id, target_name=t.target_name, rationale=t.rationale,
        patent_count=t.patent_count, relevance_score=t.relevance_score,
        cpc_overlap=t.cpc_overlap or [],
        analysis_data=t.analysis_data if t.analysis_data else {},
        is_starred=t.is_starred,
        created_at=t.created_at.isoformat() if t.created_at else None)


# ---- Competitor Monitors ----

@router.get("/monitors", response_model=MonitorListResponse)
async def list_monitors(
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MonitorListResponse:
    monitors = await competitive_service.list_monitors(
        session, user_id=current_user.id, status=status_filter)
    return MonitorListResponse(
        monitors=[_monitor_response(m) for m in monitors])

@router.post(
    "/monitors", response_model=MonitorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_monitor(
    payload: MonitorCreateRequest, request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MonitorResponse:
    m = await competitive_service.create_monitor(
        session, user_id=current_user.id,
        competitor_name=payload.competitor_name,
        aliases=payload.aliases, cpc_focus=payload.cpc_focus,
        notes=payload.notes)
    await activity_service.log_event(
        session, event_type="competitive.monitor.created",
        user_id=current_user.id, resource_type="competitor_monitor",
        resource_id=str(m.id),
        event_metadata={"competitor": payload.competitor_name},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"))
    await session.commit()
    return _monitor_response(m)

@router.patch("/monitors/{monitor_id}", response_model=MonitorResponse)
async def update_monitor(
    monitor_id: int, payload: MonitorUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MonitorResponse:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    try:
        m = await competitive_service.update_monitor(
            session, monitor_id=monitor_id,
            user_id=current_user.id, **updates)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return _monitor_response(m)

@router.delete("/monitors/{monitor_id}")
async def delete_monitor(
    monitor_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    try:
        await competitive_service.delete_monitor(
            session, monitor_id=monitor_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return {"success": True}

# ---- Portfolio Comparisons ----

@router.get("/comparisons", response_model=ComparisonListResponse)
async def list_comparisons(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ComparisonListResponse:
    comps = await competitive_service.list_comparisons(
        session, user_id=current_user.id)
    return ComparisonListResponse(
        comparisons=[_comparison_response(c) for c in comps])

@router.post(
    "/comparisons", response_model=ComparisonResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comparison(
    payload: ComparisonCreateRequest, request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ComparisonResponse:
    c = await competitive_service.create_comparison(
        session, user_id=current_user.id,
        entity_a=payload.entity_a, entity_b=payload.entity_b)
    await activity_service.log_event(
        session, event_type="competitive.comparison.created",
        user_id=current_user.id, resource_type="portfolio_comparison",
        resource_id=str(c.id),
        event_metadata={"entity_a": payload.entity_a, "entity_b": payload.entity_b},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"))
    await session.commit()
    return _comparison_response(c)

@router.post("/comparisons/{comparison_id}/compute", response_model=ComparisonResponse)
async def compute_comparison(
    comparison_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ComparisonResponse:
    try:
        c = await competitive_service.compute_comparison(
            session, comparison_id=comparison_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return _comparison_response(c)

@router.delete("/comparisons/{comparison_id}")
async def delete_comparison(
    comparison_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    try:
        await competitive_service.delete_comparison(
            session, comparison_id=comparison_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return {"success": True}

# ---- Acquisition Targets ----

@router.get("/targets", response_model=TargetListResponse)
async def list_targets(
    starred: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TargetListResponse:
    targets = await competitive_service.list_targets(
        session, user_id=current_user.id, starred_only=starred)
    return TargetListResponse(
        targets=[_target_response(t) for t in targets])

@router.post(
    "/targets", response_model=TargetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_target(
    payload: TargetCreateRequest, request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TargetResponse:
    t = await competitive_service.create_target(
        session, user_id=current_user.id,
        target_name=payload.target_name, rationale=payload.rationale,
        patent_count=payload.patent_count,
        relevance_score=payload.relevance_score,
        cpc_overlap=payload.cpc_overlap)
    await activity_service.log_event(
        session, event_type="competitive.target.created",
        user_id=current_user.id, resource_type="acquisition_target",
        resource_id=str(t.id),
        event_metadata={"target": payload.target_name},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"))
    await session.commit()
    return _target_response(t)

@router.patch("/targets/{target_id}", response_model=TargetResponse)
async def update_target(
    target_id: int, payload: TargetUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TargetResponse:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    try:
        t = await competitive_service.update_target(
            session, target_id=target_id,
            user_id=current_user.id, **updates)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return _target_response(t)

@router.delete("/targets/{target_id}")
async def delete_target(
    target_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    try:
        await competitive_service.delete_target(
            session, target_id=target_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return {"success": True}
