"""Schemas for AI-powered idea generation endpoints."""
from pydantic import BaseModel, Field


class IdeaRequest(BaseModel):
    """Request body for idea generation."""
    cpc_prefix: str | None = Field(None, description="CPC code prefix to focus on")
    focus: str = Field(
        default="expiring",
        description="Generation strategy: expiring, combination, or improvement",
        pattern="^(expiring|combination|improvement)$",
    )
    count: int = Field(default=5, ge=1, le=10, description="Number of ideas to generate")
    context_text: str | None = Field(None, max_length=2000, description="Additional context")


class GeneratedIdea(BaseModel):
    """A single generated invention idea."""
    title: str
    description: str
    rationale: str
    target_cpc: str
    inspired_by: list[str] = []
    novelty_score: float = Field(ge=0.0, le=1.0)


class IdeaResponse(BaseModel):
    """Response from idea generation."""
    ideas: list[GeneratedIdea]
    focus: str
    cpc_prefix: str | None
    seed_patents_used: int
    trends_used: int


class SeedPatent(BaseModel):
    """Expiring patent used as seed for idea generation."""
    patent_number: str
    title: str
    abstract: str
    cpc_codes: list[str] = []
    expiration_date: str | None = None
    cited_by_count: int = 0
    assignee: str | None = None


class GrowthArea(BaseModel):
    """Trending technology area."""
    cpc_code: str
    patent_count: int


class SeedResponse(BaseModel):
    """Seed data for idea generation context."""
    expiring_patents: list[SeedPatent] = []
    growth_areas: list[GrowthArea] = []
    high_impact_patents: list[SeedPatent] = []
