"""AI-powered patent idea generation service.

Uses LLM (Claude/OpenAI) to generate invention ideas from expiring patents,
technology trends, and cross-domain combinations.
"""
import json
from datetime import date, timedelta

from sqlalchemy import select, func, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.patent import Patent
from src.utils.logger import logger


class IdeaGenerationService:
    """Service for generating invention ideas from patent intelligence."""

    def __init__(self):
        self._http_client: "httpx.AsyncClient | None" = None

    async def _get_http_client(self):
        import httpx
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=60.0)
        return self._http_client

    async def generate_ideas(
        self,
        session: AsyncSession,
        cpc_prefix: str | None = None,
        focus: str = "expiring",
        count: int = 5,
        context_text: str | None = None,
    ) -> dict:
        """
        Generate invention ideas based on patent landscape analysis.

        Args:
            session: DB session
            cpc_prefix: Technology area to focus on (e.g., "H01L" for semiconductors)
            focus: Generation strategy - "expiring", "combination", "improvement"
            count: Number of ideas to generate
            context_text: Optional additional context for idea generation
        """
        # Gather seed data from the patent database
        seeds = await self._gather_seeds(session, cpc_prefix, focus)

        # Build the LLM prompt
        prompt = self._build_prompt(seeds, focus, count, context_text)

        # Generate ideas via LLM or fallback
        ideas = await self._call_llm(prompt, count)

        return {
            "ideas": ideas,
            "focus": focus,
            "cpc_prefix": cpc_prefix,
            "seed_patents_used": len(seeds.get("expiring_patents", [])),
            "trends_used": len(seeds.get("growth_areas", [])),
        }

    async def get_seeds(
        self,
        session: AsyncSession,
        cpc_prefix: str | None = None,
    ) -> dict:
        """
        Get seed data for idea generation context.

        Returns expiring patents, trending technology areas, and top assignees
        that can be used as inspiration for new inventions.
        """
        return await self._gather_seeds(session, cpc_prefix, "expiring")

    async def _gather_seeds(
        self,
        session: AsyncSession,
        cpc_prefix: str | None,
        focus: str,
    ) -> dict:
        """Gather contextual patent data for idea generation."""
        today = date.today()
        seeds: dict = {}

        # Expiring patents (next 2 years)
        expiry_conditions = [
            Patent.expiration_date.isnot(None),
            Patent.expiration_date >= today,
            Patent.expiration_date <= today + timedelta(days=730),
            Patent.status == "active",
        ]
        if cpc_prefix:
            expiry_conditions.append(
                func.array_to_string(Patent.cpc_codes, ',').ilike(f"%{cpc_prefix}%")
            )

        expiring_result = await session.execute(
            select(Patent)
            .where(and_(*expiry_conditions))
            .order_by(Patent.cited_by_count.desc())
            .limit(10)
        )
        expiring_patents = expiring_result.scalars().all()
        seeds["expiring_patents"] = [
            {
                "patent_number": p.patent_number,
                "title": p.title,
                "abstract": (p.abstract or "")[:300],
                "cpc_codes": p.cpc_codes[:3] if p.cpc_codes else [],
                "expiration_date": p.expiration_date.isoformat() if p.expiration_date else None,
                "cited_by_count": p.cited_by_count,
                "assignee": p.assignee_organization,
            }
            for p in expiring_patents
        ]

        # Growth areas (CPC codes with highest recent activity)
        recent_start = today.year - 3
        growth_conditions = [
            Patent.filing_date.isnot(None),
            extract("year", Patent.filing_date) >= recent_start,
            Patent.cpc_codes.isnot(None),
        ]
        if cpc_prefix:
            growth_conditions.append(
                func.array_to_string(Patent.cpc_codes, ',').ilike(f"%{cpc_prefix}%")
            )

        cpc_unnest = func.unnest(Patent.cpc_codes).label("cpc_code")
        growth_result = await session.execute(
            select(cpc_unnest, func.count(Patent.id).label("cnt"))
            .where(and_(*growth_conditions))
            .group_by("cpc_code")
            .order_by(func.count(Patent.id).desc())
            .limit(10)
        )
        seeds["growth_areas"] = [
            {"cpc_code": row[0][:8] if len(row[0]) > 8 else row[0], "patent_count": row[1]}
            for row in growth_result.all()
        ]

        # Top recent patents by citation impact
        if focus in ("combination", "improvement"):
            impact_conditions = [
                Patent.filing_date.isnot(None),
                extract("year", Patent.filing_date) >= today.year - 5,
                Patent.cited_by_count > 5,
            ]
            if cpc_prefix:
                impact_conditions.append(
                    func.array_to_string(Patent.cpc_codes, ',').ilike(f"%{cpc_prefix}%")
                )

            impact_result = await session.execute(
                select(Patent)
                .where(and_(*impact_conditions))
                .order_by(Patent.cited_by_count.desc())
                .limit(5)
            )
            high_impact = impact_result.scalars().all()
            seeds["high_impact_patents"] = [
                {
                    "patent_number": p.patent_number,
                    "title": p.title,
                    "abstract": (p.abstract or "")[:200],
                    "cited_by_count": p.cited_by_count,
                    "cpc_codes": p.cpc_codes[:3] if p.cpc_codes else [],
                }
                for p in high_impact
            ]

        return seeds

    def _build_prompt(
        self,
        seeds: dict,
        focus: str,
        count: int,
        context_text: str | None,
    ) -> str:
        """Build a structured LLM prompt for idea generation."""
        sections = []

        sections.append(
            "You are a patent innovation analyst. Generate novel invention ideas "
            "based on the following patent landscape data. Each idea should be "
            "technically feasible, non-obvious, and commercially viable."
        )

        if focus == "expiring":
            sections.append(
                "\n## Strategy: Expiring Patent Opportunities\n"
                "These patents are expiring soon. Generate ideas that improve upon, "
                "combine, or reimagine these technologies using modern approaches."
            )
        elif focus == "combination":
            sections.append(
                "\n## Strategy: Cross-Domain Combinations\n"
                "Look for opportunities to combine technologies from different "
                "patent classification areas to create novel inventions."
            )
        elif focus == "improvement":
            sections.append(
                "\n## Strategy: High-Impact Improvements\n"
                "These are highly-cited patents. Generate ideas that significantly "
                "improve upon these foundational technologies."
            )

        if seeds.get("expiring_patents"):
            sections.append("\n## Expiring Patents:")
            for p in seeds["expiring_patents"][:5]:
                sections.append(
                    f"- {p['patent_number']}: {p['title']}\n"
                    f"  CPC: {', '.join(p['cpc_codes'])}\n"
                    f"  Abstract: {p['abstract']}"
                )

        if seeds.get("growth_areas"):
            sections.append("\n## Trending Technology Areas:")
            for g in seeds["growth_areas"][:5]:
                sections.append(f"- {g['cpc_code']} ({g['patent_count']} recent patents)")

        if seeds.get("high_impact_patents"):
            sections.append("\n## High-Impact Patents:")
            for p in seeds["high_impact_patents"][:3]:
                sections.append(
                    f"- {p['patent_number']}: {p['title']} (cited by {p['cited_by_count']})\n"
                    f"  Abstract: {p['abstract']}"
                )

        if context_text:
            sections.append(f"\n## Additional Context:\n{context_text}")

        sections.append(
            f"\n## Instructions:\n"
            f"Generate exactly {count} invention ideas. For each idea, provide:\n"
            f"1. title: A concise invention title\n"
            f"2. description: 2-3 sentence technical description\n"
            f"3. rationale: Why this is novel and commercially viable\n"
            f"4. target_cpc: Most relevant CPC classification code\n"
            f"5. inspired_by: Patent numbers that inspired this idea\n"
            f"6. novelty_score: Estimated novelty 0.0-1.0\n\n"
            f"Return ONLY valid JSON array of objects with these keys."
        )

        return "\n".join(sections)

    async def _call_llm(self, prompt: str, count: int) -> list[dict]:
        """
        Call LLM API for idea generation.

        Tries Anthropic first, falls back to OpenAI, then template generation.
        """
        if settings.anthropic_api_key:
            try:
                return await self._call_anthropic(prompt, count)
            except Exception as e:
                logger.warning("idea_generation.anthropic_failed", error=str(e))

        if settings.openai_api_key:
            try:
                return await self._call_openai(prompt, count)
            except Exception as e:
                logger.warning("idea_generation.openai_failed", error=str(e))

        # Fallback: generate template ideas without LLM
        logger.info("idea_generation.using_fallback")
        return self._generate_fallback_ideas(count)

    async def _call_anthropic(self, prompt: str, count: int) -> list[dict]:
        """Call Anthropic Claude API."""
        client = await self._get_http_client()
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        data = response.json()
        content = data["content"][0]["text"]
        return self._parse_llm_response(content, count)

    async def _call_openai(self, prompt: str, count: int) -> list[dict]:
        """Call OpenAI API."""
        client = await self._get_http_client()
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4096,
                "temperature": 0.8,
            },
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return self._parse_llm_response(content, count)

    def _parse_llm_response(self, content: str, count: int) -> list[dict]:
        """Parse LLM response into structured ideas."""
        # Try to extract JSON from response
        content = content.strip()

        # Handle markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        try:
            ideas = json.loads(content)
            if isinstance(ideas, list):
                return [self._normalize_idea(idea) for idea in ideas[:count]]
        except json.JSONDecodeError:
            logger.warning("idea_generation.parse_failed", content_preview=content[:100])

        return self._generate_fallback_ideas(count)

    def _normalize_idea(self, idea: dict) -> dict:
        """Ensure idea has all required fields."""
        return {
            "title": idea.get("title", "Untitled Idea"),
            "description": idea.get("description", ""),
            "rationale": idea.get("rationale", ""),
            "target_cpc": idea.get("target_cpc", ""),
            "inspired_by": idea.get("inspired_by", []),
            "novelty_score": min(max(float(idea.get("novelty_score", 0.5)), 0.0), 1.0),
        }

    def _generate_fallback_ideas(self, count: int) -> list[dict]:
        """Generate template ideas when no LLM is available."""
        templates = [
            {
                "title": "Adaptive Energy Harvesting System",
                "description": "A multi-modal energy harvesting system that dynamically switches between solar, thermal, and kinetic energy sources based on environmental conditions using ML-optimized switching algorithms.",
                "rationale": "Combines expiring solar cell patents with modern ML optimization to create more efficient ambient energy collection for IoT devices.",
                "target_cpc": "H02J7/00",
                "inspired_by": [],
                "novelty_score": 0.75,
            },
            {
                "title": "Biodegradable Semiconductor Substrate",
                "description": "A transient electronics platform using cellulose-derived substrates with programmed dissolution rates, enabling fully biodegradable sensor networks for environmental monitoring.",
                "rationale": "Addresses growing e-waste concerns by combining biodegradable materials research with semiconductor fabrication techniques from expiring process patents.",
                "target_cpc": "H01L21/02",
                "inspired_by": [],
                "novelty_score": 0.82,
            },
            {
                "title": "Federated Patent Prior Art Search",
                "description": "A decentralized prior art search system using federated learning across multiple patent offices, enabling semantic search without centralizing proprietary patent embeddings.",
                "rationale": "Novel approach to cross-office patent search that preserves data sovereignty while improving search quality through collaborative model training.",
                "target_cpc": "G06F16/00",
                "inspired_by": [],
                "novelty_score": 0.71,
            },
            {
                "title": "Self-Healing Photonic Interconnect",
                "description": "An optical interconnect system with built-in fault detection and automatic rerouting using reconfigurable photonic switches, reducing datacenter downtime from fiber failures.",
                "rationale": "Applies expiring fiber optic switching patents with modern photonic integration to solve growing datacenter reliability challenges.",
                "target_cpc": "H04B10/00",
                "inspired_by": [],
                "novelty_score": 0.68,
            },
            {
                "title": "Neuromorphic Drug Discovery Accelerator",
                "description": "A specialized neuromorphic computing architecture optimized for molecular dynamics simulations, achieving 100x speedup over GPU-based approaches for protein-ligand binding predictions.",
                "rationale": "Combines neuromorphic computing advances with pharmaceutical screening techniques, targeting the intersection of two rapidly growing patent areas.",
                "target_cpc": "G16C20/00",
                "inspired_by": [],
                "novelty_score": 0.79,
            },
            {
                "title": "Quantum-Enhanced Battery Management",
                "description": "A battery state estimation system using quantum sensors for real-time electrochemical impedance spectroscopy, enabling precise remaining-life predictions without invasive measurements.",
                "rationale": "Leverages quantum sensing technology becoming available as foundational battery monitoring patents expire, improving EV battery longevity.",
                "target_cpc": "H01M10/48",
                "inspired_by": [],
                "novelty_score": 0.73,
            },
            {
                "title": "Programmable Metamaterial Antenna Array",
                "description": "A reconfigurable antenna system using electrically-tunable metamaterial surfaces that can dynamically reshape radiation patterns for 6G communications without mechanical movement.",
                "rationale": "Combines expiring phased array patents with emerging metamaterial research to enable software-defined antenna characteristics.",
                "target_cpc": "H01Q15/00",
                "inspired_by": [],
                "novelty_score": 0.77,
            },
            {
                "title": "Synthetic Biology IP Compliance Engine",
                "description": "An automated system for checking synthetic gene constructs against patent claims databases, flagging potential IP conflicts before biological parts are synthesized.",
                "rationale": "Addresses the growing regulatory need for IP compliance in synthetic biology as the field scales, combining NLP patent analysis with bioinformatics.",
                "target_cpc": "G16B50/00",
                "inspired_by": [],
                "novelty_score": 0.70,
            },
            {
                "title": "Acoustic Metamaterial Noise Cancellation Panel",
                "description": "A passive noise cancellation system using 3D-printed acoustic metamaterials with sub-wavelength resonant structures, achieving broadband attenuation without electronics or power.",
                "rationale": "Applies expiring acoustic dampening patents with additive manufacturing to create next-generation soundproofing for urban environments.",
                "target_cpc": "G10K11/16",
                "inspired_by": [],
                "novelty_score": 0.74,
            },
            {
                "title": "Edge-Computing Predictive Maintenance Mesh",
                "description": "A distributed sensor network using edge ML inference to predict mechanical failures in industrial equipment, with peer-to-peer model updates eliminating cloud dependency.",
                "rationale": "Combines IoT sensor patents nearing expiration with federated edge computing to enable real-time predictive maintenance without internet connectivity.",
                "target_cpc": "G05B23/02",
                "inspired_by": [],
                "novelty_score": 0.72,
            },
        ]
        return templates[:count]


idea_service = IdeaGenerationService()
