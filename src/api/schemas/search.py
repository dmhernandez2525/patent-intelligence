from datetime import date

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    search_type: str = Field(default="hybrid", pattern="^(fulltext|semantic|hybrid)$")
    cpc_codes: list[str] | None = None
    country: str | None = None
    status: str | None = None
    assignee: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class SearchResultItem(BaseModel):
    patent_number: str
    title: str
    abstract: str | None = None
    filing_date: date | None = None
    grant_date: date | None = None
    expiration_date: date | None = None
    assignee_organization: str | None = None
    inventors: list[str] | None = None
    cpc_codes: list[str] | None = None
    status: str
    country: str
    citation_count: int | None = None
    relevance_score: float = 0.0

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    total: int
    query: str
    search_type: str
    page: int
    per_page: int
