from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.patent import Patent


def _escape_like(value: str) -> str:
    """Escape special characters for LIKE/ILIKE queries."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class PatentSearchService:
    """Service for full-text, semantic, and hybrid patent search."""

    def __init__(self):
        self._embedding_service = None

    @property
    def embedding_service(self):
        if self._embedding_service is None:
            from src.ai.embeddings import embedding_service

            self._embedding_service = embedding_service
        return self._embedding_service

    async def fulltext_search(
        self,
        session: AsyncSession,
        query: str,
        filters: dict | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[dict], int]:
        """
        Full-text search using PostgreSQL ts_rank with trigram similarity fallback.
        """
        offset = (page - 1) * per_page

        # Build the search query using ILIKE for broad matching
        # and ts_rank for ranking when available
        escaped_query = _escape_like(query)
        search_condition = or_(
            Patent.title.ilike(f"%{escaped_query}%"),
            Patent.abstract.ilike(f"%{escaped_query}%"),
            Patent.patent_number.ilike(f"%{escaped_query}%"),
            Patent.assignee_organization.ilike(f"%{escaped_query}%"),
        )

        # Build base query with relevance scoring
        # Use similarity for ranking
        relevance = func.greatest(
            func.coalesce(func.similarity(Patent.title, query), 0.0),
            func.coalesce(func.similarity(Patent.abstract, query), 0.0),
        ).label("relevance_score")

        base_query = select(Patent, relevance).where(search_condition)
        base_query = self._apply_filters(base_query, filters)

        # Count total
        count_query = select(func.count()).select_from(base_query.subquery())
        total = (await session.execute(count_query)).scalar() or 0

        # Fetch results ordered by relevance
        results_query = (
            base_query.order_by(text("relevance_score DESC")).offset(offset).limit(per_page)
        )

        result = await session.execute(results_query)
        rows = result.all()

        patents = []
        for row in rows:
            patent = row[0]
            score = float(row[1]) if row[1] is not None else 0.0
            patents.append(self._patent_to_result(patent, score))

        return patents, total

    async def semantic_search(
        self,
        session: AsyncSession,
        query: str,
        filters: dict | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[dict], int]:
        """
        Semantic search using PatentSBERTa embeddings and pgvector cosine distance.
        """
        offset = (page - 1) * per_page

        # Generate query embedding
        query_embedding = self.embedding_service.generate_embedding(query)

        # Build query with cosine distance
        distance = Patent.embedding.cosine_distance(query_embedding)
        relevance = (1 - distance).label("relevance_score")

        base_query = select(Patent, relevance).where(Patent.embedding.isnot(None))
        base_query = self._apply_filters(base_query, filters)

        # Count total matching patents with embeddings
        count_query = select(func.count()).select_from(
            select(Patent.id).where(Patent.embedding.isnot(None)).subquery()
        )
        if filters:
            count_base = select(Patent.id).where(Patent.embedding.isnot(None))
            count_base = self._apply_filters(count_base, filters)
            count_query = select(func.count()).select_from(count_base.subquery())

        total = (await session.execute(count_query)).scalar() or 0

        # Fetch nearest neighbors
        results_query = (
            base_query.order_by(Patent.embedding.cosine_distance(query_embedding))
            .offset(offset)
            .limit(per_page)
        )

        result = await session.execute(results_query)
        rows = result.all()

        patents = []
        for row in rows:
            patent = row[0]
            score = float(row[1]) if row[1] is not None else 0.0
            patents.append(self._patent_to_result(patent, max(0, score)))

        return patents, total

    async def hybrid_search(
        self,
        session: AsyncSession,
        query: str,
        filters: dict | None = None,
        page: int = 1,
        per_page: int = 20,
        semantic_weight: float = 0.6,
    ) -> tuple[list[dict], int]:
        """
        Hybrid search combining full-text and semantic results.

        Uses Reciprocal Rank Fusion (RRF) to merge rankings.
        """
        # Try semantic first, fall back to fulltext if no embeddings
        has_embeddings = await session.execute(
            select(func.count(Patent.id)).where(Patent.embedding.isnot(None)).limit(1)
        )
        embedding_count = has_embeddings.scalar() or 0

        if embedding_count == 0:
            # No embeddings available, fall back to fulltext
            return await self.fulltext_search(session, query, filters, page, per_page)

        # Get both result sets (larger window for fusion)
        fusion_limit = per_page * 3

        fulltext_results, ft_total = await self.fulltext_search(
            session, query, filters, page=1, per_page=fusion_limit
        )
        semantic_results, sem_total = await self.semantic_search(
            session, query, filters, page=1, per_page=fusion_limit
        )

        # Reciprocal Rank Fusion
        rrf_scores: dict[str, float] = {}
        patent_data: dict[str, dict] = {}
        k = 60  # RRF constant

        for rank, result in enumerate(fulltext_results):
            patent_num = result["patent_number"]
            rrf_scores[patent_num] = rrf_scores.get(patent_num, 0) + (1 - semantic_weight) / (
                k + rank + 1
            )
            patent_data[patent_num] = result

        for rank, result in enumerate(semantic_results):
            patent_num = result["patent_number"]
            rrf_scores[patent_num] = rrf_scores.get(patent_num, 0) + semantic_weight / (
                k + rank + 1
            )
            patent_data[patent_num] = result

        # Sort by RRF score
        sorted_patents = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        # Paginate
        offset = (page - 1) * per_page
        page_results = sorted_patents[offset : offset + per_page]

        # Normalize RRF scores to [0, 1] range
        max_rrf = sorted_patents[0][1] if sorted_patents else 1.0
        results = []
        for patent_num, score in page_results:
            data = patent_data[patent_num].copy()
            data["relevance_score"] = round(score / max_rrf, 4) if max_rrf > 0 else 0.0
            results.append(data)

        total = len(rrf_scores)
        return results, total

    def _apply_filters(self, query, filters: dict | None):
        """Apply search filters to a query."""
        if not filters:
            return query

        if filters.get("country"):
            query = query.where(Patent.country == filters["country"])
        if filters.get("status"):
            query = query.where(Patent.status == filters["status"])
        if filters.get("assignee"):
            query = query.where(
                Patent.assignee_organization.ilike(f"%{_escape_like(filters['assignee'])}%")
            )
        if filters.get("cpc_codes"):
            # Check if any CPC code matches
            query = query.where(Patent.cpc_codes.overlap(filters["cpc_codes"]))
        if filters.get("date_from"):
            query = query.where(Patent.filing_date >= filters["date_from"])
        if filters.get("date_to"):
            query = query.where(Patent.filing_date <= filters["date_to"])

        return query

    @staticmethod
    def _patent_to_result(patent: Patent, relevance_score: float) -> dict:
        """Convert a Patent model to a search result dict."""
        return {
            "patent_number": patent.patent_number,
            "title": patent.title,
            "abstract": patent.abstract,
            "filing_date": patent.filing_date.isoformat() if patent.filing_date else None,
            "grant_date": patent.grant_date.isoformat() if patent.grant_date else None,
            "expiration_date": patent.expiration_date.isoformat()
            if patent.expiration_date
            else None,
            "assignee_organization": patent.assignee_organization,
            "inventors": patent.inventors,
            "cpc_codes": patent.cpc_codes,
            "status": patent.status,
            "country": patent.country,
            "citation_count": patent.citation_count,
            "relevance_score": round(relevance_score, 4),
        }


search_service = PatentSearchService()
