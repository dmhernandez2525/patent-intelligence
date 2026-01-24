from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session
from src.api.schemas.similarity import (
    SimilarityRequest,
    SimilarityResponse,
    PriorArtRequest,
    PriorArtResponse,
    LandscapeResponse,
)
from src.services.similarity_service import similarity_service
from src.utils.logger import logger

router = APIRouter()


@router.post("/similar", response_model=SimilarityResponse)
async def find_similar_patents(
    request: SimilarityRequest,
    session: AsyncSession = Depends(get_session),
) -> SimilarityResponse:
    """Find patents similar to a given patent or text query."""
    if not request.patent_number and not request.text_query:
        raise HTTPException(
            status_code=400,
            detail="Either patent_number or text_query must be provided",
        )

    logger.info(
        "similarity.search",
        patent_number=request.patent_number,
        text_query=request.text_query[:50] if request.text_query else None,
        top_k=request.top_k,
    )

    results = await similarity_service.find_similar_patents(
        session,
        patent_number=request.patent_number,
        text_query=request.text_query,
        top_k=request.top_k,
        min_score=request.min_score,
        exclude_same_assignee=request.exclude_same_assignee,
        country=request.country,
        cpc_code=request.cpc_code,
    )

    return SimilarityResponse(
        results=results,
        query_patent=request.patent_number,
        query_text=request.text_query,
        total_found=len(results),
    )


@router.post("/prior-art", response_model=PriorArtResponse)
async def find_prior_art(
    request: PriorArtRequest,
    session: AsyncSession = Depends(get_session),
) -> PriorArtResponse:
    """Find potential prior art for a patent or invention concept."""
    if not request.patent_number and not request.text_query:
        raise HTTPException(
            status_code=400,
            detail="Either patent_number or text_query must be provided",
        )

    logger.info(
        "similarity.prior_art",
        patent_number=request.patent_number,
        text_query=request.text_query[:50] if request.text_query else None,
    )

    result = await similarity_service.find_prior_art(
        session,
        patent_number=request.patent_number,
        text_query=request.text_query,
        filing_date_before=request.filing_date_before,
        top_k=request.top_k,
        min_score=request.min_score,
    )

    return PriorArtResponse(**result)


@router.get("/landscape/{patent_number}", response_model=LandscapeResponse)
async def get_patent_landscape(
    patent_number: str,
    radius: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> LandscapeResponse:
    """Get the patent landscape around a specific patent."""
    logger.info("similarity.landscape", patent_number=patent_number, radius=radius)

    result = await similarity_service.get_patent_landscape(
        session, patent_number=patent_number, radius=radius
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return LandscapeResponse(**result)
