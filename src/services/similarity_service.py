"""Patent similarity and prior art discovery service.

Uses PatentSBERTa embeddings for semantic similarity and citation
networks for prior art analysis.
"""
from datetime import date

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.patent import Patent, Citation
from src.utils.logger import logger


class SimilarityService:
    """Service for finding similar patents and prior art."""

    def __init__(self):
        self._embedding_service = None

    @property
    def embedding_service(self):
        if self._embedding_service is None:
            from src.ai.embeddings import embedding_service
            self._embedding_service = embedding_service
        return self._embedding_service

    async def find_similar_patents(
        self,
        session: AsyncSession,
        patent_number: str | None = None,
        text_query: str | None = None,
        top_k: int = 20,
        min_score: float = 0.5,
        exclude_same_assignee: bool = False,
        country: str | None = None,
        cpc_code: str | None = None,
    ) -> list[dict]:
        """
        Find patents similar to a given patent or text query.

        Uses cosine similarity on PatentSBERTa embeddings.
        Either patent_number or text_query must be provided.
        """
        if patent_number:
            query_embedding = await self._get_patent_embedding(session, patent_number)
            if query_embedding is None:
                # Generate embedding from patent text
                patent = await self._get_patent(session, patent_number)
                if not patent:
                    return []
                text = f"{patent.title} {patent.abstract or ''}"
                query_embedding = self.embedding_service.generate_embedding(text)
        elif text_query:
            query_embedding = self.embedding_service.generate_embedding(text_query)
        else:
            return []

        # Build similarity query
        distance = Patent.embedding.cosine_distance(query_embedding)
        similarity = (1 - distance).label("similarity_score")

        conditions = [Patent.embedding.isnot(None)]

        if patent_number:
            conditions.append(Patent.patent_number != patent_number)

        if country:
            conditions.append(Patent.country == country)

        if cpc_code:
            conditions.append(Patent.cpc_codes.any(cpc_code))

        query = (
            select(Patent, similarity)
            .where(and_(*conditions))
            .order_by(distance)
            .limit(top_k * 2)  # Fetch extra for post-filtering
        )

        result = await session.execute(query)
        rows = result.all()

        # Post-filter and format results
        similar_patents = []
        source_assignee = None

        if exclude_same_assignee and patent_number:
            source_patent = await self._get_patent(session, patent_number)
            if source_patent:
                source_assignee = source_patent.assignee_organization

        for row in rows:
            patent = row[0]
            score = float(row[1]) if row[1] else 0.0

            if score < min_score:
                continue

            if exclude_same_assignee and source_assignee:
                if patent.assignee_organization == source_assignee:
                    continue

            similar_patents.append(self._to_similarity_result(patent, score))

            if len(similar_patents) >= top_k:
                break

        return similar_patents

    async def find_prior_art(
        self,
        session: AsyncSession,
        patent_number: str | None = None,
        text_query: str | None = None,
        filing_date_before: date | None = None,
        top_k: int = 20,
        min_score: float = 0.4,
    ) -> dict:
        """
        Find potential prior art for a patent or invention concept.

        Combines semantic similarity with citation analysis.
        Prior art must predate the filing date of the target patent.
        """
        target_patent = None
        if patent_number:
            target_patent = await self._get_patent(session, patent_number)
            if target_patent and not filing_date_before:
                filing_date_before = target_patent.filing_date

        # Semantic prior art (similar patents filed before target)
        semantic_results = await self._semantic_prior_art(
            session,
            patent_number=patent_number,
            text_query=text_query,
            before_date=filing_date_before,
            top_k=top_k,
            min_score=min_score,
        )

        # Citation-based prior art (what does this patent cite?)
        citation_results = []
        if patent_number:
            citation_results = await self._citation_prior_art(
                session, patent_number, top_k=top_k
            )

        # Merge and deduplicate
        seen = set()
        combined = []

        for item in citation_results:
            if item["patent_number"] not in seen:
                item["source"] = "citation"
                combined.append(item)
                seen.add(item["patent_number"])

        for item in semantic_results:
            if item["patent_number"] not in seen:
                item["source"] = "semantic"
                combined.append(item)
                seen.add(item["patent_number"])
            else:
                # Patent found in both - boost score
                for existing in combined:
                    if existing["patent_number"] == item["patent_number"]:
                        existing["source"] = "both"
                        existing["similarity_score"] = max(
                            existing.get("similarity_score", 0),
                            item.get("similarity_score", 0),
                        )

        # Sort by score
        combined.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)

        return {
            "target_patent": patent_number,
            "target_filing_date": filing_date_before.isoformat() if filing_date_before else None,
            "prior_art": combined[:top_k],
            "total_found": len(combined),
            "semantic_count": len(semantic_results),
            "citation_count": len(citation_results),
        }

    async def get_patent_landscape(
        self,
        session: AsyncSession,
        patent_number: str,
        radius: int = 10,
    ) -> dict:
        """
        Get the patent landscape around a specific patent.

        Returns similar patents, citing patents, cited patents,
        and competitive context.
        """
        target = await self._get_patent(session, patent_number)
        if not target:
            return {"error": "Patent not found"}

        # Similar patents
        similar = await self.find_similar_patents(
            session, patent_number=patent_number, top_k=radius
        )

        # Patents this one cites
        cited_by_target = await self._get_citations_made(session, patent_number, limit=radius)

        # Patents that cite this one
        citing_target = await self._get_cited_by(session, patent_number, limit=radius)

        # Assignee competition (same CPC codes, different assignees)
        competitors = await self._get_competitors(session, target, limit=5)

        return {
            "target": self._to_similarity_result(target, 1.0),
            "similar_patents": similar,
            "cited_patents": cited_by_target,
            "citing_patents": citing_target,
            "competitors": competitors,
        }

    async def _semantic_prior_art(
        self,
        session: AsyncSession,
        patent_number: str | None,
        text_query: str | None,
        before_date: date | None,
        top_k: int,
        min_score: float,
    ) -> list[dict]:
        """Find semantically similar patents filed before a given date."""
        if patent_number:
            embedding = await self._get_patent_embedding(session, patent_number)
            if embedding is None:
                patent = await self._get_patent(session, patent_number)
                if not patent:
                    return []
                text = f"{patent.title} {patent.abstract or ''}"
                embedding = self.embedding_service.generate_embedding(text)
        elif text_query:
            embedding = self.embedding_service.generate_embedding(text_query)
        else:
            return []

        distance = Patent.embedding.cosine_distance(embedding)
        similarity = (1 - distance).label("similarity_score")

        conditions = [Patent.embedding.isnot(None)]
        if patent_number:
            conditions.append(Patent.patent_number != patent_number)
        if before_date:
            conditions.append(Patent.filing_date < before_date)

        query = (
            select(Patent, similarity)
            .where(and_(*conditions))
            .order_by(distance)
            .limit(top_k)
        )

        result = await session.execute(query)
        rows = result.all()

        results = []
        for row in rows:
            patent = row[0]
            score = float(row[1]) if row[1] else 0.0
            if score >= min_score:
                results.append(self._to_similarity_result(patent, score))

        return results

    async def _citation_prior_art(
        self,
        session: AsyncSession,
        patent_number: str,
        top_k: int,
    ) -> list[dict]:
        """Get patents cited by the target patent (these are prior art)."""
        target = await self._get_patent(session, patent_number)
        if not target:
            return []

        query = (
            select(Citation, Patent)
            .join(Patent, Citation.cited_patent_id == Patent.id)
            .where(Citation.citing_patent_id == target.id)
            .limit(top_k)
        )

        result = await session.execute(query)
        rows = result.all()

        return [
            self._to_similarity_result(row[1], 0.8)  # Citations get a base relevance
            for row in rows
        ]

    async def _get_citations_made(
        self,
        session: AsyncSession,
        patent_number: str,
        limit: int,
    ) -> list[dict]:
        """Get patents cited by this patent."""
        target = await self._get_patent(session, patent_number)
        if not target:
            return []

        query = (
            select(Patent)
            .join(Citation, Citation.cited_patent_id == Patent.id)
            .where(Citation.citing_patent_id == target.id)
            .limit(limit)
        )

        result = await session.execute(query)
        patents = result.scalars().all()
        return [self._to_similarity_result(p, 0.0) for p in patents]

    async def _get_cited_by(
        self,
        session: AsyncSession,
        patent_number: str,
        limit: int,
    ) -> list[dict]:
        """Get patents that cite this patent."""
        target = await self._get_patent(session, patent_number)
        if not target:
            return []

        query = (
            select(Patent)
            .join(Citation, Citation.citing_patent_id == Patent.id)
            .where(Citation.cited_patent_id == target.id)
            .limit(limit)
        )

        result = await session.execute(query)
        patents = result.scalars().all()
        return [self._to_similarity_result(p, 0.0) for p in patents]

    async def _get_competitors(
        self,
        session: AsyncSession,
        target: Patent,
        limit: int,
    ) -> list[dict]:
        """Find competing assignees in the same technology area."""
        if not target.cpc_codes:
            return []

        # Get top-level CPC sections (first 4 chars)
        cpc_prefixes = list({code[:4] for code in target.cpc_codes if len(code) >= 4})[:3]

        conditions = [
            Patent.assignee_organization.isnot(None),
            Patent.assignee_organization != target.assignee_organization,
        ]

        # Match any CPC prefix
        cpc_conditions = [
            Patent.cpc_codes.any(prefix) for prefix in cpc_prefixes
        ]
        if cpc_conditions:
            conditions.append(or_(*cpc_conditions))

        query = (
            select(
                Patent.assignee_organization,
                func.count(Patent.id).label("patent_count"),
            )
            .where(and_(*conditions))
            .group_by(Patent.assignee_organization)
            .order_by(func.count(Patent.id).desc())
            .limit(limit)
        )

        result = await session.execute(query)
        rows = result.all()

        return [
            {"assignee": row[0], "patent_count": row[1]}
            for row in rows
        ]

    async def _get_patent(self, session: AsyncSession, patent_number: str) -> Patent | None:
        """Fetch a patent by number."""
        result = await session.execute(
            select(Patent).where(Patent.patent_number == patent_number)
        )
        return result.scalar_one_or_none()

    async def _get_patent_embedding(
        self, session: AsyncSession, patent_number: str
    ) -> list[float] | None:
        """Get the embedding vector for a patent."""
        result = await session.execute(
            select(Patent.embedding).where(
                Patent.patent_number == patent_number,
                Patent.embedding.isnot(None),
            )
        )
        embedding = result.scalar_one_or_none()
        return list(embedding) if embedding else None

    @staticmethod
    def _to_similarity_result(patent: Patent, score: float) -> dict:
        """Convert a patent to a similarity result dict."""
        return {
            "patent_number": patent.patent_number,
            "title": patent.title,
            "abstract": patent.abstract,
            "filing_date": patent.filing_date.isoformat() if patent.filing_date else None,
            "grant_date": patent.grant_date.isoformat() if patent.grant_date else None,
            "assignee_organization": patent.assignee_organization,
            "cpc_codes": patent.cpc_codes,
            "country": patent.country,
            "status": patent.status,
            "citation_count": patent.citation_count,
            "similarity_score": round(score, 4),
        }


similarity_service = SimilarityService()
