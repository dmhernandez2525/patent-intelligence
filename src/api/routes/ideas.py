from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.ideas import IdeaRequest, IdeaResponse, SeedResponse
from src.database.connection import get_session
from src.services.idea_service import idea_service
from src.utils.logger import logger

router = APIRouter()


@router.post("/generate", response_model=IdeaResponse)
async def generate_ideas(
    request: IdeaRequest,
    session: AsyncSession = Depends(get_session),
) -> IdeaResponse:
    """Generate AI-powered invention ideas from patent landscape analysis."""
    logger.info(
        "ideas.generate",
        cpc_prefix=request.cpc_prefix,
        focus=request.focus,
        count=request.count,
    )

    result = await idea_service.generate_ideas(
        session,
        cpc_prefix=request.cpc_prefix,
        focus=request.focus,
        count=request.count,
        context_text=request.context_text,
    )
    return IdeaResponse(**result)


@router.get("/seeds", response_model=SeedResponse)
async def get_seeds(
    cpc_prefix: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> SeedResponse:
    """Get seed data for idea generation context (expiring patents, trends)."""
    logger.info("ideas.seeds", cpc_prefix=cpc_prefix)

    result = await idea_service.get_seeds(session, cpc_prefix=cpc_prefix)
    return SeedResponse(**result)
