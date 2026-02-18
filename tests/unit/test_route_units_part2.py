"""Additional unit coverage for route modules (part 2)."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.api.routes import health, ideas, ingestion, whitespace
from src.api.schemas.ideas import IdeaRequest
from src.models.ingestion import IngestionCheckpoint, IngestionJob


class _Result:
    def __init__(self, scalar_value=None, rows=None):
        self._scalar_value = scalar_value
        self._rows = rows or []

    def scalar(self):
        return self._scalar_value

    def scalar_one_or_none(self):
        return self._scalar_value

    def scalars(self):
        return SimpleNamespace(all=lambda: self._rows)


def _coverage_payload() -> dict:
    return {
        "coverage_areas": [
            {
                "cpc_code": "G06F",
                "section": "G",
                "section_name": "Physics",
                "patent_count": 10,
                "avg_citations": 5.0,
                "recent_count": 3,
                "growth_rate": 0.1,
                "density_score": 0.3,
            }
        ],
        "total_areas": 1,
        "avg_patents_per_area": 10.0,
        "analysis_period_years": 5,
        "cpc_level": 4,
    }


@pytest.mark.asyncio
async def test_whitespace_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    monkeypatch.setattr(
        whitespace.whitespace_service,
        "get_coverage_analysis",
        AsyncMock(return_value=_coverage_payload()),
    )
    coverage = await whitespace.get_coverage_analysis(
        cpc_level=4, min_patents=5, years=5, session=session
    )
    assert coverage.total_areas == 1

    monkeypatch.setattr(
        whitespace.whitespace_service,
        "get_white_spaces",
        AsyncMock(
            return_value={
                "white_spaces": [
                    {
                        "cpc_code": "G06F",
                        "section": "G",
                        "section_name": "Physics",
                        "historical_patents": 10,
                        "recent_patents": 2,
                        "decline_ratio": 0.8,
                        "high_impact_count": 1,
                        "max_citations": 20,
                        "gap_score": 0.7,
                        "opportunity_type": "dormant",
                    }
                ],
                "total_found": 1,
                "min_gap_score": 0.3,
                "analysis_window": {"years": 5},
            }
        ),
    )
    gaps = await whitespace.get_white_spaces(session=session)
    assert gaps.total_found == 1

    monkeypatch.setattr(
        whitespace.whitespace_service,
        "get_cross_domain_opportunities",
        AsyncMock(
            return_value={
                "source_cpc": "G06F",
                "source_section": "G",
                "source_section_name": "Physics",
                "opportunities": [
                    {
                        "cpc_code": "H04L",
                        "section": "H",
                        "section_name": "Electricity",
                        "patent_count": 4,
                        "avg_citations": 2.0,
                        "existing_combinations": 1,
                        "opportunity_score": 0.6,
                        "status": "emerging",
                    }
                ],
                "total_analyzed": 1,
            }
        ),
    )
    cross = await whitespace.get_cross_domain_opportunities("G06F", session=session)
    assert cross.total_analyzed == 1
    alias = await whitespace.get_opportunities_alias(source_cpc="G06F", session=session)
    assert alias.source_cpc == "G06F"

    with pytest.raises(HTTPException):
        await whitespace.get_opportunities_alias(source_cpc=None, session=session)

    monkeypatch.setattr(
        whitespace.whitespace_service,
        "get_section_overview",
        AsyncMock(
            return_value={
                "sections": [
                    {
                        "section": "G",
                        "name": "Physics",
                        "total_patents": 10,
                        "recent_patents": 3,
                        "market_share": 0.3,
                        "avg_citations": 2.0,
                        "high_impact_count": 1,
                        "momentum": 0.2,
                        "trend": "up",
                    }
                ],
                "total_patents": 10,
                "analysis_years": 5,
            }
        ),
    )
    sections = await whitespace.get_section_overview(session=session)
    assert sections.total_patents == 10
    detail = await whitespace.get_section_detail("G", session=session)
    assert detail.section == "G"
    with pytest.raises(HTTPException):
        await whitespace.get_section_detail("Z", session=session)


@pytest.mark.asyncio
async def test_ideas_and_health_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    monkeypatch.setattr(
        ideas.idea_service,
        "generate_ideas",
        AsyncMock(
            return_value={
                "ideas": [],
                "focus": "expiring",
                "cpc_prefix": None,
                "seed_patents_used": 0,
                "trends_used": 0,
            }
        ),
    )
    generated = await ideas.generate_ideas(IdeaRequest(), session=session)
    assert generated.focus == "expiring"

    monkeypatch.setattr(
        ideas.idea_service,
        "get_seeds",
        AsyncMock(
            return_value={"expiring_patents": [], "cpc_trends": [], "cross_domain_pairs": []}
        ),
    )
    seeds = await ideas.get_seeds(session=session)
    assert seeds.expiring_patents == []

    monkeypatch.setattr(
        health.stats_service,
        "get_dashboard_stats",
        AsyncMock(return_value={"ok": True}),
    )
    stats = await health.get_dashboard_stats(request_user=None, session=session)
    assert stats["ok"] is True

    monkeypatch.setattr(
        health.stats_service,
        "get_system_status",
        AsyncMock(return_value={"database": "operational"}),
    )
    status = await health.get_system_status(session=session)
    assert status["database"] == "operational"


@pytest.mark.asyncio
async def test_ingestion_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    now = datetime.now(UTC)

    trigger_payload = ingestion.IngestionTriggerRequest(source="uspto")
    session.execute.return_value = _Result(scalar_value=1)
    with pytest.raises(HTTPException) as conflict_exc:
        await ingestion.trigger_ingestion(trigger_payload, session=session)
    assert conflict_exc.value.status_code == 409

    jobs = [
        IngestionJob(
            id=1,
            source="uspto",
            status="completed",
            job_type="full",
            total_fetched=1,
            total_inserted=1,
            total_updated=0,
            total_errors=0,
            completed_at=now,
        )
    ]
    checkpoint = IngestionCheckpoint(
        id=1,
        source="uspto",
        last_sync_date=now,
        total_patents_ingested=100,
    )
    session.execute.side_effect = [
        _Result(rows=jobs),
        _Result(scalar_value=checkpoint),
        _Result(scalar_value=1),
    ]
    status = await ingestion.get_ingestion_status(source="uspto", limit=10, session=session)
    assert status.total_jobs == 1

    session.get.return_value = jobs[0]
    fetched = await ingestion.get_ingestion_job(1, session=session)
    assert fetched.id == 1

    session.get.return_value = None
    with pytest.raises(HTTPException):
        await ingestion.get_ingestion_job(9, session=session)
