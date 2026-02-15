"""Schemas for research project collaboration."""

from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    """Create project payload."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class ProjectUpdateRequest(BaseModel):
    """Update project payload."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, pattern="^(active|on_hold|completed|archived)$")


class ProjectMemberRequest(BaseModel):
    """Add or update project member payload."""

    user_id: int = Field(ge=1)
    permission: str = Field(pattern="^(editor|viewer)$")


class ProjectPatentRequest(BaseModel):
    """Add or remove project patent payload."""

    patent_number: str = Field(min_length=1, max_length=50)


class ProjectSearchRequest(BaseModel):
    """Project-scoped search payload."""

    query: str = Field(default="", max_length=500)
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class ProjectMemberResponse(BaseModel):
    """Project member response."""

    user_id: int
    permission: str


class ProjectPatentResponse(BaseModel):
    """Project patent response."""

    id: int
    patent_number: str
    patent_id: int | None
    added_by_user_id: int


class ProjectResponse(BaseModel):
    """Project response."""

    id: int
    name: str
    description: str | None
    status: str
    owner_id: int
    members: list[ProjectMemberResponse]
    patents: list[ProjectPatentResponse]


class ProjectListResponse(BaseModel):
    """Project list response."""

    projects: list[ProjectResponse]


class ProjectSearchPatentResponse(BaseModel):
    """Project search result patent."""

    id: int
    patent_number: str
    title: str
    status: str
    country: str
    filing_date: str | None


class ProjectSearchResponse(BaseModel):
    """Project-scoped search response."""

    patents: list[ProjectSearchPatentResponse]
    total: int
    page: int
    per_page: int
