"""White space discovery service for identifying technology gaps.

Analyzes patent landscape to find underserved technology areas,
declining sectors, and cross-domain opportunities.
"""

from datetime import date, timedelta

from sqlalchemy import and_, case, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.patent import Patent

# Standard CPC sections and their descriptions
CPC_SECTIONS = {
    "A": "Human Necessities",
    "B": "Operations & Transport",
    "C": "Chemistry & Metallurgy",
    "D": "Textiles & Paper",
    "E": "Fixed Constructions",
    "F": "Mechanical Engineering",
    "G": "Physics",
    "H": "Electricity",
    "Y": "Emerging Technologies",
}


class WhiteSpaceService:
    """Service for discovering technology gaps and opportunities."""

    async def get_coverage_analysis(
        self,
        session: AsyncSession,
        cpc_level: int = 4,
        min_patents: int = 5,
        years: int = 5,
    ) -> dict:
        """
        Analyze CPC code coverage to identify underserved areas.

        Args:
            session: Database session
            cpc_level: CPC hierarchy depth (1=section, 4=class, 8=subclass)
            min_patents: Minimum patent count to include
            years: Time window for analysis
        """
        today = date.today()
        start_date = today - timedelta(days=years * 365)

        # Get patent counts by CPC code prefix
        cpc_unnest = func.unnest(Patent.cpc_codes).label("cpc_full")
        cpc_prefix = func.substr(cpc_unnest, 1, cpc_level).label("cpc_prefix")

        coverage_query = (
            select(
                cpc_prefix,
                func.count(func.distinct(Patent.id)).label("patent_count"),
                func.avg(Patent.cited_by_count).label("avg_citations"),
                func.count(
                    case(
                        (extract("year", Patent.filing_date) >= today.year - 2, Patent.id),
                        else_=None,
                    )
                ).label("recent_count"),
            )
            .where(
                and_(
                    Patent.cpc_codes.isnot(None),
                    Patent.filing_date >= start_date,
                )
            )
            .group_by(cpc_prefix)
            .having(func.count(func.distinct(Patent.id)) >= min_patents)
            .order_by(func.count(func.distinct(Patent.id)).desc())
            .limit(100)
        )

        result = await session.execute(coverage_query)
        rows = result.all()

        # Calculate statistics
        if not rows:
            return {
                "coverage_areas": [],
                "total_areas": 0,
                "avg_patents_per_area": 0,
                "analysis_period_years": years,
                "cpc_level": cpc_level,
            }

        total_patents = sum(r[1] for r in rows)
        avg_patents = total_patents / len(rows) if rows else 0

        coverage_areas = []
        for row in rows:
            cpc_code = row[0]
            patent_count = row[1]
            avg_citations = float(row[2]) if row[2] else 0
            recent_count = row[3] or 0

            # Calculate growth rate (recent vs older)
            older_count = patent_count - recent_count
            growth_rate = (
                (recent_count - older_count / (years - 2)) / max(older_count / (years - 2), 1)
                if older_count > 0 and years > 2
                else 0
            )

            # Determine section description
            section = cpc_code[0] if cpc_code else ""
            section_name = CPC_SECTIONS.get(section, "Unknown")

            coverage_areas.append({
                "cpc_code": cpc_code,
                "section": section,
                "section_name": section_name,
                "patent_count": patent_count,
                "avg_citations": round(avg_citations, 2),
                "recent_count": recent_count,
                "growth_rate": round(growth_rate, 3),
                "density_score": round(patent_count / avg_patents, 2) if avg_patents > 0 else 0,
            })

        return {
            "coverage_areas": coverage_areas,
            "total_areas": len(coverage_areas),
            "avg_patents_per_area": round(avg_patents, 1),
            "analysis_period_years": years,
            "cpc_level": cpc_level,
        }

    async def get_white_spaces(
        self,
        session: AsyncSession,
        cpc_prefix: str | None = None,
        min_gap_score: float = 0.3,
        limit: int = 20,
    ) -> dict:
        """
        Identify technology white spaces (gaps with opportunity).

        White spaces are areas where:
        - Patent activity has declined
        - Coverage is low relative to adjacent areas
        - High-citation patents exist but few follow-ups

        Args:
            session: Database session
            cpc_prefix: Optional prefix to focus analysis
            min_gap_score: Minimum gap score threshold (0-1)
            limit: Maximum results to return
        """
        today = date.today()
        recent_start = today - timedelta(days=2 * 365)
        historical_start = today - timedelta(days=7 * 365)

        # Build base conditions
        conditions = [
            Patent.cpc_codes.isnot(None),
            Patent.filing_date >= historical_start,
        ]
        if cpc_prefix:
            conditions.append(
                func.array_to_string(Patent.cpc_codes, ",").ilike(f"%{cpc_prefix}%")
            )

        # Get historical vs recent activity by CPC subclass (first 8 chars)
        cpc_unnest = func.unnest(Patent.cpc_codes).label("cpc_full")
        cpc_subclass = func.substr(cpc_unnest, 1, 8).label("cpc_subclass")

        activity_query = (
            select(
                cpc_subclass,
                # Historical count (5-7 years ago)
                func.count(
                    case(
                        (
                            and_(
                                Patent.filing_date >= historical_start,
                                Patent.filing_date < recent_start,
                            ),
                            Patent.id,
                        ),
                        else_=None,
                    )
                ).label("historical_count"),
                # Recent count (last 2 years)
                func.count(
                    case(
                        (Patent.filing_date >= recent_start, Patent.id),
                        else_=None,
                    )
                ).label("recent_count"),
                # High-impact historical patents
                func.count(
                    case(
                        (
                            and_(
                                Patent.filing_date < recent_start,
                                Patent.cited_by_count >= 10,
                            ),
                            Patent.id,
                        ),
                        else_=None,
                    )
                ).label("high_impact_historical"),
                func.max(Patent.cited_by_count).label("max_citations"),
            )
            .where(and_(*conditions))
            .group_by(cpc_subclass)
            .having(
                # Must have historical activity
                func.count(
                    case(
                        (Patent.filing_date < recent_start, Patent.id),
                        else_=None,
                    )
                )
                >= 5
            )
        )

        result = await session.execute(activity_query)
        rows = result.all()

        white_spaces = []
        for row in rows:
            cpc_code = row[0]
            historical = row[1] or 0
            recent = row[2] or 0
            high_impact = row[3] or 0
            max_citations = row[4] or 0

            if historical == 0:
                continue

            # Calculate decline ratio
            # Normalize by time period (5 years historical vs 2 years recent)
            historical_annual = historical / 5
            recent_annual = recent / 2 if recent > 0 else 0

            if historical_annual == 0:
                decline_ratio = 0
            else:
                decline_ratio = max(0, (historical_annual - recent_annual) / historical_annual)

            # Gap score: combination of decline and high-impact presence
            impact_factor = min(1.0, high_impact / 5) if high_impact > 0 else 0
            gap_score = (decline_ratio * 0.6) + (impact_factor * 0.4)

            if gap_score < min_gap_score:
                continue

            section = cpc_code[0] if cpc_code else ""

            white_spaces.append({
                "cpc_code": cpc_code,
                "section": section,
                "section_name": CPC_SECTIONS.get(section, "Unknown"),
                "historical_patents": historical,
                "recent_patents": recent,
                "decline_ratio": round(decline_ratio, 3),
                "high_impact_count": high_impact,
                "max_citations": max_citations,
                "gap_score": round(gap_score, 3),
                "opportunity_type": self._classify_opportunity(decline_ratio, high_impact, recent),
            })

        # Sort by gap score descending
        white_spaces.sort(key=lambda x: x["gap_score"], reverse=True)

        return {
            "white_spaces": white_spaces[:limit],
            "total_found": len(white_spaces),
            "min_gap_score": min_gap_score,
            "analysis_window": {
                "historical_years": 5,
                "recent_years": 2,
            },
        }

    async def get_cross_domain_opportunities(
        self,
        session: AsyncSession,
        source_cpc: str,
        max_results: int = 15,
    ) -> dict:
        """
        Find cross-domain combination opportunities for a given CPC area.

        Identifies adjacent technology areas that could be combined
        with the source area for novel inventions.

        Args:
            session: Database session
            source_cpc: Source CPC code to find combinations for
            max_results: Maximum number of opportunities
        """
        today = date.today()
        start_date = today - timedelta(days=5 * 365)

        # Find patents that have both the source CPC and other CPCs
        # This identifies which areas are already being combined

        # First, get patents in the source area
        source_patents = (
            select(Patent.id)
            .where(
                and_(
                    func.array_to_string(Patent.cpc_codes, ",").ilike(f"%{source_cpc}%"),
                    Patent.filing_date >= start_date,
                    Patent.cpc_codes.isnot(None),
                )
            )
        ).subquery()

        # Find co-occurring CPC codes (different sections)
        cpc_unnest = func.unnest(Patent.cpc_codes).label("cpc_code")
        cpc_section = func.substr(cpc_unnest, 1, 1).label("cpc_section")
        source_section = source_cpc[0] if source_cpc else ""

        cooccurrence_query = (
            select(
                func.substr(cpc_unnest, 1, 4).label("adjacent_cpc"),
                cpc_section,
                func.count(func.distinct(Patent.id)).label("combo_count"),
                func.avg(Patent.cited_by_count).label("avg_citations"),
            )
            .where(
                and_(
                    Patent.id.in_(select(source_patents.c.id)),
                    cpc_section != source_section,  # Different section
                )
            )
            .group_by(func.substr(cpc_unnest, 1, 4), cpc_section)
            .having(func.count(func.distinct(Patent.id)) >= 2)
            .order_by(func.avg(Patent.cited_by_count).desc())
            .limit(max_results * 2)
        )

        result = await session.execute(cooccurrence_query)
        existing_combos = {row[0]: {"count": row[2], "avg_citations": float(row[3] or 0)} for row in result.all()}

        # Find areas with high activity that AREN'T being combined yet
        # These represent untapped opportunities
        high_activity_query = (
            select(
                func.substr(func.unnest(Patent.cpc_codes), 1, 4).label("cpc_class"),
                func.substr(func.unnest(Patent.cpc_codes), 1, 1).label("section"),
                func.count(func.distinct(Patent.id)).label("patent_count"),
                func.avg(Patent.cited_by_count).label("avg_citations"),
            )
            .where(
                and_(
                    Patent.filing_date >= start_date,
                    Patent.cpc_codes.isnot(None),
                    func.substr(func.unnest(Patent.cpc_codes), 1, 1) != source_section,
                )
            )
            .group_by(
                func.substr(func.unnest(Patent.cpc_codes), 1, 4),
                func.substr(func.unnest(Patent.cpc_codes), 1, 1),
            )
            .having(func.count(func.distinct(Patent.id)) >= 50)
            .order_by(func.count(func.distinct(Patent.id)).desc())
            .limit(50)
        )

        result = await session.execute(high_activity_query)
        potential_areas = result.all()

        opportunities = []
        for row in potential_areas:
            cpc_class = row[0]
            section = row[1]
            patent_count = row[2]
            avg_citations = float(row[3] or 0)

            existing = existing_combos.get(cpc_class)

            # Calculate opportunity score
            if existing:
                # Already being combined - score based on citation performance
                combo_lift = existing["avg_citations"] / max(avg_citations, 1)
                opportunity_score = min(1.0, combo_lift * 0.5)
                status = "emerging"
            else:
                # Not yet combined - higher opportunity
                opportunity_score = min(1.0, 0.5 + (patent_count / 1000))
                status = "untapped"

            opportunities.append({
                "cpc_code": cpc_class,
                "section": section,
                "section_name": CPC_SECTIONS.get(section, "Unknown"),
                "patent_count": patent_count,
                "avg_citations": round(avg_citations, 2),
                "existing_combinations": existing["count"] if existing else 0,
                "opportunity_score": round(opportunity_score, 3),
                "status": status,
            })

        # Sort by opportunity score
        opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)

        return {
            "source_cpc": source_cpc,
            "source_section": source_section,
            "source_section_name": CPC_SECTIONS.get(source_section, "Unknown"),
            "opportunities": opportunities[:max_results],
            "total_analyzed": len(potential_areas),
        }

    async def get_section_overview(
        self,
        session: AsyncSession,
        years: int = 5,
    ) -> dict:
        """
        Get high-level overview of patent activity by CPC section.

        Provides a bird's-eye view of the technology landscape.
        """
        today = date.today()
        start_date = today - timedelta(days=years * 365)
        recent_start = today - timedelta(days=2 * 365)

        cpc_unnest = func.unnest(Patent.cpc_codes).label("cpc_code")
        section = func.substr(cpc_unnest, 1, 1).label("section")

        overview_query = (
            select(
                section,
                func.count(func.distinct(Patent.id)).label("total_patents"),
                func.count(
                    case(
                        (Patent.filing_date >= recent_start, Patent.id),
                        else_=None,
                    )
                ).label("recent_patents"),
                func.avg(Patent.cited_by_count).label("avg_citations"),
                func.count(
                    case(
                        (Patent.cited_by_count >= 10, Patent.id),
                        else_=None,
                    )
                ).label("high_impact_count"),
            )
            .where(
                and_(
                    Patent.cpc_codes.isnot(None),
                    Patent.filing_date >= start_date,
                )
            )
            .group_by(section)
            .order_by(func.count(func.distinct(Patent.id)).desc())
        )

        result = await session.execute(overview_query)
        rows = result.all()

        total_all = sum(r[1] for r in rows) if rows else 1

        sections = []
        for row in rows:
            sect = row[0]
            total = row[1]
            recent = row[2] or 0
            avg_cit = float(row[3] or 0)
            high_impact = row[4] or 0

            # Calculate momentum (recent share vs overall share)
            total_share = total / total_all
            recent_share = recent / (sum(r[2] or 0 for r in rows) or 1)
            momentum = recent_share / total_share if total_share > 0 else 1

            sections.append({
                "section": sect,
                "name": CPC_SECTIONS.get(sect, "Unknown"),
                "total_patents": total,
                "recent_patents": recent,
                "market_share": round(total_share * 100, 1),
                "avg_citations": round(avg_cit, 2),
                "high_impact_count": high_impact,
                "momentum": round(momentum, 2),
                "trend": "growing" if momentum > 1.1 else "declining" if momentum < 0.9 else "stable",
            })

        return {
            "sections": sections,
            "total_patents": total_all,
            "analysis_years": years,
        }

    def _classify_opportunity(
        self,
        decline_ratio: float,
        high_impact: int,
        recent: int,
    ) -> str:
        """Classify the type of white space opportunity."""
        if decline_ratio > 0.7 and high_impact >= 3:
            return "abandoned_goldmine"  # High-impact area with sharp decline
        if decline_ratio > 0.5 and recent < 5:
            return "dormant"  # Significant decline, very few recent
        if high_impact >= 5 and decline_ratio > 0.3:
            return "consolidation"  # Foundational patents, slowing innovation
        if decline_ratio > 0.3:
            return "emerging_gap"  # Moderate decline, potential opportunity
        return "minor_gap"


whitespace_service = WhiteSpaceService()
