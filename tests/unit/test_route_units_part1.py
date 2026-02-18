"""Additional unit coverage for route modules (part 1)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.api.routes import analysis, expiration, patents, similarity
from src.api.schemas.similarity import PriorArtRequest, SimilarityRequest
from src.models.patent import Patent


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


def _similar_item() -> dict:
    return {
        "patent_number": "US123",
        "title": "Battery",
        "country": "US",
        "status": "active",
        "similarity_score": 0.9,
    }


def _expiring_item() -> dict:
    return {
        "patent_number": "US123",
        "title": "Battery",
        "country": "US",
        "status": "active",
        "days_until_expiration": 45,
        "maintenance_fee_status": "pending",
    }


def _fee_item() -> dict:
    return {
        "patent_number": "US123",
        "title": "Battery",
        "fee_year": 4,
        "due_date": "2026-03-01",
        "days_until_due": 14,
        "status": "pending",
    }


def _expiration_stats() -> dict:
    return {
        "expiring_30_days": 1,
        "expiring_90_days": 2,
        "expiring_180_days": 3,
        "expiring_365_days": 4,
        "recently_lapsed": 1,
        "pending_maintenance_fees": 2,
        "top_sectors": [{"cpc_code": "G06F", "count": 2}],
        "monthly_timeline": [{"month": "2026-03", "count": 1}],
    }


@pytest.mark.asyncio
async def test_analysis_routes_success_and_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    monkeypatch.setattr(
        analysis.citation_service,
        "get_technology_trends",
        AsyncMock(return_value={"trends": []}),
    )
    trends = await analysis.get_trends(session=session)
    assert trends["trends"] == []

    monkeypatch.setattr(
        analysis.citation_service,
        "get_technology_trends",
        AsyncMock(side_effect=Exception("boom")),
    )
    with pytest.raises(HTTPException) as trends_exc:
        await analysis.get_trends(session=session)
    assert trends_exc.value.status_code == 500

    monkeypatch.setattr(
        analysis.citation_service,
        "get_citation_network",
        AsyncMock(return_value={"error": "missing"}),
    )
    with pytest.raises(HTTPException) as net_exc:
        await analysis.get_citation_network("US1", session=session)
    assert net_exc.value.status_code == 404

    monkeypatch.setattr(
        analysis.citation_service,
        "get_citation_stats",
        AsyncMock(return_value={"error": "missing"}),
    )
    with pytest.raises(HTTPException) as stats_exc:
        await analysis.get_citation_stats("US1", session=session)
    assert stats_exc.value.status_code == 404


@pytest.mark.asyncio
async def test_expiration_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    monkeypatch.setattr(
        expiration.expiration_service,
        "get_expiration_stats",
        AsyncMock(return_value=_expiration_stats()),
    )
    monkeypatch.setattr(
        expiration.expiration_service,
        "get_expiring_patents",
        AsyncMock(return_value=([_expiring_item()], 1)),
    )
    monkeypatch.setattr(
        expiration.expiration_service,
        "get_lapsed_patents",
        AsyncMock(return_value=([_expiring_item()], 1)),
    )
    monkeypatch.setattr(
        expiration.expiration_service,
        "get_upcoming_maintenance_fees",
        AsyncMock(return_value=([_fee_item()], 1)),
    )

    dashboard = await expiration.expiration_dashboard(session=session)
    assert dashboard.stats.expiring_30_days == 1
    upcoming = await expiration.upcoming_expirations(
        days=90,
        country=None,
        cpc_code=None,
        assignee=None,
        page=1,
        per_page=20,
        session=session,
    )
    assert upcoming.total == 1
    lapsed = await expiration.lapsed_patents(
        days_back=90,
        country=None,
        cpc_code=None,
        assignee=None,
        page=1,
        per_page=20,
        session=session,
    )
    assert lapsed.total == 1
    fees = await expiration.maintenance_fees(days=90, page=1, per_page=20, session=session)
    assert fees.total == 1
    stats = await expiration.expiration_stats(session=session)
    assert stats.expiring_90_days == 2


@pytest.mark.asyncio
async def test_patent_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    patent = Patent(
        id=1,
        patent_number="US1",
        title="Battery",
        status="active",
        country="US",
        citation_count=0,
        cited_by_count=0,
        claim_count=0,
        patent_term_adjustment_days=0,
        patent_term_extension_days=0,
        terminal_disclaimer=False,
        source="uspto",
    )
    session.execute.side_effect = [
        _Result(scalar_value=1),
        _Result(rows=[patent]),
    ]

    response = await patents.list_patents(page=1, per_page=20, session=session)
    assert response.total == 1
    assert response.patents[0].patent_number == "US1"

    session.execute.side_effect = [_Result(scalar_value=patent)]
    detail = await patents.get_patent("US1", session=session)
    assert detail.patent_number == "US1"

    session.execute.side_effect = [_Result(scalar_value=None)]
    with pytest.raises(HTTPException) as not_found:
        await patents.get_patent("MISSING", session=session)
    assert not_found.value.status_code == 404

    session.execute.side_effect = [
        _Result(scalar_value=10),
        _Result(scalar_value=7),
        _Result(scalar_value=2),
        _Result(scalar_value=1),
        _Result(scalar_value=1),
    ]
    stats = await patents.patent_stats(session=session)
    assert stats["total_patents"] == 10


@pytest.mark.asyncio
async def test_similarity_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    with pytest.raises(HTTPException):
        await similarity.find_similar_patents(SimilarityRequest(), session=session)

    monkeypatch.setattr(
        similarity.similarity_service,
        "find_similar_patents",
        AsyncMock(return_value=[_similar_item()]),
    )
    similar_response = await similarity.find_similar_patents(
        SimilarityRequest(text_query="battery"),
        session=session,
    )
    assert similar_response.total_found == 1

    with pytest.raises(HTTPException):
        await similarity.find_prior_art(PriorArtRequest(), session=session)

    monkeypatch.setattr(
        similarity.similarity_service,
        "find_prior_art",
        AsyncMock(
            return_value={
                "target_patent": "US123",
                "target_filing_date": "2020-01-01",
                "prior_art": [_similar_item()],
                "total_found": 1,
                "semantic_count": 1,
                "citation_count": 0,
            }
        ),
    )
    prior_art = await similarity.find_prior_art(
        PriorArtRequest(text_query="battery"),
        session=session,
    )
    assert prior_art.total_found == 1

    monkeypatch.setattr(
        similarity.similarity_service,
        "get_patent_landscape",
        AsyncMock(return_value={"error": "missing"}),
    )
    with pytest.raises(HTTPException):
        await similarity.get_patent_landscape("US1", session=session)
