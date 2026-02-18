"""API routes for enterprise features: SSO, audit, compliance, tenant."""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_user
from src.api.schemas.enterprise import (
    AdminStatsResponse,
    AuditEntryResponse,
    AuditListResponse,
    PolicyCreateRequest,
    PolicyListResponse,
    PolicyResponse,
    PolicyUpdateRequest,
    SSOConfigRequest,
    SSOConfigResponse,
    TenantSettingsRequest,
    TenantSettingsResponse,
)
from src.database.connection import get_session
from src.models.organization import OrganizationMember
from src.models.user import User
from src.services.enterprise_service import enterprise_service

router = APIRouter()


async def _verify_org_access(
    session: AsyncSession, org_id: int, user_id: int,
) -> None:
    """Verify the user is a member of the organization."""
    r = await session.execute(
        select(OrganizationMember.id).where(and_(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id)))
    if r.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=403, detail="Not a member of this organization")


def _sso_response(c) -> SSOConfigResponse:
    return SSOConfigResponse(
        id=c.id, organization_id=c.organization_id,
        provider=c.provider, entity_id=c.entity_id,
        metadata_url=c.metadata_url, is_enabled=c.is_enabled,
        auto_provision=c.auto_provision, default_role=c.default_role,
        created_at=c.created_at.isoformat() if c.created_at else None)


def _audit_response(e) -> AuditEntryResponse:
    return AuditEntryResponse(
        id=e.id, organization_id=e.organization_id,
        user_id=e.user_id, action=e.action,
        resource_type=e.resource_type, resource_id=e.resource_id,
        before_state=e.before_state, after_state=e.after_state,
        ip_address=e.ip_address, compliance_tags=e.compliance_tags,
        created_at=e.created_at.isoformat() if e.created_at else None)


def _policy_response(p) -> PolicyResponse:
    return PolicyResponse(
        id=p.id, organization_id=p.organization_id,
        policy_type=p.policy_type, name=p.name,
        description=p.description, rules=p.rules if p.rules else {},
        is_enforced=p.is_enforced,
        last_evaluated_at=p.last_evaluated_at.isoformat() if p.last_evaluated_at else None,
        created_at=p.created_at.isoformat() if p.created_at else None)


def _tenant_response(t) -> TenantSettingsResponse:
    return TenantSettingsResponse(
        id=t.id, organization_id=t.organization_id,
        max_users=t.max_users, max_patents_tracked=t.max_patents_tracked,
        allowed_features=t.allowed_features if t.allowed_features else {},
        data_region=t.data_region, is_isolated=t.is_isolated,
        custom_branding=t.custom_branding,
        created_at=t.created_at.isoformat() if t.created_at else None)


# ---- SSO Config ----

@router.get("/{org_id}/sso", response_model=SSOConfigResponse)
async def get_sso_config(
    org_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SSOConfigResponse:
    await _verify_org_access(session, org_id, current_user.id)
    config = await enterprise_service.get_sso_config(session, org_id)
    if config is None:
        raise HTTPException(status_code=404, detail="SSO config not found")
    return _sso_response(config)

@router.put("/{org_id}/sso", response_model=SSOConfigResponse)
async def upsert_sso_config(
    org_id: int, payload: SSOConfigRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SSOConfigResponse:
    await _verify_org_access(session, org_id, current_user.id)
    config = await enterprise_service.upsert_sso_config(
        session, organization_id=org_id, provider=payload.provider,
        entity_id=payload.entity_id, metadata_url=payload.metadata_url,
        certificate=payload.certificate, is_enabled=payload.is_enabled,
        auto_provision=payload.auto_provision,
        default_role=payload.default_role)
    await session.commit()
    return _sso_response(config)

@router.delete("/{org_id}/sso")
async def delete_sso_config(
    org_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    await _verify_org_access(session, org_id, current_user.id)
    try:
        await enterprise_service.delete_sso_config(session, org_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return {"success": True}

# ---- Audit Log ----

@router.get("/{org_id}/audit", response_model=AuditListResponse)
async def list_audit_entries(
    org_id: int,
    action: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AuditListResponse:
    await _verify_org_access(session, org_id, current_user.id)
    entries = await enterprise_service.list_audit_entries(
        session, organization_id=org_id, action=action,
        user_id=user_id, limit=limit, offset=offset)
    total = await enterprise_service.count_audit_entries(session, org_id)
    return AuditListResponse(
        entries=[_audit_response(e) for e in entries], total=total)

# ---- Compliance Policies ----

@router.get("/{org_id}/policies", response_model=PolicyListResponse)
async def list_policies(
    org_id: int,
    policy_type: str | None = Query(default=None),
    enforced: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PolicyListResponse:
    await _verify_org_access(session, org_id, current_user.id)
    policies = await enterprise_service.list_policies(
        session, organization_id=org_id,
        policy_type=policy_type, enforced_only=enforced)
    return PolicyListResponse(
        policies=[_policy_response(p) for p in policies])

@router.post(
    "/{org_id}/policies", response_model=PolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_policy(
    org_id: int, payload: PolicyCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PolicyResponse:
    await _verify_org_access(session, org_id, current_user.id)
    p = await enterprise_service.create_policy(
        session, organization_id=org_id, policy_type=payload.policy_type,
        name=payload.name, description=payload.description,
        rules=payload.rules, is_enforced=payload.is_enforced)
    await session.commit()
    return _policy_response(p)

@router.patch("/{org_id}/policies/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    org_id: int, policy_id: int, payload: PolicyUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PolicyResponse:
    await _verify_org_access(session, org_id, current_user.id)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    try:
        p = await enterprise_service.update_policy(
            session, policy_id=policy_id,
            organization_id=org_id, **updates)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return _policy_response(p)

@router.post(
    "/{org_id}/policies/{policy_id}/evaluate",
    response_model=PolicyResponse,
)
async def evaluate_policy(
    org_id: int, policy_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PolicyResponse:
    await _verify_org_access(session, org_id, current_user.id)
    try:
        p = await enterprise_service.evaluate_policy(
            session, policy_id=policy_id, organization_id=org_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return _policy_response(p)

@router.delete("/{org_id}/policies/{policy_id}")
async def delete_policy(
    org_id: int, policy_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    await _verify_org_access(session, org_id, current_user.id)
    try:
        await enterprise_service.delete_policy(
            session, policy_id=policy_id, organization_id=org_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return {"success": True}

# ---- Tenant Settings ----

@router.get("/{org_id}/tenant", response_model=TenantSettingsResponse)
async def get_tenant_settings(
    org_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TenantSettingsResponse:
    await _verify_org_access(session, org_id, current_user.id)
    ts = await enterprise_service.get_tenant_settings(session, org_id)
    if ts is None:
        raise HTTPException(status_code=404, detail="Tenant settings not found")
    return _tenant_response(ts)

@router.put("/{org_id}/tenant", response_model=TenantSettingsResponse)
async def upsert_tenant_settings(
    org_id: int, payload: TenantSettingsRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TenantSettingsResponse:
    await _verify_org_access(session, org_id, current_user.id)
    ts = await enterprise_service.upsert_tenant_settings(
        session, organization_id=org_id,
        **payload.model_dump(exclude_unset=True))
    await session.commit()
    return _tenant_response(ts)

# ---- Admin Dashboard ----

@router.get("/{org_id}/admin/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    org_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AdminStatsResponse:
    await _verify_org_access(session, org_id, current_user.id)
    stats = await enterprise_service.get_admin_stats(session, org_id)
    return AdminStatsResponse(**stats)
