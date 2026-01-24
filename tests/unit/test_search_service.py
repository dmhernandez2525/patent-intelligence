import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date

from src.ai.search_service import PatentSearchService


@pytest.fixture
def search_service():
    return PatentSearchService()


class TestPatentToResult:
    """Test the _patent_to_result static method."""

    def _make_patent(self, **overrides):
        patent = MagicMock()
        patent.patent_number = overrides.get("patent_number", "US-12345-A1")
        patent.title = overrides.get("title", "Test Patent Title")
        patent.abstract = overrides.get("abstract", "A test abstract")
        patent.filing_date = overrides.get("filing_date", date(2020, 1, 15))
        patent.grant_date = overrides.get("grant_date", date(2021, 6, 1))
        patent.expiration_date = overrides.get("expiration_date", date(2040, 1, 15))
        patent.assignee_organization = overrides.get("assignee_organization", "Test Corp")
        patent.inventors = overrides.get("inventors", ["Alice", "Bob"])
        patent.cpc_codes = overrides.get("cpc_codes", ["H01L21/00", "G06F3/01"])
        patent.status = overrides.get("status", "active")
        patent.country = overrides.get("country", "US")
        patent.citation_count = overrides.get("citation_count", 5)
        return patent

    def test_basic_conversion(self, search_service: PatentSearchService):
        patent = self._make_patent()
        result = search_service._patent_to_result(patent, 0.85)

        assert result["patent_number"] == "US-12345-A1"
        assert result["title"] == "Test Patent Title"
        assert result["abstract"] == "A test abstract"
        assert result["filing_date"] == "2020-01-15"
        assert result["grant_date"] == "2021-06-01"
        assert result["expiration_date"] == "2040-01-15"
        assert result["assignee_organization"] == "Test Corp"
        assert result["inventors"] == ["Alice", "Bob"]
        assert result["cpc_codes"] == ["H01L21/00", "G06F3/01"]
        assert result["status"] == "active"
        assert result["country"] == "US"
        assert result["citation_count"] == 5
        assert result["relevance_score"] == 0.85

    def test_none_dates(self, search_service: PatentSearchService):
        patent = self._make_patent(
            filing_date=None,
            grant_date=None,
            expiration_date=None,
        )
        result = search_service._patent_to_result(patent, 0.5)

        assert result["filing_date"] is None
        assert result["grant_date"] is None
        assert result["expiration_date"] is None

    def test_relevance_score_rounding(self, search_service: PatentSearchService):
        patent = self._make_patent()
        result = search_service._patent_to_result(patent, 0.123456789)
        assert result["relevance_score"] == 0.1235

    def test_none_optional_fields(self, search_service: PatentSearchService):
        patent = self._make_patent(
            abstract=None,
            assignee_organization=None,
            inventors=None,
            cpc_codes=None,
            citation_count=None,
        )
        result = search_service._patent_to_result(patent, 0.7)

        assert result["abstract"] is None
        assert result["assignee_organization"] is None
        assert result["inventors"] is None
        assert result["cpc_codes"] is None
        assert result["citation_count"] is None


class TestApplyFilters:
    """Test the _apply_filters method."""

    def test_no_filters(self, search_service: PatentSearchService):
        mock_query = MagicMock()
        result = search_service._apply_filters(mock_query, None)
        assert result == mock_query

    def test_empty_filters(self, search_service: PatentSearchService):
        mock_query = MagicMock()
        result = search_service._apply_filters(mock_query, {})
        assert result == mock_query

    def test_country_filter(self, search_service: PatentSearchService):
        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        search_service._apply_filters(mock_query, {"country": "US"})
        mock_query.where.assert_called()

    def test_status_filter(self, search_service: PatentSearchService):
        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        search_service._apply_filters(mock_query, {"status": "active"})
        mock_query.where.assert_called()

    def test_assignee_filter(self, search_service: PatentSearchService):
        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        search_service._apply_filters(mock_query, {"assignee": "Apple"})
        mock_query.where.assert_called()

    def test_cpc_codes_filter(self, search_service: PatentSearchService):
        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        search_service._apply_filters(mock_query, {"cpc_codes": ["H01L"]})
        mock_query.where.assert_called()

    def test_date_range_filters(self, search_service: PatentSearchService):
        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        search_service._apply_filters(
            mock_query,
            {"date_from": date(2020, 1, 1), "date_to": date(2023, 12, 31)},
        )
        assert mock_query.where.call_count == 2

    def test_multiple_filters(self, search_service: PatentSearchService):
        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        search_service._apply_filters(
            mock_query,
            {"country": "US", "status": "active", "assignee": "Google"},
        )
        assert mock_query.where.call_count == 3


class TestHybridSearchRRF:
    """Test the hybrid search reciprocal rank fusion logic."""

    @pytest.mark.asyncio
    async def test_hybrid_fallback_to_fulltext_no_embeddings(
        self, search_service: PatentSearchService
    ):
        """When no embeddings exist, hybrid should fall back to fulltext."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0  # No embeddings
        mock_session.execute.return_value = mock_result

        with patch.object(
            search_service, "fulltext_search", new_callable=AsyncMock
        ) as mock_ft:
            mock_ft.return_value = ([], 0)
            results, total = await search_service.hybrid_search(
                mock_session, "battery technology", {}
            )
            mock_ft.assert_called_once()

    @pytest.mark.asyncio
    async def test_hybrid_combines_results(self, search_service: PatentSearchService):
        """Hybrid search should combine results from both methods."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 100  # Has embeddings
        mock_session.execute.return_value = mock_result

        ft_results = [
            {"patent_number": "US-001", "title": "Patent 1", "relevance_score": 0.9, "status": "active", "country": "US"},
            {"patent_number": "US-002", "title": "Patent 2", "relevance_score": 0.7, "status": "active", "country": "US"},
        ]
        sem_results = [
            {"patent_number": "US-002", "title": "Patent 2", "relevance_score": 0.95, "status": "active", "country": "US"},
            {"patent_number": "US-003", "title": "Patent 3", "relevance_score": 0.85, "status": "active", "country": "US"},
        ]

        with patch.object(
            search_service, "fulltext_search", new_callable=AsyncMock
        ) as mock_ft, patch.object(
            search_service, "semantic_search", new_callable=AsyncMock
        ) as mock_sem:
            mock_ft.return_value = (ft_results, 2)
            mock_sem.return_value = (sem_results, 2)

            results, total = await search_service.hybrid_search(
                mock_session, "battery", {}
            )

            # US-002 should score highest (appears in both)
            assert total == 3  # 3 unique patents
            assert len(results) <= 20


class TestSearchSchemas:
    """Test the search request/response schemas."""

    def test_search_request_defaults(self):
        from src.api.schemas.search import SearchRequest

        req = SearchRequest(query="test")
        assert req.search_type == "hybrid"
        assert req.page == 1
        assert req.per_page == 20
        assert req.country is None
        assert req.status is None
        assert req.cpc_codes is None

    def test_search_request_validation(self):
        from src.api.schemas.search import SearchRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SearchRequest(query="")  # min_length=1

        with pytest.raises(ValidationError):
            SearchRequest(query="test", search_type="invalid")

        with pytest.raises(ValidationError):
            SearchRequest(query="test", page=0)  # ge=1

        with pytest.raises(ValidationError):
            SearchRequest(query="test", per_page=101)  # le=100

    def test_search_result_item(self):
        from src.api.schemas.search import SearchResultItem

        item = SearchResultItem(
            patent_number="US-123",
            title="Test",
            status="active",
            country="US",
            relevance_score=0.85,
            grant_date=date(2021, 1, 1),
            inventors=["Alice"],
            citation_count=10,
        )
        assert item.patent_number == "US-123"
        assert item.grant_date == date(2021, 1, 1)
        assert item.inventors == ["Alice"]
        assert item.citation_count == 10

    def test_search_response(self):
        from src.api.schemas.search import SearchResponse, SearchResultItem

        resp = SearchResponse(
            results=[
                SearchResultItem(
                    patent_number="US-1",
                    title="T",
                    status="active",
                    country="US",
                    relevance_score=0.9,
                )
            ],
            total=1,
            query="test",
            search_type="hybrid",
            page=1,
            per_page=20,
        )
        assert len(resp.results) == 1
        assert resp.total == 1
