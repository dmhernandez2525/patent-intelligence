from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session
from src.services.citation_service import citation_service
from src.utils.logger import logger

router = APIRouter()


@router.get("/trends")
async def get_trends(
    cpc_prefix: str | None = Query(None),
    country: str | None = Query(None),
    years: int = Query(default=10, ge=1, le=50),
    top_n: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get technology trend analysis based on patent filing patterns."""
    logger.info("analysis.trends", cpc_prefix=cpc_prefix, country=country, years=years)

    result = await citation_service.get_technology_trends(
        session,
        cpc_prefix=cpc_prefix,
        country=country,
        years=years,
        top_n=top_n,
    )
    return result


@router.get("/citations/{patent_number}")
async def get_citation_network(
    patent_number: str,
    depth: int = Query(default=2, ge=1, le=3),
    max_nodes: int = Query(default=50, ge=10, le=200),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get citation network graph for a patent."""
    logger.info("analysis.citations", patent_number=patent_number, depth=depth)

    result = await citation_service.get_citation_network(
        session,
        patent_number=patent_number,
        depth=depth,
        max_nodes=max_nodes,
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/citations/{patent_number}/stats")
async def get_citation_stats(
    patent_number: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get citation statistics for a patent."""
    logger.info("analysis.citation_stats", patent_number=patent_number)

    result = await citation_service.get_citation_stats(session, patent_number)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result
