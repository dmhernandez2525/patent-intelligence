from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session

router = APIRouter()


@router.get("")
async def get_watchlist(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get user watchlist. Implemented in Phase 10."""
    return {"items": [], "message": "Watchlist available after Phase 10"}
