from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session

router = APIRouter()


@router.post("/generate")
async def generate_ideas(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Generate invention ideas from patents. Implemented in Phase 8."""
    return {"ideas": [], "message": "Idea generation available after Phase 8"}
