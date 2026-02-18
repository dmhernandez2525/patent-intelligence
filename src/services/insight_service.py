"""AI-powered patent insight generation service."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.insight import InsightTemplate, PatentInsight

logger = structlog.get_logger(__name__)
DEFAULT_MODEL = "gpt-4"


class InsightService:
    """Manage patent insight lifecycle and AI generation dispatch."""

    # Public CRUD

    async def list_insights(
        self,
        session: AsyncSession,
        user_id: int,
        insight_type: str | None = None,
        patent_id: int | None = None,
    ) -> list[PatentInsight]:
        """Return insights for a user, optionally filtered by type or patent."""
        stmt = select(PatentInsight).where(PatentInsight.user_id == user_id)
        if insight_type is not None:
            stmt = stmt.where(PatentInsight.insight_type == insight_type)
        if patent_id is not None:
            stmt = stmt.where(PatentInsight.patent_id == patent_id)
        stmt = stmt.order_by(PatentInsight.created_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_insight(
        self,
        session: AsyncSession,
        insight_id: int,
        user_id: int,
    ) -> PatentInsight:
        """Get a single insight, verifying ownership."""
        return await self._get_user_insight(session, insight_id, user_id)

    async def create_insight(
        self,
        session: AsyncSession,
        user_id: int,
        insight_type: str,
        query_text: str | None = None,
        patent_id: int | None = None,
    ) -> PatentInsight:
        """Create a new insight record in pending state."""
        insight = PatentInsight(
            user_id=user_id,
            insight_type=insight_type,
            status="pending",
            query_text=query_text,
            patent_id=patent_id,
            result_data={},
        )
        session.add(insight)
        await session.flush()
        await session.refresh(insight)
        logger.info(
            "insight.created",
            insight_id=insight.id,
            insight_type=insight_type,
            user_id=user_id,
        )
        return insight

    async def generate_insight(
        self,
        session: AsyncSession,
        insight_id: int,
        user_id: int,
    ) -> PatentInsight:
        """Run AI generation for an insight, dispatching by type."""
        insight = await self._get_user_insight(session, insight_id, user_id)
        insight.status = "processing"
        await session.flush()

        generators = {
            "summary": self._generate_summary,
            "claim_analysis": self._generate_claim_analysis,
            "patentability": self._generate_patentability,
            "fto_analysis": self._generate_fto,
            "nl_query": self._generate_nl_query,
            "competitive_brief": self._generate_competitive_brief,
        }

        generator = generators.get(insight.insight_type)
        if generator is None:
            insight.status = "failed"
            insight.error_message = f"Unknown insight type: {insight.insight_type}"
            await session.flush()
            return insight

        try:
            result = await generator(insight, session)
            insight.status = "completed"
            insight.result_text = result["result_text"]
            insight.result_data = result["result_data"]
            insight.model_used = result["model_used"]
            insight.token_count = result["token_count"]
            insight.completed_at = datetime.now(UTC)
            logger.info(
                "insight.generated",
                insight_id=insight.id,
                insight_type=insight.insight_type,
            )
        except Exception as exc:
            insight.status = "failed"
            insight.error_message = str(exc)
            logger.error(
                "insight.generation_failed",
                insight_id=insight.id,
                error=str(exc),
            )

        await session.flush()
        return insight

    async def delete_insight(
        self,
        session: AsyncSession,
        insight_id: int,
        user_id: int,
    ) -> bool:
        """Delete an insight after verifying ownership."""
        insight = await self._get_user_insight(session, insight_id, user_id)
        await session.delete(insight)
        await session.flush()
        logger.info("insight.deleted", insight_id=insight_id, user_id=user_id)
        return True

    # Template operations

    async def list_templates(
        self,
        session: AsyncSession,
        insight_type: str | None = None,
    ) -> list[InsightTemplate]:
        """List available insight templates, optionally filtered by type."""
        stmt = select(InsightTemplate)
        if insight_type is not None:
            stmt = stmt.where(InsightTemplate.insight_type == insight_type)
        stmt = stmt.order_by(InsightTemplate.name)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_template(
        self,
        session: AsyncSession,
        template_id: int,
    ) -> InsightTemplate:
        """Get a single template by ID."""
        result = await session.execute(
            select(InsightTemplate).where(InsightTemplate.id == template_id)
        )
        template = result.scalar_one_or_none()
        if template is None:
            raise ValueError("Template not found")
        return template

    # Private generation stubs

    async def _generate_summary(
        self, insight: PatentInsight, session: AsyncSession,
    ) -> dict:
        logger.info("insight.generate_summary", insight_id=insight.id)
        return {
            "result_text": "Patent summary placeholder for further AI integration.",
            "result_data": {
                "sections": ["background", "claims", "novelty"],
            },
            "model_used": DEFAULT_MODEL,
            "token_count": 0,
        }

    async def _generate_claim_analysis(
        self, insight: PatentInsight, session: AsyncSession,
    ) -> dict:
        logger.info("insight.generate_claim_analysis", insight_id=insight.id)
        return {
            "result_text": "Claim analysis placeholder for further AI integration.",
            "result_data": {
                "independent_claims": [],
                "dependent_claims": [],
                "claim_scope": "broad",
            },
            "model_used": DEFAULT_MODEL,
            "token_count": 0,
        }

    async def _generate_patentability(
        self, insight: PatentInsight, session: AsyncSession,
    ) -> dict:
        logger.info("insight.generate_patentability", insight_id=insight.id)
        return {
            "result_text": "Patentability assessment placeholder for further AI integration.",
            "result_data": {
                "novelty_score": 0.0,
                "non_obviousness_score": 0.0,
                "references": [],
            },
            "model_used": DEFAULT_MODEL,
            "token_count": 0,
        }

    async def _generate_fto(
        self, insight: PatentInsight, session: AsyncSession,
    ) -> dict:
        logger.info("insight.generate_fto", insight_id=insight.id)
        return {
            "result_text": "Freedom-to-operate analysis placeholder for further AI integration.",
            "result_data": {
                "risk_level": "unknown",
                "blocking_patents": [],
                "recommendations": [],
            },
            "model_used": DEFAULT_MODEL,
            "token_count": 0,
        }

    async def _generate_nl_query(
        self, insight: PatentInsight, session: AsyncSession,
    ) -> dict:
        logger.info(
            "insight.generate_nl_query",
            insight_id=insight.id,
            query=insight.query_text,
        )
        return {
            "result_text": f"Results for: {insight.query_text}",
            "result_data": {
                "patents_found": 0,
                "query_interpretation": "",
            },
            "model_used": DEFAULT_MODEL,
            "token_count": 0,
        }

    async def _generate_competitive_brief(
        self, insight: PatentInsight, session: AsyncSession,
    ) -> dict:
        logger.info("insight.generate_competitive_brief", insight_id=insight.id)
        return {
            "result_text": "Competitive landscape brief placeholder for further AI integration.",
            "result_data": {
                "competitors": [],
                "market_position": "",
                "trends": [],
            },
            "model_used": DEFAULT_MODEL,
            "token_count": 0,
        }

    # Private helpers

    async def _get_user_insight(
        self,
        session: AsyncSession,
        insight_id: int,
        user_id: int,
    ) -> PatentInsight:
        """Fetch an insight and verify it belongs to the given user."""
        result = await session.execute(
            select(PatentInsight).where(
                and_(
                    PatentInsight.id == insight_id,
                    PatentInsight.user_id == user_id,
                )
            )
        )
        insight = result.scalar_one_or_none()
        if insight is None:
            raise ValueError("Insight not found")
        return insight


insight_service = InsightService()
