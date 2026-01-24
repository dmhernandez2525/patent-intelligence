from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session
from src.api.schemas.search import SearchRequest, SearchResponse

router = APIRouter()


@router.post("", response_model=SearchResponse)
async def search_patents(
    request: SearchRequest,
    session: AsyncSession = Depends(get_session),
) -> SearchResponse:
    """Search patents using full-text or semantic search. Implemented in Phase 3."""
    return SearchResponse(
        results=[],
        total=0,
        query=request.query,
        search_type=request.search_type,
        page=request.page,
        per_page=request.per_page,
    )
