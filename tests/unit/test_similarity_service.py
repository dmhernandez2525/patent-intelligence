import pytest
from datetime import date
from unittest.mock import MagicMock

from src.services.similarity_service import SimilarityService


@pytest.fixture
def service():
    return SimilarityService()


class TestToSimilarityResult:
    """Test the _to_similarity_result static method."""

    def _make_patent(self, **overrides):
        patent = MagicMock()
        patent.patent_number = overrides.get("patent_number", "US-12345-A1")
        patent.title = overrides.get("title", "Test Patent")
        patent.abstract = overrides.get("abstract", "An abstract")
        patent.filing_date = overrides.get("filing_date", date(2020, 3, 15))
        patent.grant_date = overrides.get("grant_date", date(2022, 1, 10))
        patent.assignee_organization = overrides.get("assignee_organization", "Acme Corp")
        patent.cpc_codes = overrides.get("cpc_codes", ["H01L21/00"])
        patent.country = overrides.get("country", "US")
        patent.status = overrides.get("status", "active")
        patent.citation_count = overrides.get("citation_count", 5)
        return patent

    def test_basic_conversion(self, service: SimilarityService):
        patent = self._make_patent()
        result = service._to_similarity_result(patent, 0.85)

        assert result["patent_number"] == "US-12345-A1"
        assert result["title"] == "Test Patent"
        assert result["similarity_score"] == 0.85
        assert result["country"] == "US"
        assert result["filing_date"] == "2020-03-15"

    def test_score_rounding(self, service: SimilarityService):
        patent = self._make_patent()
        result = service._to_similarity_result(patent, 0.87654321)
        assert result["similarity_score"] == 0.8765

    def test_none_dates(self, service: SimilarityService):
        patent = self._make_patent(filing_date=None, grant_date=None)
        result = service._to_similarity_result(patent, 0.5)
        assert result["filing_date"] is None
        assert result["grant_date"] is None


class TestSimilaritySchemas:
    """Test the similarity request/response schemas."""

    def test_similarity_request_defaults(self):
        from src.api.schemas.similarity import SimilarityRequest

        req = SimilarityRequest(text_query="battery technology")
        assert req.top_k == 20
        assert req.min_score == 0.5
        assert req.exclude_same_assignee is False
        assert req.patent_number is None

    def test_similarity_request_patent(self):
        from src.api.schemas.similarity import SimilarityRequest

        req = SimilarityRequest(patent_number="US-123")
        assert req.patent_number == "US-123"
        assert req.text_query is None

    def test_similarity_request_validation(self):
        from src.api.schemas.similarity import SimilarityRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SimilarityRequest(text_query="test", top_k=0)  # ge=1

        with pytest.raises(ValidationError):
            SimilarityRequest(text_query="test", min_score=2.0)  # le=1.0

    def test_prior_art_request(self):
        from src.api.schemas.similarity import PriorArtRequest

        req = PriorArtRequest(
            patent_number="US-123",
            filing_date_before=date(2020, 1, 1),
        )
        assert req.filing_date_before == date(2020, 1, 1)
        assert req.min_score == 0.4

    def test_similarity_response(self):
        from src.api.schemas.similarity import SimilarityResponse, SimilarPatentItem

        resp = SimilarityResponse(
            results=[
                SimilarPatentItem(
                    patent_number="US-1",
                    title="T",
                    country="US",
                    status="active",
                    similarity_score=0.9,
                )
            ],
            query_patent="US-123",
            query_text=None,
            total_found=1,
        )
        assert len(resp.results) == 1
        assert resp.results[0].similarity_score == 0.9

    def test_prior_art_response(self):
        from src.api.schemas.similarity import PriorArtResponse

        resp = PriorArtResponse(
            target_patent="US-123",
            target_filing_date="2020-01-01",
            prior_art=[],
            total_found=0,
            semantic_count=0,
            citation_count=0,
        )
        assert resp.target_patent == "US-123"

    def test_landscape_response(self):
        from src.api.schemas.similarity import LandscapeResponse, SimilarPatentItem

        target = SimilarPatentItem(
            patent_number="US-1",
            title="T",
            country="US",
            status="active",
            similarity_score=1.0,
        )
        resp = LandscapeResponse(
            target=target,
            similar_patents=[],
            cited_patents=[],
            citing_patents=[],
            competitors=[],
        )
        assert resp.target.patent_number == "US-1"
