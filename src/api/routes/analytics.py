"""API routes for custom analytics engine."""

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
from src.api.schemas.analytics import (
    MetricCreateRequest,
    MetricListResponse,
    MetricResponse,
    MetricUpdateRequest,
    QueryCreateRequest,
    QueryListResponse,
    QueryResponse,
    QueryUpdateRequest,
    ScheduleCreateRequest,
    ScheduleListResponse,
    ScheduleResponse,
    ScheduleUpdateRequest,
)
from src.database.connection import get_session
from src.models.user import User
from src.services.activity_service import activity_service
from src.services.analytics_service import analytics_service

router = APIRouter()


def _query_response(q) -> QueryResponse:
    return QueryResponse(
        id=q.id, name=q.name, description=q.description,
        query_config=q.query_config if q.query_config else {},
        filters=q.filters if q.filters else {},
        status=q.status, is_public=q.is_public,
        last_run_at=q.last_run_at.isoformat() if q.last_run_at else None,
        run_count=q.run_count or 0,
        created_at=q.created_at.isoformat() if q.created_at else None)


def _metric_response(m) -> MetricResponse:
    return MetricResponse(
        id=m.id, name=m.name, metric_type=m.metric_type,
        definition=m.definition if m.definition else {},
        current_value=m.current_value,
        last_computed_at=m.last_computed_at.isoformat() if m.last_computed_at else None,
        created_at=m.created_at.isoformat() if m.created_at else None)


def _schedule_response(s) -> ScheduleResponse:
    return ScheduleResponse(
        id=s.id, query_id=s.query_id, metric_id=s.metric_id,
        frequency=s.frequency, is_active=s.is_active,
        next_run_at=s.next_run_at.isoformat() if s.next_run_at else None,
        created_at=s.created_at.isoformat() if s.created_at else None)


# ---- Saved Queries ----

@router.get("/queries", response_model=QueryListResponse)
async def list_queries(
    status_filter: str | None = Query(default=None, alias="status"),
    public: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> QueryListResponse:
    queries = await analytics_service.list_queries(
        session, user_id=current_user.id,
        status=status_filter, public_only=public)
    return QueryListResponse(
        queries=[_query_response(q) for q in queries])

@router.post(
    "/queries", response_model=QueryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_query(
    payload: QueryCreateRequest, request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> QueryResponse:
    q = await analytics_service.create_query(
        session, user_id=current_user.id, name=payload.name,
        description=payload.description, query_config=payload.query_config,
        filters=payload.filters, is_public=payload.is_public)
    await activity_service.log_event(
        session, event_type="analytics.query.created",
        user_id=current_user.id, resource_type="saved_query",
        resource_id=str(q.id),
        event_metadata={"name": payload.name},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"))
    await session.commit()
    return _query_response(q)

@router.patch("/queries/{query_id}", response_model=QueryResponse)
async def update_query(
    query_id: int, payload: QueryUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> QueryResponse:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    try:
        q = await analytics_service.update_query(
            session, query_id=query_id,
            user_id=current_user.id, **updates)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return _query_response(q)

@router.delete("/queries/{query_id}")
async def delete_query(
    query_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    try:
        await analytics_service.delete_query(
            session, query_id=query_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return {"success": True}

@router.post("/queries/{query_id}/run", response_model=QueryResponse)
async def run_query(
    query_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> QueryResponse:
    try:
        q = await analytics_service.run_query(
            session, query_id=query_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return _query_response(q)

# ---- Custom Metrics ----

@router.get("/metrics", response_model=MetricListResponse)
async def list_metrics(
    metric_type: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MetricListResponse:
    metrics = await analytics_service.list_metrics(
        session, user_id=current_user.id, metric_type=metric_type)
    return MetricListResponse(
        metrics=[_metric_response(m) for m in metrics])

@router.post(
    "/metrics", response_model=MetricResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_metric(
    payload: MetricCreateRequest, request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MetricResponse:
    m = await analytics_service.create_metric(
        session, user_id=current_user.id, name=payload.name,
        metric_type=payload.metric_type, definition=payload.definition)
    await activity_service.log_event(
        session, event_type="analytics.metric.created",
        user_id=current_user.id, resource_type="custom_metric",
        resource_id=str(m.id),
        event_metadata={"name": payload.name, "type": payload.metric_type},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"))
    await session.commit()
    return _metric_response(m)

@router.patch("/metrics/{metric_id}", response_model=MetricResponse)
async def update_metric(
    metric_id: int, payload: MetricUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MetricResponse:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    try:
        m = await analytics_service.update_metric(
            session, metric_id=metric_id,
            user_id=current_user.id, **updates)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return _metric_response(m)

@router.delete("/metrics/{metric_id}")
async def delete_metric(
    metric_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    try:
        await analytics_service.delete_metric(
            session, metric_id=metric_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return {"success": True}

@router.post("/metrics/{metric_id}/compute", response_model=MetricResponse)
async def compute_metric(
    metric_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MetricResponse:
    try:
        m = await analytics_service.compute_metric(
            session, metric_id=metric_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return _metric_response(m)

# ---- Schedules ----

@router.get("/schedules", response_model=ScheduleListResponse)
async def list_schedules(
    active: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ScheduleListResponse:
    schedules = await analytics_service.list_schedules(
        session, user_id=current_user.id, active_only=active)
    return ScheduleListResponse(
        schedules=[_schedule_response(s) for s in schedules])

@router.post(
    "/schedules", response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule(
    payload: ScheduleCreateRequest, request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ScheduleResponse:
    s = await analytics_service.create_schedule(
        session, user_id=current_user.id, frequency=payload.frequency,
        query_id=payload.query_id, metric_id=payload.metric_id)
    await activity_service.log_event(
        session, event_type="analytics.schedule.created",
        user_id=current_user.id, resource_type="analytics_schedule",
        resource_id=str(s.id),
        event_metadata={"frequency": payload.frequency},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"))
    await session.commit()
    return _schedule_response(s)

@router.patch("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int, payload: ScheduleUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ScheduleResponse:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    try:
        s = await analytics_service.update_schedule(
            session, schedule_id=schedule_id,
            user_id=current_user.id, **updates)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return _schedule_response(s)

@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    try:
        await analytics_service.delete_schedule(
            session, schedule_id=schedule_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return {"success": True}
