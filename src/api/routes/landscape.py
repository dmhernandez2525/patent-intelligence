"""API routes for patent landscape visualization."""

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
from src.api.schemas.landscape import (
    ClusterSummary,
    ClusterSummaryResponse,
    ComputeRequest,
    PointListResponse,
    PointResponse,
    SnapshotCreateRequest,
    SnapshotListResponse,
    SnapshotResponse,
)
from src.database.connection import get_session
from src.models.user import User
from src.services.activity_service import activity_service
from src.services.landscape_service import landscape_service

router = APIRouter()


def _snapshot_response(s) -> SnapshotResponse:
    return SnapshotResponse(
        id=s.id, user_id=s.user_id, name=s.name,
        description=s.description,
        reduction_method=s.reduction_method,
        cluster_method=s.cluster_method,
        num_clusters=s.num_clusters,
        patent_count=s.patent_count,
        status=s.status,
        error_message=s.error_message,
        computed_at=s.computed_at.isoformat() if s.computed_at else None,
        created_at=s.created_at.isoformat() if s.created_at else None,
    )


def _point_response(p) -> PointResponse:
    return PointResponse(
        id=p.id, patent_id=p.patent_id,
        x=p.x, y=p.y,
        cluster_id=p.cluster_id,
        cluster_label=p.cluster_label,
        metadata=p.point_metadata if p.point_metadata else {},
    )


# ---- Snapshots ----

@router.get("/snapshots", response_model=SnapshotListResponse)
async def list_snapshots(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SnapshotListResponse:
    """List all landscape snapshots for the current user."""
    snapshots = await landscape_service.list_snapshots(
        session, user_id=current_user.id,
    )
    return SnapshotListResponse(
        snapshots=[_snapshot_response(s) for s in snapshots],
    )


@router.post(
    "/snapshots", response_model=SnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_snapshot(
    payload: SnapshotCreateRequest, request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SnapshotResponse:
    """Create a new landscape snapshot."""
    snapshot = await landscape_service.create_snapshot(
        session, user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        reduction_method=payload.reduction_method,
        cluster_method=payload.cluster_method,
        num_clusters=payload.num_clusters,
        config=payload.config,
    )
    await activity_service.log_event(
        session, event_type="landscape.snapshot.created",
        user_id=current_user.id, resource_type="landscape_snapshot",
        resource_id=str(snapshot.id),
        event_metadata={
            "name": payload.name,
            "reduction_method": payload.reduction_method,
            "cluster_method": payload.cluster_method,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    return _snapshot_response(snapshot)


@router.get("/snapshots/{snapshot_id}", response_model=SnapshotResponse)
async def get_snapshot(
    snapshot_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SnapshotResponse:
    """Retrieve a single landscape snapshot by ID."""
    try:
        snapshot = await landscape_service.get_snapshot(
            session, snapshot_id=snapshot_id, user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _snapshot_response(snapshot)


@router.post(
    "/snapshots/{snapshot_id}/compute",
    response_model=SnapshotResponse,
)
async def compute_snapshot(
    snapshot_id: int, payload: ComputeRequest, request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SnapshotResponse:
    """Trigger landscape computation for a snapshot."""
    try:
        snapshot = await landscape_service.compute_snapshot(
            session, snapshot_id=snapshot_id, user_id=current_user.id,
            patent_ids=payload.patent_ids,
            cpc_filter=payload.cpc_filter,
            assignee_filter=payload.assignee_filter,
            max_patents=payload.max_patents,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await activity_service.log_event(
        session, event_type="landscape.snapshot.computed",
        user_id=current_user.id, resource_type="landscape_snapshot",
        resource_id=str(snapshot_id),
        event_metadata={"max_patents": payload.max_patents},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    return _snapshot_response(snapshot)


@router.get(
    "/snapshots/{snapshot_id}/points",
    response_model=PointListResponse,
)
async def list_points(
    snapshot_id: int,
    cluster_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PointListResponse:
    """List projected points for a landscape snapshot."""
    try:
        points = await landscape_service.get_points(
            session, snapshot_id=snapshot_id, user_id=current_user.id,
            cluster_id=cluster_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return PointListResponse(
        points=[_point_response(p) for p in points],
        total=len(points),
    )


@router.get(
    "/snapshots/{snapshot_id}/clusters",
    response_model=ClusterSummaryResponse,
)
async def list_clusters(
    snapshot_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ClusterSummaryResponse:
    """Get cluster summaries for a landscape snapshot."""
    try:
        clusters = await landscape_service.get_cluster_summary(
            session, snapshot_id=snapshot_id, user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ClusterSummaryResponse(clusters=[
        ClusterSummary(
            cluster_id=c["cluster_id"], label=c["label"],
            count=c["count"],
            centroid_x=c["centroid"]["x"],
            centroid_y=c["centroid"]["y"],
            top_assignees=c["top_assignees"],
        )
        for c in clusters
    ])


@router.delete("/snapshots/{snapshot_id}")
async def delete_snapshot(
    snapshot_id: int, request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    """Delete a landscape snapshot and its associated data."""
    try:
        await landscape_service.delete_snapshot(
            session, snapshot_id=snapshot_id, user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await activity_service.log_event(
        session, event_type="landscape.snapshot.deleted",
        user_id=current_user.id, resource_type="landscape_snapshot",
        resource_id=str(snapshot_id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    return {"success": True}
