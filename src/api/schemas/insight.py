"""Schemas for AI-powered patent insight endpoints."""

from pydantic import BaseModel, Field

_INSIGHT_TYPE_PATTERN = (
    "^(summary|claim_analysis|patentability|fto_analysis|nl_query|competitive_brief)$"
)


class InsightCreateRequest(BaseModel):
    """Request body for creating an insight."""

    insight_type: str = Field(pattern=_INSIGHT_TYPE_PATTERN)
    query_text: str | None = None
    patent_id: int | None = None


class InsightResponse(BaseModel):
    """Single insight response model."""

    id: int
    user_id: int
    patent_id: int | None
    insight_type: str
    status: str
    query_text: str | None
    result_text: str | None
    result_data: dict
    model_used: str | None
    token_count: int | None
    error_message: str | None
    completed_at: str | None
    created_at: str | None


class InsightListResponse(BaseModel):
    """Response for listing insights."""

    insights: list[InsightResponse]
    total: int


class TemplateResponse(BaseModel):
    """Prompt template response model."""

    id: int
    name: str
    insight_type: str
    prompt_template: str
    description: str | None
    is_default: bool


class TemplateListResponse(BaseModel):
    """Response for listing prompt templates."""

    templates: list[TemplateResponse]
