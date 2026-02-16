"""Schemas for enterprise feature endpoints."""

from pydantic import BaseModel, Field

# ---- SSO Config ----

class SSOConfigRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=50)
    entity_id: str = Field(min_length=1, max_length=500)
    metadata_url: str | None = Field(default=None, max_length=1000)
    certificate: str | None = None
    is_enabled: bool = False
    auto_provision: bool = False
    default_role: str = Field(default="viewer", pattern="^(admin|analyst|viewer)$")

class SSOConfigResponse(BaseModel):
    id: int
    organization_id: int
    provider: str
    entity_id: str
    metadata_url: str | None
    is_enabled: bool
    auto_provision: bool
    default_role: str
    created_at: str | None

# ---- Audit Entries ----

class AuditEntryResponse(BaseModel):
    id: int
    organization_id: int
    user_id: int | None
    action: str
    resource_type: str | None
    resource_id: str | None
    before_state: dict | None
    after_state: dict | None
    ip_address: str | None
    compliance_tags: list[str] | None
    created_at: str | None

class AuditListResponse(BaseModel):
    entries: list[AuditEntryResponse]
    total: int

# ---- Compliance Policies ----

class PolicyCreateRequest(BaseModel):
    policy_type: str = Field(
        pattern="^(data_retention|access_control|export_restriction|encryption)$")
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    rules: dict = Field(default_factory=dict)
    is_enforced: bool = False

class PolicyUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    rules: dict | None = None
    is_enforced: bool | None = None

class PolicyResponse(BaseModel):
    id: int
    organization_id: int
    policy_type: str
    name: str
    description: str | None
    rules: dict
    is_enforced: bool
    last_evaluated_at: str | None
    created_at: str | None

class PolicyListResponse(BaseModel):
    policies: list[PolicyResponse]

# ---- Tenant Settings ----

class TenantSettingsRequest(BaseModel):
    max_users: int | None = Field(default=None, ge=1, le=10000)
    max_patents_tracked: int | None = Field(default=None, ge=1, le=1000000)
    allowed_features: dict | None = None
    data_region: str | None = Field(
        default=None, pattern="^(us-east|us-west|eu-west|ap-southeast)$")
    is_isolated: bool | None = None
    custom_branding: dict | None = None

class TenantSettingsResponse(BaseModel):
    id: int
    organization_id: int
    max_users: int
    max_patents_tracked: int
    allowed_features: dict
    data_region: str
    is_isolated: bool
    custom_branding: dict | None
    created_at: str | None

# ---- Admin Dashboard ----

class AdminStatsResponse(BaseModel):
    audit_entry_count: int
    policy_count: int
    enforced_policy_count: int
    sso_enabled: bool
    tenant_max_users: int
    tenant_is_isolated: bool
