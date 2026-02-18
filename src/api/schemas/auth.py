"""Schemas for auth, user settings, and organization collaboration."""

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    last_login: str | None
    created_at: str | None


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="viewer", pattern="^(admin|analyst|viewer)$")


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = Field(default_factory=lambda: "bearer")
    expires_in: int
    user: UserResponse


class PreferencesResponse(BaseModel):
    default_search_mode: str
    alert_frequency: str
    timezone: str
    email_notifications_enabled: bool
    updated_at: str | None


class PreferencesUpdateRequest(BaseModel):
    default_search_mode: str | None = Field(default=None, pattern="^(semantic|fulltext|hybrid)$")
    alert_frequency: str | None = Field(default=None, pattern="^(immediate|daily|weekly)$")
    timezone: str | None = Field(default=None, min_length=2, max_length=64)
    email_notifications_enabled: bool | None = None


class OrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)


class OrganizationResponse(BaseModel):
    id: int
    name: str
    owner_id: int
    invite_code: str
    created_at: str | None


class OrganizationInviteRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    note: str | None = Field(default=None, max_length=500)


class OrganizationInviteResponse(BaseModel):
    id: int
    organization_id: int
    invited_email: str
    invite_token: str
    invite_code: str
    status: str
    expires_at: str | None


class InviteAcceptResponse(BaseModel):
    organization_id: int
    user_id: int
    role: str


class SSOStartResponse(BaseModel):
    provider: str
    configured: bool
    authorization_url: str


class SSOCallbackResponse(BaseModel):
    provider: str
    status: str
    code_received: bool
    state: str | None
    message: str
