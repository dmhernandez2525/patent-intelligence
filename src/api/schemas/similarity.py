from datetime import date

from pydantic import BaseModel, Field


class SimilarPatentItem(BaseModel):
    patent_number: str
    title: str
    abstract: str | None = None
    filing_date: str | None = None
    grant_date: str | None = None
    assignee_organization: str | None = None
    cpc_codes: list[str] | None = None
    country: str
    status: str
    citation_count: int | None = None
    similarity_score: float
    source: str | None = None


class SimilarityRequest(BaseModel):
    patent_number: str | None = None
    text_query: str | None = None
    top_k: int = Field(default=20, ge=1, le=100)
    min_score: float = Field(default=0.5, ge=0.0, le=1.0)
    exclude_same_assignee: bool = False
    country: str | None = None
    cpc_code: str | None = None


class SimilarityResponse(BaseModel):
    results: list[SimilarPatentItem]
    query_patent: str | None = None
    query_text: str | None = None
    total_found: int


class PriorArtRequest(BaseModel):
    patent_number: str | None = None
    text_query: str | None = None
    filing_date_before: date | None = None
    top_k: int = Field(default=20, ge=1, le=100)
    min_score: float = Field(default=0.4, ge=0.0, le=1.0)


class PriorArtResponse(BaseModel):
    target_patent: str | None = None
    target_filing_date: str | None = None
    prior_art: list[SimilarPatentItem]
    total_found: int
    semantic_count: int
    citation_count: int


class CompetitorItem(BaseModel):
    assignee: str
    patent_count: int


class LandscapeResponse(BaseModel):
    target: SimilarPatentItem
    similar_patents: list[SimilarPatentItem]
    cited_patents: list[SimilarPatentItem]
    citing_patents: list[SimilarPatentItem]
    competitors: list[CompetitorItem]
