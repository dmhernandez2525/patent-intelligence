"""Schemas for research report generation and scheduling."""

from pydantic import BaseModel, Field

_REPORT_TYPE_PATTERN = "^(landscape|competitive|expiration|patent_analysis|custom)$"
_OUTPUT_FORMAT_PATTERN = "^(pdf|excel|html|json)$"


class ReportCreateRequest(BaseModel):
    """Request payload to create a research report."""

    title: str = Field(min_length=1, max_length=200)
    report_type: str = Field(pattern=_REPORT_TYPE_PATTERN)
    output_format: str = Field(
        pattern=_OUTPUT_FORMAT_PATTERN, default="pdf",
    )
    project_id: int | None = None
    config: dict = Field(default_factory=dict)


class ReportResponse(BaseModel):
    """Research report response model."""

    id: int
    user_id: int
    project_id: int | None
    title: str
    report_type: str
    output_format: str
    status: str
    config: dict
    file_size: int | None
    page_count: int | None
    error_message: str | None
    generated_at: str | None
    created_at: str | None


class ReportListResponse(BaseModel):
    """Response for listing research reports."""

    reports: list[ReportResponse]
    total: int


class TemplateResponse(BaseModel):
    """Report template response model."""

    id: int
    name: str
    report_type: str
    description: str | None
    template_config: dict
    is_default: bool
    is_system: bool


class TemplateListResponse(BaseModel):
    """Response for listing report templates."""

    templates: list[TemplateResponse]


class ScheduleCreateRequest(BaseModel):
    """Request payload to create a report schedule."""

    report_type: str = Field(pattern=_REPORT_TYPE_PATTERN)
    output_format: str = Field(
        pattern=_OUTPUT_FORMAT_PATTERN, default="pdf",
    )
    project_id: int | None = None
    config: dict = Field(default_factory=dict)
    frequency: str = Field(
        pattern="^(daily|weekly|monthly)$", default="weekly",
    )


class ScheduleResponse(BaseModel):
    """Report schedule response model."""

    id: int
    report_type: str
    output_format: str
    project_id: int | None
    config: dict
    frequency: str
    next_run_at: str | None
    is_active: bool


class ScheduleListResponse(BaseModel):
    """Response for listing report schedules."""

    schedules: list[ScheduleResponse]
