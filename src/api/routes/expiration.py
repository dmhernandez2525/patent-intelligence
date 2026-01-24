from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session
from src.api.schemas.expiration import ExpirationDashboardResponse

router = APIRouter()


@router.get("/dashboard", response_model=ExpirationDashboardResponse)
async def expiration_dashboard(
    session: AsyncSession = Depends(get_session),
) -> ExpirationDashboardResponse:
    """Get expiration dashboard data. Implemented in Phase 4."""
    return ExpirationDashboardResponse(
        expiring_30_days=[],
        expiring_90_days=[],
        expiring_365_days=[],
        recently_lapsed=[],
        total_expiring_soon=0,
    )
