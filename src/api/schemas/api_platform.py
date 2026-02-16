"""Schemas for API platform endpoints."""

from pydantic import BaseModel, Field

# ---- API Keys ----

class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    tier: str = Field(default="free", pattern="^(free|standard|premium|enterprise)$")
    scopes: dict = Field(default_factory=dict)
    expires_in_days: int | None = Field(default=None, ge=1, le=365)

class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    tier: str
    scopes: dict
    rate_limit_per_minute: int
    is_active: bool
    last_used_at: str | None
    expires_at: str | None
    created_at: str | None

class ApiKeyCreatedResponse(ApiKeyResponse):
    raw_key: str

class ApiKeyListResponse(BaseModel):
    keys: list[ApiKeyResponse]

# ---- Webhooks ----

class WebhookCreateRequest(BaseModel):
    url: str = Field(min_length=1, max_length=1000)
    events: dict = Field(default_factory=dict)
    description: str | None = None

class WebhookUpdateRequest(BaseModel):
    url: str | None = Field(default=None, max_length=1000)
    events: dict | None = None
    description: str | None = None
    is_active: bool | None = None

class WebhookResponse(BaseModel):
    id: int
    url: str
    events: dict
    is_active: bool
    description: str | None
    failure_count: int
    last_triggered_at: str | None
    created_at: str | None

class WebhookListResponse(BaseModel):
    webhooks: list[WebhookResponse]

# ---- Deliveries ----

class DeliveryResponse(BaseModel):
    id: int
    endpoint_id: int
    event_type: str
    payload: dict
    response_status: int | None
    success: bool
    attempt_count: int
    next_retry_at: str | None
    created_at: str | None

class DeliveryListResponse(BaseModel):
    deliveries: list[DeliveryResponse]

# ---- Usage Stats ----

class UsageStatsResponse(BaseModel):
    api_key_count: int
    webhook_count: int
