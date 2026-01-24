from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session
from src.services.idea_service import idea_service
from src.utils.logger import logger

router = APIRouter()


@router.post("/generate")
async def generate_ideas(
    cpc_prefix: str | None = Query(None),
    focus: str = Query(default="expiring", pattern="^(expiring|combination|improvement)$"),
    count: int = Query(default=5, ge=1, le=10),
    context_text: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Generate AI-powered invention ideas from patent landscape analysis."""
    logger.info(
        "ideas.generate",
        cpc_prefix=cpc_prefix,
        focus=focus,
        count=count,
    )

    result = await idea_service.generate_ideas(
        session,
        cpc_prefix=cpc_prefix,
        focus=focus,
        count=count,
        context_text=context_text,
    )
    return result


@router.get("/seeds")
async def get_seeds(
    cpc_prefix: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get seed data for idea generation context (expiring patents, trends)."""
    logger.info("ideas.seeds", cpc_prefix=cpc_prefix)

    result = await idea_service.get_seeds(session, cpc_prefix=cpc_prefix)
    return result
