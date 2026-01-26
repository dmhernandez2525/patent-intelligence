from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database.connection import get_session
from src.services.stats_service import stats_service

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str
    service: str


class DetailedHealthResponse(HealthResponse):
    database: str
    redis: str
    celery: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        service=settings.app_name,
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check() -> DetailedHealthResponse:
    db_status = "healthy"
    redis_status = "healthy"
    celery_status = "healthy"

    try:
        from sqlalchemy import text

        from src.database.connection import engine

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
    except Exception:
        redis_status = "unhealthy"

    return DetailedHealthResponse(
        status="healthy" if all(s == "healthy" for s in [db_status, redis_status]) else "degraded",
        version=settings.app_version,
        service=settings.app_name,
        database=db_status,
        redis=redis_status,
        celery=celery_status,
    )


@router.get("/stats")
async def get_dashboard_stats(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get dashboard statistics for the frontend."""
    return await stats_service.get_dashboard_stats(session)


@router.get("/status")
async def get_system_status(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get system component status."""
    return await stats_service.get_system_status(session)
