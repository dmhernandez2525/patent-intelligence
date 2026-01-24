from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session
from src.api.schemas.expiration import (
    ExpirationDashboardResponse,
    ExpirationListResponse,
    ExpirationStatsResponse,
    MaintenanceFeeListResponse,
)
from src.services.expiration_service import expiration_service
from src.utils.logger import logger

router = APIRouter()


@router.get("/dashboard", response_model=ExpirationDashboardResponse)
async def expiration_dashboard(
    country: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> ExpirationDashboardResponse:
    """Get expiration dashboard with stats, upcoming expirations, and fees."""
    logger.info("expiration.dashboard", country=country)

    stats = await expiration_service.get_expiration_stats(session, country=country)
    expiring_soon, _ = await expiration_service.get_expiring_patents(
        session, days=30, country=country, per_page=10
    )
    lapsed, _ = await expiration_service.get_lapsed_patents(
        session, days_back=90, country=country, per_page=10
    )
    fees, _ = await expiration_service.get_upcoming_maintenance_fees(
        session, days=90, per_page=10
    )

    return ExpirationDashboardResponse(
        stats=stats,
        expiring_soon=expiring_soon,
        recently_lapsed=lapsed,
        upcoming_fees=fees,
    )


@router.get("/upcoming", response_model=ExpirationListResponse)
async def upcoming_expirations(
    days: int = Query(default=90, ge=1, le=3650),
    country: str | None = Query(None),
    cpc_code: str | None = Query(None),
    assignee: str | None = Query(None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> ExpirationListResponse:
    """Get patents expiring within a specified time window."""
    logger.info("expiration.upcoming", days=days, country=country, page=page)

    patents, total = await expiration_service.get_expiring_patents(
        session,
        days=days,
        country=country,
        cpc_code=cpc_code,
        assignee=assignee,
        page=page,
        per_page=per_page,
    )

    return ExpirationListResponse(
        patents=patents,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/lapsed", response_model=ExpirationListResponse)
async def lapsed_patents(
    days_back: int = Query(default=365, ge=1, le=3650),
    country: str | None = Query(None),
    cpc_code: str | None = Query(None),
    assignee: str | None = Query(None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> ExpirationListResponse:
    """Get recently lapsed patents (expired or missed maintenance fees)."""
    logger.info("expiration.lapsed", days_back=days_back, country=country, page=page)

    patents, total = await expiration_service.get_lapsed_patents(
        session,
        days_back=days_back,
        country=country,
        cpc_code=cpc_code,
        assignee=assignee,
        page=page,
        per_page=per_page,
    )

    return ExpirationListResponse(
        patents=patents,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/maintenance-fees", response_model=MaintenanceFeeListResponse)
async def maintenance_fees(
    days: int = Query(default=90, ge=1, le=3650),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> MaintenanceFeeListResponse:
    """Get upcoming maintenance fee deadlines."""
    logger.info("expiration.maintenance_fees", days=days, page=page)

    fees, total = await expiration_service.get_upcoming_maintenance_fees(
        session, days=days, page=page, per_page=per_page
    )

    return MaintenanceFeeListResponse(
        fees=fees,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/stats", response_model=ExpirationStatsResponse)
async def expiration_stats(
    country: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> ExpirationStatsResponse:
    """Get expiration statistics and trends."""
    logger.info("expiration.stats", country=country)

    stats = await expiration_service.get_expiration_stats(session, country=country)
    return ExpirationStatsResponse(**stats)
