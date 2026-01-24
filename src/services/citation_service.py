"""Citation network and trend analysis service.

Provides citation graph traversal, technology trend analysis,
and competitive landscape insights.
"""
from datetime import date, timedelta

from sqlalchemy import select, func, and_, extract, case, text, column
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.patent import Patent, Citation
from src.utils.logger import logger


class CitationService:
    """Service for citation network analysis and technology trends."""

    async def get_citation_network(
        self,
        session: AsyncSession,
        patent_number: str,
        depth: int = 2,
        max_nodes: int = 50,
    ) -> dict:
        """
        Build a citation network graph around a patent.

        Returns nodes (patents) and edges (citations) for visualization.
        """
        target = await self._get_patent(session, patent_number)
        if not target:
            return {"error": "Patent not found"}

        nodes: dict[str, dict] = {}
        edges: list[dict] = []
        edge_set: set[tuple[str, str, str]] = set()
        visited: set[int] = set()

        # Add target node
        nodes[patent_number] = self._to_node(target, depth=0)
        visited.add(target.id)

        # BFS through citation graph
        current_level = [target]
        for level in range(1, depth + 1):
            next_level = []
            if len(nodes) >= max_nodes:
                break

            for patent in current_level:
                # Forward citations (patents this one cites)
                cited = await self._get_forward_citations(session, patent.id)
                for citation, cited_patent in cited:
                    if len(nodes) >= max_nodes:
                        break
                    if cited_patent and cited_patent.id not in visited:
                        nodes[cited_patent.patent_number] = self._to_node(cited_patent, depth=level)
                        visited.add(cited_patent.id)
                        next_level.append(cited_patent)
                    target_num = cited_patent.patent_number if cited_patent else citation.cited_patent_number
                    edge_key = (patent.patent_number, target_num, "cites")
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        edges.append({
                            "source": patent.patent_number,
                            "target": target_num,
                            "type": "cites",
                        })

                # Backward citations (patents that cite this one)
                citing = await self._get_backward_citations(session, patent.id)
                for citation, citing_patent in citing:
                    if len(nodes) >= max_nodes:
                        break
                    if citing_patent and citing_patent.id not in visited:
                        nodes[citing_patent.patent_number] = self._to_node(citing_patent, depth=level)
                        visited.add(citing_patent.id)
                        next_level.append(citing_patent)
                    source_num = citing_patent.patent_number if citing_patent else "unknown"
                    edge_key = (source_num, patent.patent_number, "cited_by")
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        edges.append({
                            "source": source_num,
                            "target": patent.patent_number,
                            "type": "cited_by",
                        })

            current_level = next_level

        return {
            "center": patent_number,
            "nodes": list(nodes.values()),
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "depth": depth,
        }

    async def get_technology_trends(
        self,
        session: AsyncSession,
        cpc_prefix: str | None = None,
        country: str | None = None,
        years: int = 10,
        top_n: int = 10,
    ) -> dict:
        """
        Analyze technology trends based on patent filing patterns.

        Returns yearly filing counts by CPC section and growth rates.
        """
        current_year = date.today().year
        start_year = current_year - years

        # Overall yearly patent counts
        yearly_counts = await self._get_yearly_counts(
            session, start_year, current_year, country
        )

        # Top CPC sections by recent filings
        top_cpc = await self._get_top_cpc_trends(
            session, start_year, current_year, country, cpc_prefix, top_n
        )

        # Growth analysis
        growth_leaders = await self._get_growth_leaders(
            session, start_year, current_year, country, top_n
        )

        # Top assignees
        top_assignees = await self._get_top_assignees(
            session, start_year, current_year, country, top_n
        )

        return {
            "period": {"start_year": start_year, "end_year": current_year},
            "yearly_totals": yearly_counts,
            "top_cpc_trends": top_cpc,
            "growth_leaders": growth_leaders,
            "top_assignees": top_assignees,
        }

    async def get_citation_stats(
        self,
        session: AsyncSession,
        patent_number: str,
    ) -> dict:
        """Get citation statistics for a patent."""
        target = await self._get_patent(session, patent_number)
        if not target:
            return {"error": "Patent not found"}

        # Count forward citations
        forward_count = (await session.execute(
            select(func.count(Citation.id)).where(
                Citation.citing_patent_id == target.id
            )
        )).scalar() or 0

        # Count backward citations
        backward_count = (await session.execute(
            select(func.count(Citation.id)).where(
                Citation.cited_patent_id == target.id
            )
        )).scalar() or 0

        # Average citations for same year/CPC
        avg_citations = None
        if target.filing_date and target.cpc_codes:
            year = target.filing_date.year
            avg_result = await session.execute(
                select(func.avg(Patent.cited_by_count)).where(and_(
                    extract("year", Patent.filing_date) == year,
                    Patent.cpc_codes.overlap(target.cpc_codes[:1]),
                ))
            )
            avg_citations = float(avg_result.scalar() or 0)

        return {
            "patent_number": patent_number,
            "forward_citations": forward_count,
            "backward_citations": backward_count,
            "avg_field_citations": round(avg_citations, 1) if avg_citations else None,
            "citation_index": round(backward_count / avg_citations, 2) if avg_citations and avg_citations > 0 else None,
        }

    async def _get_forward_citations(
        self, session: AsyncSession, patent_id: int, limit: int = 20
    ) -> list[tuple]:
        """Get patents cited by this patent."""
        result = await session.execute(
            select(Citation, Patent)
            .outerjoin(Patent, Citation.cited_patent_id == Patent.id)
            .where(Citation.citing_patent_id == patent_id)
            .limit(limit)
        )
        return result.all()

    async def _get_backward_citations(
        self, session: AsyncSession, patent_id: int, limit: int = 20
    ) -> list[tuple]:
        """Get patents that cite this patent."""
        result = await session.execute(
            select(Citation, Patent)
            .join(Patent, Citation.citing_patent_id == Patent.id)
            .where(Citation.cited_patent_id == patent_id)
            .limit(limit)
        )
        return result.all()

    async def _get_yearly_counts(
        self, session: AsyncSession, start_year: int, end_year: int, country: str | None
    ) -> list[dict]:
        """Get patent filing counts by year."""
        conditions = [
            extract("year", Patent.filing_date) >= start_year,
            extract("year", Patent.filing_date) <= end_year,
            Patent.filing_date.isnot(None),
        ]
        if country:
            conditions.append(Patent.country == country)

        result = await session.execute(
            select(
                extract("year", Patent.filing_date).label("year"),
                func.count(Patent.id).label("count"),
            )
            .where(and_(*conditions))
            .group_by("year")
            .order_by("year")
        )

        return [{"year": int(row[0]), "count": row[1]} for row in result.all()]

    async def _get_top_cpc_trends(
        self,
        session: AsyncSession,
        start_year: int,
        end_year: int,
        country: str | None,
        cpc_prefix: str | None,
        top_n: int,
    ) -> list[dict]:
        """Get top CPC codes with yearly breakdown."""
        conditions = [
            extract("year", Patent.filing_date) >= start_year,
            Patent.filing_date.isnot(None),
            Patent.cpc_codes.isnot(None),
        ]
        if country:
            conditions.append(Patent.country == country)

        # Get top CPC codes overall
        cpc_unnest = func.unnest(Patent.cpc_codes).label("cpc_code")

        top_query = (
            select(cpc_unnest, func.count(Patent.id).label("total"))
            .where(and_(*conditions))
        )

        if cpc_prefix:
            top_query = top_query.having(
                column("cpc_code").like(f"{cpc_prefix}%")
            )

        top_query = (
            top_query
            .group_by("cpc_code")
            .order_by(func.count(Patent.id).desc())
            .limit(top_n)
        )

        result = await session.execute(top_query)
        top_codes = result.all()

        # Deduplicate by 4-char prefix and aggregate counts
        prefix_totals: dict[str, int] = {}
        for row in top_codes:
            code = row[0]
            code_prefix = code[:4] if len(code) >= 4 else code
            prefix_totals[code_prefix] = prefix_totals.get(code_prefix, 0) + row[1]

        trends = [
            {"cpc_code": code, "total_patents": total}
            for code, total in sorted(prefix_totals.items(), key=lambda x: x[1], reverse=True)
        ]

        return trends[:top_n]

    async def _get_growth_leaders(
        self,
        session: AsyncSession,
        start_year: int,
        end_year: int,
        country: str | None,
        top_n: int,
    ) -> list[dict]:
        """Find CPC codes with highest growth rate."""
        mid_year = start_year + (end_year - start_year) // 2

        conditions_base = [
            Patent.filing_date.isnot(None),
            Patent.cpc_codes.isnot(None),
        ]
        if country:
            conditions_base.append(Patent.country == country)

        # Recent period count
        recent_conditions = conditions_base + [
            extract("year", Patent.filing_date) >= mid_year,
            extract("year", Patent.filing_date) <= end_year,
        ]

        # Earlier period count
        earlier_conditions = conditions_base + [
            extract("year", Patent.filing_date) >= start_year,
            extract("year", Patent.filing_date) < mid_year,
        ]

        cpc_unnest = func.unnest(Patent.cpc_codes).label("cpc_code")

        recent_result = await session.execute(
            select(cpc_unnest, func.count(Patent.id).label("count"))
            .where(and_(*recent_conditions))
            .group_by("cpc_code")
            .order_by(func.count(Patent.id).desc())
            .limit(50)
        )
        recent_counts = {row[0][:4]: row[1] for row in recent_result.all()}

        earlier_result = await session.execute(
            select(cpc_unnest, func.count(Patent.id).label("count"))
            .where(and_(*earlier_conditions))
            .group_by("cpc_code")
            .order_by(func.count(Patent.id).desc())
            .limit(50)
        )
        earlier_counts = {row[0][:4]: row[1] for row in earlier_result.all()}

        # Calculate growth
        growth = []
        for code, recent in recent_counts.items():
            earlier = earlier_counts.get(code, 0)
            if earlier > 5:  # Min threshold to avoid noise
                growth_rate = (recent - earlier) / earlier
                growth.append({
                    "cpc_code": code,
                    "recent_count": recent,
                    "earlier_count": earlier,
                    "growth_rate": round(growth_rate, 3),
                })

        growth.sort(key=lambda x: x["growth_rate"], reverse=True)
        return growth[:top_n]

    async def _get_top_assignees(
        self,
        session: AsyncSession,
        start_year: int,
        end_year: int,
        country: str | None,
        top_n: int,
    ) -> list[dict]:
        """Get top patent filers."""
        conditions = [
            Patent.assignee_organization.isnot(None),
            extract("year", Patent.filing_date) >= start_year,
            Patent.filing_date.isnot(None),
        ]
        if country:
            conditions.append(Patent.country == country)

        result = await session.execute(
            select(
                Patent.assignee_organization,
                func.count(Patent.id).label("patent_count"),
            )
            .where(and_(*conditions))
            .group_by(Patent.assignee_organization)
            .order_by(func.count(Patent.id).desc())
            .limit(top_n)
        )

        return [
            {"assignee": row[0], "patent_count": row[1]}
            for row in result.all()
        ]

    async def _get_patent(self, session: AsyncSession, patent_number: str) -> Patent | None:
        result = await session.execute(
            select(Patent).where(Patent.patent_number == patent_number)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _to_node(patent: Patent, depth: int) -> dict:
        return {
            "patent_number": patent.patent_number,
            "title": patent.title,
            "assignee_organization": patent.assignee_organization,
            "filing_date": patent.filing_date.isoformat() if patent.filing_date else None,
            "country": patent.country,
            "status": patent.status,
            "cpc_codes": patent.cpc_codes,
            "citation_count": patent.citation_count,
            "cited_by_count": patent.cited_by_count,
            "depth": depth,
        }


citation_service = CitationService()
