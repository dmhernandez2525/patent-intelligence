"""Enterprise service for SSO, audit, compliance, and tenant management."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.enterprise import (
    AuditEntry,
    CompliancePolicy,
    SSOConfig,
    TenantSettings,
)

logger = structlog.get_logger(__name__)


class EnterpriseService:
    """Manage SSO configs, audit logs, compliance policies, and tenant settings."""

    # ---- SSO Configuration ----

    async def get_sso_config(
        self, session: AsyncSession, organization_id: int,
    ) -> SSOConfig | None:
        r = await session.execute(
            select(SSOConfig).where(
                SSOConfig.organization_id == organization_id))
        return r.scalar_one_or_none()

    async def upsert_sso_config(
        self, session: AsyncSession, organization_id: int,
        provider: str, entity_id: str,
        metadata_url: str | None = None, certificate: str | None = None,
        is_enabled: bool = False, auto_provision: bool = False,
        default_role: str = "viewer",
    ) -> SSOConfig:
        existing = await self.get_sso_config(session, organization_id)
        if existing is not None:
            existing.provider = provider
            existing.entity_id = entity_id
            existing.metadata_url = metadata_url
            existing.certificate = certificate
            existing.is_enabled = is_enabled
            existing.auto_provision = auto_provision
            existing.default_role = default_role
            await session.flush()
            return existing
        config = SSOConfig(
            organization_id=organization_id, provider=provider,
            entity_id=entity_id, metadata_url=metadata_url,
            certificate=certificate, is_enabled=is_enabled,
            auto_provision=auto_provision, default_role=default_role)
        session.add(config)
        await session.flush()
        await session.refresh(config)
        return config

    async def delete_sso_config(
        self, session: AsyncSession, organization_id: int,
    ) -> bool:
        config = await self.get_sso_config(session, organization_id)
        if config is None:
            raise ValueError("SSO config not found")
        await session.delete(config)
        return True

    # ---- Audit Log ----

    async def list_audit_entries(
        self, session: AsyncSession, organization_id: int,
        action: str | None = None, user_id: int | None = None,
        limit: int = 50, offset: int = 0,
    ) -> list[AuditEntry]:
        stmt = select(AuditEntry).where(
            AuditEntry.organization_id == organization_id)
        if action is not None:
            stmt = stmt.where(AuditEntry.action == action)
        if user_id is not None:
            stmt = stmt.where(AuditEntry.user_id == user_id)
        stmt = stmt.order_by(AuditEntry.created_at.desc())
        stmt = stmt.limit(limit).offset(offset)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def create_audit_entry(
        self, session: AsyncSession, organization_id: int,
        action: str, user_id: int | None = None,
        resource_type: str | None = None, resource_id: str | None = None,
        before_state: dict | None = None, after_state: dict | None = None,
        ip_address: str | None = None, user_agent: str | None = None,
        compliance_tags: list[str] | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            organization_id=organization_id, user_id=user_id,
            action=action, resource_type=resource_type,
            resource_id=resource_id, before_state=before_state,
            after_state=after_state, ip_address=ip_address,
            user_agent=user_agent, compliance_tags=compliance_tags)
        session.add(entry)
        await session.flush()
        await session.refresh(entry)
        return entry

    async def count_audit_entries(
        self, session: AsyncSession, organization_id: int,
    ) -> int:
        r = await session.execute(
            select(func.count(AuditEntry.id)).where(
                AuditEntry.organization_id == organization_id))
        return r.scalar_one()

    # ---- Compliance Policies ----

    async def list_policies(
        self, session: AsyncSession, organization_id: int,
        policy_type: str | None = None,
        enforced_only: bool = False,
    ) -> list[CompliancePolicy]:
        stmt = select(CompliancePolicy).where(
            CompliancePolicy.organization_id == organization_id)
        if policy_type is not None:
            stmt = stmt.where(CompliancePolicy.policy_type == policy_type)
        if enforced_only:
            stmt = stmt.where(CompliancePolicy.is_enforced.is_(True))
        stmt = stmt.order_by(CompliancePolicy.created_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def create_policy(
        self, session: AsyncSession, organization_id: int,
        policy_type: str, name: str,
        description: str | None = None, rules: dict | None = None,
        is_enforced: bool = False,
    ) -> CompliancePolicy:
        policy = CompliancePolicy(
            organization_id=organization_id, policy_type=policy_type,
            name=name, description=description,
            rules=rules or {}, is_enforced=is_enforced)
        session.add(policy)
        await session.flush()
        await session.refresh(policy)
        return policy

    async def update_policy(
        self, session: AsyncSession, policy_id: int, organization_id: int,
        name: str | None = None, description: str | None = None,
        rules: dict | None = None, is_enforced: bool | None = None,
    ) -> CompliancePolicy:
        policy = await self._get_org_policy(session, policy_id, organization_id)
        if name is not None:
            policy.name = name
        if description is not None:
            policy.description = description
        if rules is not None:
            policy.rules = rules
        if is_enforced is not None:
            policy.is_enforced = is_enforced
        await session.flush()
        return policy

    async def evaluate_policy(
        self, session: AsyncSession, policy_id: int, organization_id: int,
    ) -> CompliancePolicy:
        policy = await self._get_org_policy(session, policy_id, organization_id)
        result = await self._run_evaluation(policy.policy_type, policy.rules)
        policy.last_evaluated_at = datetime.now(UTC)
        policy.rules = {**policy.rules, "last_evaluation": result}
        await session.flush()
        return policy

    async def delete_policy(
        self, session: AsyncSession, policy_id: int, organization_id: int,
    ) -> bool:
        policy = await self._get_org_policy(session, policy_id, organization_id)
        await session.delete(policy)
        return True

    # ---- Tenant Settings ----

    async def get_tenant_settings(
        self, session: AsyncSession, organization_id: int,
    ) -> TenantSettings | None:
        r = await session.execute(
            select(TenantSettings).where(
                TenantSettings.organization_id == organization_id))
        return r.scalar_one_or_none()

    async def upsert_tenant_settings(
        self, session: AsyncSession, organization_id: int,
        max_users: int | None = None,
        max_patents_tracked: int | None = None,
        allowed_features: dict | None = None,
        data_region: str | None = None,
        is_isolated: bool | None = None,
        custom_branding: dict | None = None,
    ) -> TenantSettings:
        existing = await self.get_tenant_settings(session, organization_id)
        if existing is not None:
            if max_users is not None:
                existing.max_users = max_users
            if max_patents_tracked is not None:
                existing.max_patents_tracked = max_patents_tracked
            if allowed_features is not None:
                existing.allowed_features = allowed_features
            if data_region is not None:
                existing.data_region = data_region
            if is_isolated is not None:
                existing.is_isolated = is_isolated
            if custom_branding is not None:
                existing.custom_branding = custom_branding
            await session.flush()
            return existing
        ts = TenantSettings(
            organization_id=organization_id,
            max_users=max_users or 50,
            max_patents_tracked=max_patents_tracked or 10000,
            allowed_features=allowed_features or {},
            data_region=data_region or "us-east",
            is_isolated=is_isolated or False,
            custom_branding=custom_branding)
        session.add(ts)
        await session.flush()
        await session.refresh(ts)
        return ts

    # ---- Admin Dashboard ----

    async def get_admin_stats(
        self, session: AsyncSession, organization_id: int,
    ) -> dict:
        audit_count = await self.count_audit_entries(session, organization_id)
        policies = await self.list_policies(session, organization_id)
        sso = await self.get_sso_config(session, organization_id)
        tenant = await self.get_tenant_settings(session, organization_id)
        return {
            "audit_entry_count": audit_count,
            "policy_count": len(policies),
            "enforced_policy_count": sum(1 for p in policies if p.is_enforced),
            "sso_enabled": sso.is_enabled if sso else False,
            "tenant_max_users": tenant.max_users if tenant else 50,
            "tenant_is_isolated": tenant.is_isolated if tenant else False,
        }

    # ---- Stubs ----

    async def _run_evaluation(
        self, policy_type: str, rules: dict,
    ) -> dict:
        logger.info("compliance.evaluate", policy_type=policy_type)
        return {
            "compliant": True, "violations": [],
            "evaluated_at": datetime.now(UTC).isoformat(),
        }

    # ---- Internal helpers ----

    async def _get_org_policy(
        self, session: AsyncSession, policy_id: int, organization_id: int,
    ) -> CompliancePolicy:
        r = await session.execute(
            select(CompliancePolicy).where(and_(
                CompliancePolicy.id == policy_id,
                CompliancePolicy.organization_id == organization_id)))
        p = r.scalar_one_or_none()
        if p is None:
            raise ValueError("Compliance policy not found")
        return p


enterprise_service = EnterpriseService()
