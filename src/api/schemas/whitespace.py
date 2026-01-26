"""Pydantic schemas for white space discovery API."""

from pydantic import BaseModel


class CoverageArea(BaseModel):
    """A technology area with coverage metrics."""

    cpc_code: str
    section: str
    section_name: str
    patent_count: int
    avg_citations: float
    recent_count: int
    growth_rate: float
    density_score: float


class CoverageResponse(BaseModel):
    """Response for coverage analysis endpoint."""

    coverage_areas: list[CoverageArea]
    total_areas: int
    avg_patents_per_area: float
    analysis_period_years: int
    cpc_level: int


class WhiteSpaceItem(BaseModel):
    """A white space opportunity."""

    cpc_code: str
    section: str
    section_name: str
    historical_patents: int
    recent_patents: int
    decline_ratio: float
    high_impact_count: int
    max_citations: int
    gap_score: float
    opportunity_type: str


class WhiteSpaceResponse(BaseModel):
    """Response for white space discovery endpoint."""

    white_spaces: list[WhiteSpaceItem]
    total_found: int
    min_gap_score: float
    analysis_window: dict


class CrossDomainOpportunity(BaseModel):
    """A cross-domain combination opportunity."""

    cpc_code: str
    section: str
    section_name: str
    patent_count: int
    avg_citations: float
    existing_combinations: int
    opportunity_score: float
    status: str


class CrossDomainResponse(BaseModel):
    """Response for cross-domain opportunities endpoint."""

    source_cpc: str
    source_section: str
    source_section_name: str
    opportunities: list[CrossDomainOpportunity]
    total_analyzed: int


class SectionInfo(BaseModel):
    """Information about a CPC section."""

    section: str
    name: str
    total_patents: int
    recent_patents: int
    market_share: float
    avg_citations: float
    high_impact_count: int
    momentum: float
    trend: str


class SectionOverviewResponse(BaseModel):
    """Response for section overview endpoint."""

    sections: list[SectionInfo]
    total_patents: int
    analysis_years: int
