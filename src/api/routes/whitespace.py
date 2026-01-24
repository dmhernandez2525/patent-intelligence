"""API routes for white space discovery."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.whitespace import (
    CoverageResponse,
    CrossDomainResponse,
    SectionOverviewResponse,
    WhiteSpaceResponse,
)
from src.database.connection import get_session
from src.services.whitespace_service import whitespace_service
from src.utils.logger import logger

router = APIRouter()


@router.get("/coverage", response_model=CoverageResponse)
async def get_coverage_analysis(
    cpc_level: int = Query(default=4, ge=1, le=8, description="CPC hierarchy depth"),
    min_patents: int = Query(default=5, ge=1, le=100, description="Minimum patents per area"),
    years: int = Query(default=5, ge=1, le=20, description="Analysis time window in years"),
    session: AsyncSession = Depends(get_session),
) -> CoverageResponse:
    """
    Analyze CPC code coverage to identify technology density.

    Returns areas with patent counts, citation averages, and growth rates.
    Higher density_score indicates more crowded areas.
    """
    logger.info("whitespace.coverage", cpc_level=cpc_level, years=years)

    try:
        result = await whitespace_service.get_coverage_analysis(
            session,
            cpc_level=cpc_level,
            min_patents=min_patents,
            years=years,
        )
        return CoverageResponse(**result)
    except Exception as e:
        logger.error("whitespace.coverage_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to analyze coverage")


@router.get("/gaps", response_model=WhiteSpaceResponse)
async def get_white_spaces(
    cpc_prefix: str | None = Query(None, description="CPC prefix to focus analysis"),
    min_gap_score: float = Query(default=0.3, ge=0.0, le=1.0, description="Minimum gap score"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum results"),
    session: AsyncSession = Depends(get_session),
) -> WhiteSpaceResponse:
    """
    Identify technology white spaces (gaps with innovation opportunity).

    White spaces are areas with:
    - Declining patent activity
    - High-impact foundational patents
    - Low recent follow-up innovation

    Opportunity types:
    - abandoned_goldmine: High-impact area with sharp decline
    - dormant: Significant decline, very few recent patents
    - consolidation: Strong foundations, slowing innovation
    - emerging_gap: Moderate decline, potential opportunity
    """
    logger.info("whitespace.gaps", cpc_prefix=cpc_prefix, min_gap_score=min_gap_score)

    try:
        result = await whitespace_service.get_white_spaces(
            session,
            cpc_prefix=cpc_prefix,
            min_gap_score=min_gap_score,
            limit=limit,
        )
        return WhiteSpaceResponse(**result)
    except Exception as e:
        logger.error("whitespace.gaps_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to find white spaces")


@router.get("/cross-domain/{source_cpc}", response_model=CrossDomainResponse)
async def get_cross_domain_opportunities(
    source_cpc: str,
    max_results: int = Query(default=15, ge=1, le=50, description="Maximum opportunities"),
    session: AsyncSession = Depends(get_session),
) -> CrossDomainResponse:
    """
    Find cross-domain combination opportunities for a technology area.

    Identifies adjacent CPC areas that could be combined with the source
    area for novel inventions. Returns both emerging combinations (already
    being explored) and untapped opportunities.
    """
    if len(source_cpc) < 1:
        raise HTTPException(status_code=400, detail="source_cpc must be at least 1 character")

    logger.info("whitespace.cross_domain", source_cpc=source_cpc)

    try:
        result = await whitespace_service.get_cross_domain_opportunities(
            session,
            source_cpc=source_cpc,
            max_results=max_results,
        )
        return CrossDomainResponse(**result)
    except Exception as e:
        logger.error("whitespace.cross_domain_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to find cross-domain opportunities")


@router.get("/sections", response_model=SectionOverviewResponse)
async def get_section_overview(
    years: int = Query(default=5, ge=1, le=20, description="Analysis time window"),
    session: AsyncSession = Depends(get_session),
) -> SectionOverviewResponse:
    """
    Get high-level overview of patent activity by CPC section.

    Provides a bird's-eye view of the technology landscape with:
    - Market share by section
    - Recent activity momentum
    - High-impact patent counts
    - Growth trends
    """
    logger.info("whitespace.sections", years=years)

    try:
        result = await whitespace_service.get_section_overview(session, years=years)
        return SectionOverviewResponse(**result)
    except Exception as e:
        logger.error("whitespace.sections_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get section overview")
