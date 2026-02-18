"""Enterprise models for SSO, audit, compliance, and tenant isolation."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class PolicyType(StrEnum):
    DATA_RETENTION = "data_retention"
    ACCESS_CONTROL = "access_control"
    EXPORT_RESTRICTION = "export_restriction"
    ENCRYPTION = "encryption"


class SSOConfig(TimestampMixin, Base):
    """SAML/OIDC SSO configuration per organization."""

    __tablename__ = "sso_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), unique=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(500), nullable=False)
    metadata_url: Mapped[str | None] = mapped_column(String(1000))
    certificate: Mapped[str | None] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_provision: Mapped[bool] = mapped_column(Boolean, default=False)
    default_role: Mapped[str] = mapped_column(String(20), default="viewer")

    __table_args__ = (
        Index("ix_sso_config_org", "organization_id"),
    )


class AuditEntry(TimestampMixin, Base):
    """Enterprise-grade audit trail entry."""

    __tablename__ = "audit_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(50))
    resource_id: Mapped[str | None] = mapped_column(String(100))
    before_state: Mapped[dict | None] = mapped_column(JSONB)
    after_state: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    compliance_tags: Mapped[list | None] = mapped_column(JSONB)

    __table_args__ = (
        Index("ix_audit_org_action", "organization_id", "action"),
        Index("ix_audit_org_created", "organization_id", "created_at"),
        Index("ix_audit_user", "user_id"),
    )


class CompliancePolicy(TimestampMixin, Base):
    """Compliance and data governance policy per organization."""

    __tablename__ = "compliance_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
    )
    policy_type: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    rules: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_enforced: Mapped[bool] = mapped_column(Boolean, default=False)
    last_evaluated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    __table_args__ = (
        Index("ix_compliance_org_type", "organization_id", "policy_type"),
    )


class TenantSettings(TimestampMixin, Base):
    """Per-organization tenant isolation and feature configuration."""

    __tablename__ = "tenant_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), unique=True,
    )
    max_users: Mapped[int] = mapped_column(Integer, default=50)
    max_patents_tracked: Mapped[int] = mapped_column(Integer, default=10000)
    allowed_features: Mapped[dict] = mapped_column(JSONB, default=dict)
    data_region: Mapped[str] = mapped_column(String(20), default="us-east")
    is_isolated: Mapped[bool] = mapped_column(Boolean, default=False)
    custom_branding: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        Index("ix_tenant_org", "organization_id"),
    )
