"""Schemas for shared watchlist collaboration."""

from pydantic import BaseModel, EmailStr, Field


class SharedWatchlistCreateRequest(BaseModel):
    """Request payload to create a shared watchlist."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class SharedWatchlistAddItemRequest(BaseModel):
    """Request payload to add an item to shared watchlist."""

    item_type: str = Field(pattern="^(patent|cpc_code|assignee|inventor)$")
    item_value: str = Field(min_length=1, max_length=255)


class SharedWatchlistInviteRequest(BaseModel):
    """Request payload to invite a collaborator."""

    email: EmailStr
    permission: str = Field(pattern="^(editor|viewer)$")


class SharedWatchlistItemResponse(BaseModel):
    """Shared watchlist item response model."""

    id: int
    item_type: str
    item_value: str
    patent_id: int | None
    added_by_user_id: int


class SharedWatchlistMemberResponse(BaseModel):
    """Shared watchlist member response model."""

    user_id: int
    permission: str


class SharedWatchlistInviteResponse(BaseModel):
    """Invite response model."""

    id: int
    invited_email: EmailStr
    permission: str
    invite_token: str
    status: str
    expires_at: str


class SharedWatchlistResponse(BaseModel):
    """Shared watchlist response model."""

    id: int
    name: str
    description: str | None
    owner_id: int
    members: list[SharedWatchlistMemberResponse]
    items: list[SharedWatchlistItemResponse]


class SharedWatchlistListItemResponse(BaseModel):
    """List item response for shared watchlists."""

    id: int
    name: str
    description: str | None
    owner_id: int
    member_count: int
    item_count: int
    created_at: str | None


class SharedWatchlistListResponse(BaseModel):
    """Response for listing shared watchlists."""

    watchlists: list[SharedWatchlistListItemResponse]


class InviteActionResponse(BaseModel):
    """Response for invite accept/decline/revoke actions."""

    success: bool
    status: str
