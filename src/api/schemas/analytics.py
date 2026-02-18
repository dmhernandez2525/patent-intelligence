"""Schemas for custom analytics engine endpoints."""

from pydantic import BaseModel, Field

# ---- Saved Queries ----

class QueryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    query_config: dict = Field(default_factory=dict)
    filters: dict = Field(default_factory=dict)
    is_public: bool = False

class QueryUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    query_config: dict | None = None
    filters: dict | None = None
    status: str | None = Field(default=None, pattern="^(draft|saved|archived)$")
    is_public: bool | None = None

class QueryResponse(BaseModel):
    id: int
    name: str
    description: str | None
    query_config: dict
    filters: dict
    status: str
    is_public: bool
    last_run_at: str | None
    run_count: int
    created_at: str | None

class QueryListResponse(BaseModel):
    queries: list[QueryResponse]

# ---- Custom Metrics ----

class MetricCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    metric_type: str = Field(pattern="^(count|sum|average|trend|distribution)$")
    definition: dict = Field(default_factory=dict)

class MetricUpdateRequest(BaseModel):
    name: str | None = None
    metric_type: str | None = Field(
        default=None, pattern="^(count|sum|average|trend|distribution)$")
    definition: dict | None = None

class MetricResponse(BaseModel):
    id: int
    name: str
    metric_type: str
    definition: dict
    current_value: dict | None
    last_computed_at: str | None
    created_at: str | None

class MetricListResponse(BaseModel):
    metrics: list[MetricResponse]

# ---- Schedules ----

class ScheduleCreateRequest(BaseModel):
    frequency: str = Field(default="daily", pattern="^(hourly|daily|weekly|monthly)$")
    query_id: int | None = None
    metric_id: int | None = None

class ScheduleUpdateRequest(BaseModel):
    frequency: str | None = Field(
        default=None, pattern="^(hourly|daily|weekly|monthly)$")
    is_active: bool | None = None

class ScheduleResponse(BaseModel):
    id: int
    query_id: int | None
    metric_id: int | None
    frequency: str
    is_active: bool
    next_run_at: str | None
    created_at: str | None

class ScheduleListResponse(BaseModel):
    schedules: list[ScheduleResponse]
