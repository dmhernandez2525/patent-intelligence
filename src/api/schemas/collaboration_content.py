"""Schemas for collaborative annotations, comments, mentions, and feed."""

from pydantic import BaseModel, Field


class AnnotationCreateRequest(BaseModel):
    """Create annotation payload."""

    text: str = Field(min_length=1, max_length=4000)


class AnnotationResponse(BaseModel):
    """Annotation response."""

    id: int
    patent_id: int
    user_id: int
    text: str
    created_at: str | None
    updated_at: str | None


class CommentThreadCreateRequest(BaseModel):
    """Create comment thread payload."""

    title: str = Field(min_length=1, max_length=255)
    project_id: int | None = Field(default=None, ge=1)


class CommentCreateRequest(BaseModel):
    """Create comment payload."""

    text: str = Field(min_length=1, max_length=4000)
    parent_comment_id: int | None = Field(default=None, ge=1)


class CommentUpdateRequest(BaseModel):
    """Update comment payload."""

    text: str = Field(min_length=1, max_length=4000)


class CommentResponse(BaseModel):
    """Comment response."""

    id: int
    thread_id: int
    user_id: int
    parent_comment_id: int | None
    text: str
    is_deleted: bool
    edited_at: str | None
    created_at: str | None


class CommentThreadResponse(BaseModel):
    """Comment thread response."""

    id: int
    patent_id: int
    project_id: int | None
    title: str
    created_by_user_id: int
    comments: list[CommentResponse]
    created_at: str | None


class MentionResponse(BaseModel):
    """Mention notification response."""

    id: int
    user_id: int
    comment_id: int
    message: str
    is_read: bool
    read_at: str | None
    created_at: str | None


class MentionListResponse(BaseModel):
    """Mention list response."""

    notifications: list[MentionResponse]


class TeamActivityEntryResponse(BaseModel):
    """Team activity entry response."""

    id: int
    user_id: int | None
    event_type: str
    resource_type: str | None
    resource_id: str | None
    event_metadata: dict
    created_at: str | None


class TeamActivityFeedResponse(BaseModel):
    """Team activity feed response."""

    entries: list[TeamActivityEntryResponse]
