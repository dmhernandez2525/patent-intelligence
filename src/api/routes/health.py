from fastapi import APIRouter
from pydantic import BaseModel

from src.config import settings

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
        from src.database.connection import engine
        from sqlalchemy import text

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
