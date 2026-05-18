"""Add enterprise features: SSO, audit, compliance, tenant settings.

Revision ID: 20260215_0010
Revises: 20260215_0009
Create Date: 2026-02-15
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260215_0010"
down_revision = "20260215_0009"
branch_labels = None
depends_on = None


def _ts() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "sso_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(500), nullable=False),
        sa.Column("metadata_url", sa.String(1000), nullable=True),
        sa.Column("certificate", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("auto_provision", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("default_role", sa.String(20), server_default=sa.text("'viewer'")),
        *_ts(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id"),
    )
    op.create_index("ix_sso_config_org", "sso_configs", ["organization_id"])

    op.create_table(
        "audit_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("before_state", postgresql.JSONB(), nullable=True),
        sa.Column("after_state", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("compliance_tags", postgresql.JSONB(), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_audit_org_action", "audit_entries", ["organization_id", "action"])
    op.create_index("ix_audit_org_created", "audit_entries", ["organization_id", "created_at"])
    op.create_index("ix_audit_user", "audit_entries", ["user_id"])

    op.create_table(
        "compliance_policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("policy_type", sa.String(30), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rules", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_enforced", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_compliance_org_type", "compliance_policies", ["organization_id", "policy_type"])

    op.create_table(
        "tenant_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("max_users", sa.Integer(), server_default=sa.text("50")),
        sa.Column("max_patents_tracked", sa.Integer(), server_default=sa.text("10000")),
        sa.Column("allowed_features", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("data_region", sa.String(20), server_default=sa.text("'us-east'")),
        sa.Column("is_isolated", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("custom_branding", postgresql.JSONB(), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id"),
    )
    op.create_index("ix_tenant_org", "tenant_settings", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_tenant_org")
    op.drop_table("tenant_settings")
    op.drop_index("ix_compliance_org_type")
    op.drop_table("compliance_policies")
    op.drop_index("ix_audit_user")
    op.drop_index("ix_audit_org_created")
    op.drop_index("ix_audit_org_action")
    op.drop_table("audit_entries")
    op.drop_index("ix_sso_config_org")
    op.drop_table("sso_configs")
