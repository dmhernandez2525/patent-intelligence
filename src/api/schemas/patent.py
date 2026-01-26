from datetime import date, datetime

from pydantic import BaseModel


class PatentResponse(BaseModel):
    id: int
    patent_number: str
    title: str
    abstract: str | None = None
    filing_date: date | None = None
    grant_date: date | None = None
    expiration_date: date | None = None
    assignee: str | None = None
    assignee_organization: str | None = None
    inventors: list[str] | None = None
    cpc_codes: list[str] | None = None
    status: str
    country: str
    citation_count: int = 0
    cited_by_count: int = 0
    claim_count: int = 0

    model_config = {"from_attributes": True}


class PatentDetailResponse(PatentResponse):
    description: str | None = None
    application_number: str | None = None
    publication_date: date | None = None
    priority_date: date | None = None
    ipc_codes: list[str] | None = None
    uspc_codes: list[str] | None = None
    patent_type: str | None = None
    kind_code: str | None = None
    patent_term_adjustment_days: int = 0
    patent_term_extension_days: int = 0
    terminal_disclaimer: bool = False
    inventor_countries: list[str] | None = None
    source: str = "uspto"
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PatentListResponse(BaseModel):
    patents: list[PatentResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
