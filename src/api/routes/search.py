from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.search_service import search_service
from src.api.dependencies.auth import RequestUserContext, get_optional_request_user
from src.api.schemas.search import SearchRequest, SearchResponse, SearchResultItem
from src.database.connection import get_session
from src.services.activity_service import activity_service
from src.utils.logger import logger

router = APIRouter()


@router.post("", response_model=SearchResponse)
async def search_patents(
    request: SearchRequest,
    http_request: Request,
    request_user: RequestUserContext | None = Depends(get_optional_request_user),
    session: AsyncSession = Depends(get_session),
) -> SearchResponse:
    """
    Search patents using full-text, semantic, or hybrid search.

    - **fulltext**: PostgreSQL trigram similarity search across title, abstract, assignee
    - **semantic**: PatentSBERTa embedding cosine similarity via pgvector
    - **hybrid**: Reciprocal Rank Fusion combining both approaches (default)
    """
    filters: dict[str, Any] = {}
    if request.country:
        filters["country"] = request.country
    if request.status:
        filters["status"] = request.status
    if request.assignee:
        filters["assignee"] = request.assignee
    if request.cpc_codes:
        filters["cpc_codes"] = request.cpc_codes
    if request.date_from:
        filters["date_from"] = request.date_from
    if request.date_to:
        filters["date_to"] = request.date_to

    logger.info(
        "search.query",
        query=request.query,
        search_type=request.search_type,
        filters=filters,
    )

    if request.search_type == "semantic":
        results, total = await search_service.semantic_search(
            session, request.query, filters, request.page, request.per_page
        )
    elif request.search_type == "fulltext":
        results, total = await search_service.fulltext_search(
            session, request.query, filters, request.page, request.per_page
        )
    else:
        results, total = await search_service.hybrid_search(
            session, request.query, filters, request.page, request.per_page
        )

    await activity_service.log_event(
        session,
        event_type="search.query",
        user_id=request_user.user_id if request_user else None,
        resource_type="search",
        event_metadata={
            "query": request.query,
            "search_type": request.search_type,
            "result_count": len(results),
            "page": request.page,
        },
        ip_address=http_request.client.host if http_request.client else None,
        user_agent=http_request.headers.get("User-Agent"),
    )

    return SearchResponse(
        results=[SearchResultItem(**r) for r in results],
        total=total,
        query=request.query,
        search_type=request.search_type,
        page=request.page,
        per_page=request.per_page,
    )
