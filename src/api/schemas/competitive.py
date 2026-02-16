"""Schemas for competitive intelligence endpoints."""

from pydantic import BaseModel, Field

# ---- Monitors ----

class MonitorCreateRequest(BaseModel):
    competitor_name: str = Field(min_length=1, max_length=200)
    aliases: list[str] = Field(default_factory=list)
    cpc_focus: list[str] = Field(default_factory=list)
    notes: str | None = None

class MonitorUpdateRequest(BaseModel):
    competitor_name: str | None = None
    aliases: list[str] | None = None
    cpc_focus: list[str] | None = None
    notes: str | None = None
    status: str | None = Field(default=None, pattern="^(active|paused|archived)$")

class MonitorResponse(BaseModel):
    id: int
    competitor_name: str
    aliases: list[str]
    cpc_focus: list[str]
    status: str
    notes: str | None
    last_checked_at: str | None
    created_at: str | None

class MonitorListResponse(BaseModel):
    monitors: list[MonitorResponse]

# ---- Comparisons ----

class ComparisonCreateRequest(BaseModel):
    entity_a: str = Field(min_length=1, max_length=200)
    entity_b: str = Field(min_length=1, max_length=200)

class ComparisonResponse(BaseModel):
    id: int
    entity_a: str
    entity_b: str
    status: str
    comparison_data: dict
    overlap_score: float | None
    summary: str | None
    error_message: str | None
    computed_at: str | None
    created_at: str | None

class ComparisonListResponse(BaseModel):
    comparisons: list[ComparisonResponse]

# ---- Targets ----

class TargetCreateRequest(BaseModel):
    target_name: str = Field(min_length=1, max_length=200)
    rationale: str | None = None
    patent_count: int = Field(default=0, ge=0)
    relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    cpc_overlap: list[str] = Field(default_factory=list)

class TargetUpdateRequest(BaseModel):
    target_name: str | None = None
    rationale: str | None = None
    patent_count: int | None = Field(default=None, ge=0)
    relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    is_starred: bool | None = None

class TargetResponse(BaseModel):
    id: int
    target_name: str
    rationale: str | None
    patent_count: int
    relevance_score: float | None
    cpc_overlap: list[str]
    analysis_data: dict
    is_starred: bool
    created_at: str | None

class TargetListResponse(BaseModel):
    targets: list[TargetResponse]
