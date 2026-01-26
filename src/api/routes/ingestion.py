from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session
from src.models.ingestion import IngestionCheckpoint, IngestionJob
from src.utils.logger import logger

router = APIRouter()


class IngestionTriggerRequest(BaseModel):
    source: str = Field(default="uspto", pattern="^(uspto|epo|bigquery)$")
    batch_size: int = Field(default=100, ge=10, le=1000)
    max_patents: int | None = Field(default=1000, ge=1, le=100000)
    since_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class IngestionJobResponse(BaseModel):
    id: int
    source: str
    status: str
    job_type: str
    total_fetched: int
    total_inserted: int
    total_updated: int
    total_errors: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    error_message: str | None = None
    celery_task_id: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class IngestionStatusResponse(BaseModel):
    jobs: list[IngestionJobResponse]
    total_jobs: int
    active_jobs: int
    last_successful: IngestionJobResponse | None = None
    checkpoint: dict | None = None


@router.post("/trigger", response_model=IngestionJobResponse)
async def trigger_ingestion(
    request: IngestionTriggerRequest,
    session: AsyncSession = Depends(get_session),
) -> IngestionJobResponse:
    """Trigger a patent data ingestion job."""
    # Check for active jobs
    active = await session.execute(
        select(func.count(IngestionJob.id)).where(
            IngestionJob.source == request.source,
            IngestionJob.status.in_(["pending", "running"]),
        )
    )
    if (active.scalar() or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail=f"An ingestion job for {request.source} is already running",
        )

    # Create job record
    job = IngestionJob(
        source=request.source,
        status="pending",
        job_type="incremental" if request.since_date else "full",
    )
    session.add(job)
    await session.flush()

    # Trigger Celery task
    try:
        from src.pipeline.orchestrator import ingest_patents_task

        _since = None  # TODO: Pass to ingest_patents_task when supported
        if request.since_date:
            try:
                _since = datetime.strptime(request.since_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid since_date format")

        task = ingest_patents_task.delay(
            source=request.source,
            batch_size=request.batch_size,
            max_patents=request.max_patents,
        )
        job.celery_task_id = task.id
        job.status = "running"
        job.started_at = datetime.now(UTC)
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        logger.error("ingestion.trigger_failed", error=str(e))

    await session.flush()

    logger.info(
        "ingestion.triggered",
        job_id=job.id,
        source=request.source,
        task_id=job.celery_task_id,
    )

    return IngestionJobResponse.model_validate(job, from_attributes=True)


@router.get("/status", response_model=IngestionStatusResponse)
async def get_ingestion_status(
    source: str | None = None,
    limit: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> IngestionStatusResponse:
    """Get ingestion job status and history."""
    query = select(IngestionJob).order_by(desc(IngestionJob.created_at)).limit(limit)
    if source:
        query = query.where(IngestionJob.source == source)

    result = await session.execute(query)
    jobs = result.scalars().all()

    # Count active jobs
    active_count = sum(1 for j in jobs if j.status in ("pending", "running"))

    # Find last successful job
    last_success = None
    for j in jobs:
        if j.status == "completed":
            last_success = IngestionJobResponse.model_validate(j, from_attributes=True)
            break

    # Get checkpoint
    checkpoint = None
    if source:
        cp_result = await session.execute(
            select(IngestionCheckpoint).where(IngestionCheckpoint.source == source)
        )
        cp = cp_result.scalar_one_or_none()
        if cp:
            checkpoint = {
                "source": cp.source,
                "last_sync_date": cp.last_sync_date.isoformat() if cp.last_sync_date else None,
                "total_patents_ingested": cp.total_patents_ingested,
            }

    total = await session.execute(select(func.count(IngestionJob.id)))

    return IngestionStatusResponse(
        jobs=[IngestionJobResponse.model_validate(j, from_attributes=True) for j in jobs],
        total_jobs=total.scalar() or 0,
        active_jobs=active_count,
        last_successful=last_success,
        checkpoint=checkpoint,
    )


@router.get("/jobs/{job_id}", response_model=IngestionJobResponse)
async def get_ingestion_job(
    job_id: int,
    session: AsyncSession = Depends(get_session),
) -> IngestionJobResponse:
    """Get details of a specific ingestion job."""
    job = await session.get(IngestionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return IngestionJobResponse.model_validate(job, from_attributes=True)
