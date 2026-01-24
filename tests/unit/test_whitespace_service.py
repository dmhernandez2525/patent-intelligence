"""Unit tests for white space discovery service."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date

from src.services.whitespace_service import WhiteSpaceService, CPC_SECTIONS


@pytest.fixture
def whitespace_service():
    return WhiteSpaceService()


class TestWhiteSpaceService:
    """Tests for WhiteSpaceService."""

    def test_cpc_sections_defined(self):
        """Verify all major CPC sections are defined."""
        assert "A" in CPC_SECTIONS
        assert "G" in CPC_SECTIONS
        assert "H" in CPC_SECTIONS
        assert CPC_SECTIONS["G"] == "Physics"
        assert CPC_SECTIONS["H"] == "Electricity"

    def test_classify_opportunity_abandoned_goldmine(self, whitespace_service):
        """Test classification of abandoned goldmine opportunities."""
        result = whitespace_service._classify_opportunity(
            decline_ratio=0.8,
            high_impact=5,
            recent=2,
        )
        assert result == "abandoned_goldmine"

    def test_classify_opportunity_dormant(self, whitespace_service):
        """Test classification of dormant areas."""
        result = whitespace_service._classify_opportunity(
            decline_ratio=0.6,
            high_impact=1,
            recent=3,
        )
        assert result == "dormant"

    def test_classify_opportunity_consolidation(self, whitespace_service):
        """Test classification of consolidation areas."""
        result = whitespace_service._classify_opportunity(
            decline_ratio=0.4,
            high_impact=6,
            recent=10,
        )
        assert result == "consolidation"

    def test_classify_opportunity_emerging_gap(self, whitespace_service):
        """Test classification of emerging gaps."""
        result = whitespace_service._classify_opportunity(
            decline_ratio=0.35,
            high_impact=2,
            recent=8,
        )
        assert result == "emerging_gap"

    def test_classify_opportunity_minor_gap(self, whitespace_service):
        """Test classification of minor gaps."""
        result = whitespace_service._classify_opportunity(
            decline_ratio=0.2,
            high_impact=1,
            recent=15,
        )
        assert result == "minor_gap"

    @pytest.mark.asyncio
    async def test_get_coverage_analysis_empty_db(self, whitespace_service):
        """Test coverage analysis with empty database."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await whitespace_service.get_coverage_analysis(mock_session)

        assert result["coverage_areas"] == []
        assert result["total_areas"] == 0
        assert result["avg_patents_per_area"] == 0
        assert result["cpc_level"] == 4

    @pytest.mark.asyncio
    async def test_get_coverage_analysis_with_data(self, whitespace_service):
        """Test coverage analysis with mock data."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        # Mock: (cpc_prefix, patent_count, avg_citations, recent_count)
        mock_result.all.return_value = [
            ("H01L", 100, 5.5, 30),
            ("G06F", 80, 3.2, 25),
        ]
        mock_session.execute.return_value = mock_result

        result = await whitespace_service.get_coverage_analysis(mock_session, years=5)

        assert result["total_areas"] == 2
        assert result["analysis_period_years"] == 5
        assert len(result["coverage_areas"]) == 2

        h01l = result["coverage_areas"][0]
        assert h01l["cpc_code"] == "H01L"
        assert h01l["patent_count"] == 100
        assert h01l["section"] == "H"
        assert h01l["section_name"] == "Electricity"

    @pytest.mark.asyncio
    async def test_get_white_spaces_empty(self, whitespace_service):
        """Test white space discovery with no results."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await whitespace_service.get_white_spaces(mock_session)

        assert result["white_spaces"] == []
        assert result["total_found"] == 0
        assert result["min_gap_score"] == 0.3

    @pytest.mark.asyncio
    async def test_get_section_overview_empty(self, whitespace_service):
        """Test section overview with empty database."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await whitespace_service.get_section_overview(mock_session)

        assert result["sections"] == []
        assert result["analysis_years"] == 5

    @pytest.mark.asyncio
    async def test_get_section_overview_with_data(self, whitespace_service):
        """Test section overview with mock data."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        # Mock: (section, total, recent, avg_citations, high_impact)
        mock_result.all.return_value = [
            ("H", 1000, 300, 4.5, 50),
            ("G", 800, 200, 3.8, 40),
        ]
        mock_session.execute.return_value = mock_result

        result = await whitespace_service.get_section_overview(mock_session, years=3)

        assert result["total_patents"] == 1800
        assert result["analysis_years"] == 3
        assert len(result["sections"]) == 2

        h_section = result["sections"][0]
        assert h_section["section"] == "H"
        assert h_section["name"] == "Electricity"
        assert h_section["total_patents"] == 1000

    @pytest.mark.asyncio
    async def test_get_cross_domain_opportunities_empty(self, whitespace_service):
        """Test cross-domain opportunities with no results."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await whitespace_service.get_cross_domain_opportunities(
            mock_session, source_cpc="H01L"
        )

        assert result["source_cpc"] == "H01L"
        assert result["source_section"] == "H"
        assert result["opportunities"] == []


class TestWhiteSpaceRoutes:
    """Test white space API route schemas."""

    def test_coverage_response_structure(self):
        """Test CoverageResponse schema structure."""
        from src.api.schemas.whitespace import CoverageResponse, CoverageArea

        area = CoverageArea(
            cpc_code="H01L",
            section="H",
            section_name="Electricity",
            patent_count=100,
            avg_citations=5.0,
            recent_count=30,
            growth_rate=0.15,
            density_score=1.2,
        )

        response = CoverageResponse(
            coverage_areas=[area],
            total_areas=1,
            avg_patents_per_area=100.0,
            analysis_period_years=5,
            cpc_level=4,
        )

        assert response.total_areas == 1
        assert response.coverage_areas[0].cpc_code == "H01L"

    def test_whitespace_response_structure(self):
        """Test WhiteSpaceResponse schema structure."""
        from src.api.schemas.whitespace import WhiteSpaceResponse, WhiteSpaceItem

        item = WhiteSpaceItem(
            cpc_code="H01L21/0",
            section="H",
            section_name="Electricity",
            historical_patents=50,
            recent_patents=5,
            decline_ratio=0.7,
            high_impact_count=3,
            max_citations=25,
            gap_score=0.65,
            opportunity_type="abandoned_goldmine",
        )

        response = WhiteSpaceResponse(
            white_spaces=[item],
            total_found=1,
            min_gap_score=0.3,
            analysis_window={"historical_years": 5, "recent_years": 2},
        )

        assert response.total_found == 1
        assert response.white_spaces[0].opportunity_type == "abandoned_goldmine"

    def test_crossdomain_response_structure(self):
        """Test CrossDomainResponse schema structure."""
        from src.api.schemas.whitespace import CrossDomainResponse, CrossDomainOpportunity

        opp = CrossDomainOpportunity(
            cpc_code="G06F",
            section="G",
            section_name="Physics",
            patent_count=500,
            avg_citations=4.2,
            existing_combinations=10,
            opportunity_score=0.75,
            status="emerging",
        )

        response = CrossDomainResponse(
            source_cpc="H01L",
            source_section="H",
            source_section_name="Electricity",
            opportunities=[opp],
            total_analyzed=50,
        )

        assert response.source_cpc == "H01L"
        assert response.opportunities[0].status == "emerging"

    def test_section_overview_response_structure(self):
        """Test SectionOverviewResponse schema structure."""
        from src.api.schemas.whitespace import SectionOverviewResponse, SectionInfo

        section = SectionInfo(
            section="H",
            name="Electricity",
            total_patents=10000,
            recent_patents=2500,
            market_share=25.5,
            avg_citations=4.8,
            high_impact_count=500,
            momentum=1.15,
            trend="growing",
        )

        response = SectionOverviewResponse(
            sections=[section],
            total_patents=40000,
            analysis_years=5,
        )

        assert response.total_patents == 40000
        assert response.sections[0].trend == "growing"
