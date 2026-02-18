"""Tests for the EnterpriseService."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.enterprise import (
    AuditEntry,
    CompliancePolicy,
    SSOConfig,
    TenantSettings,
)
from src.services.enterprise_service import EnterpriseService


class _R:
    def __init__(self, val=None, rows=None):
        self._v, self._rows = val, rows or []
    def scalar_one_or_none(self): return self._v
    def scalar_one(self): return self._v
    def scalars(self): return SimpleNamespace(all=lambda: self._rows)

def _svc(): return EnterpriseService()

def _sess():
    s = AsyncMock()
    s.add = MagicMock()
    s.flush, s.refresh, s.delete = AsyncMock(), AsyncMock(), AsyncMock()
    return s

def _sso(sid=1, oid=1, provider="okta", enabled=False):
    return SSOConfig(
        id=sid, organization_id=oid, provider=provider,
        entity_id="https://idp.example.com", metadata_url=None,
        certificate=None, is_enabled=enabled,
        auto_provision=False, default_role="viewer")

def _audit(aid=1, oid=1, action="user.login"):
    return AuditEntry(
        id=aid, organization_id=oid, user_id=1, action=action,
        resource_type=None, resource_id=None, before_state=None,
        after_state=None, ip_address=None, user_agent=None,
        compliance_tags=None)

def _policy(pid=1, oid=1, ptype="data_retention", enforced=False):
    return CompliancePolicy(
        id=pid, organization_id=oid, policy_type=ptype,
        name="Test Policy", description=None, rules={},
        is_enforced=enforced, last_evaluated_at=None)

def _tenant(tid=1, oid=1):
    return TenantSettings(
        id=tid, organization_id=oid, max_users=50,
        max_patents_tracked=10000, allowed_features={},
        data_region="us-east", is_isolated=False, custom_branding=None)


# ---- SSO Config ----

@pytest.mark.asyncio
async def test_get_sso_config():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=_sso())
    r = await svc.get_sso_config(s, organization_id=1)
    assert r is not None and r.provider == "okta"

@pytest.mark.asyncio
async def test_get_sso_config_none():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=None)
    assert await svc.get_sso_config(s, organization_id=999) is None

@pytest.mark.asyncio
async def test_upsert_sso_config_create(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "get_sso_config", AsyncMock(return_value=None))
    r = await svc.upsert_sso_config(
        s, organization_id=1, provider="okta",
        entity_id="https://idp.example.com")
    s.add.assert_called_once()
    assert r.provider == "okta"

@pytest.mark.asyncio
async def test_upsert_sso_config_update(monkeypatch):
    svc, s = _svc(), _sess()
    existing = _sso()
    monkeypatch.setattr(svc, "get_sso_config", AsyncMock(return_value=existing))
    r = await svc.upsert_sso_config(
        s, organization_id=1, provider="azure_ad",
        entity_id="https://new.example.com", is_enabled=True)
    assert r.provider == "azure_ad" and r.is_enabled is True
    s.add.assert_not_called()

@pytest.mark.asyncio
async def test_delete_sso_config(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "get_sso_config", AsyncMock(return_value=_sso()))
    assert await svc.delete_sso_config(s, organization_id=1) is True

@pytest.mark.asyncio
async def test_delete_sso_config_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "get_sso_config", AsyncMock(return_value=None))
    with pytest.raises(ValueError, match="SSO config not found"):
        await svc.delete_sso_config(s, organization_id=999)


# ---- Audit Log ----

@pytest.mark.asyncio
async def test_list_audit_entries():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_audit(1), _audit(2)])
    r = await svc.list_audit_entries(s, organization_id=1)
    assert len(r) == 2

@pytest.mark.asyncio
async def test_list_audit_entries_with_filters():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_audit(action="user.login")])
    r = await svc.list_audit_entries(
        s, organization_id=1, action="user.login", user_id=1)
    assert len(r) == 1

@pytest.mark.asyncio
async def test_create_audit_entry():
    svc, s = _svc(), _sess()
    r = await svc.create_audit_entry(
        s, organization_id=1, action="user.login", user_id=1,
        ip_address="127.0.0.1", compliance_tags=["gdpr"])
    s.add.assert_called_once()
    assert r.action == "user.login"

@pytest.mark.asyncio
async def test_create_audit_entry_with_state():
    svc, s = _svc(), _sess()
    r = await svc.create_audit_entry(
        s, organization_id=1, action="policy.update",
        before_state={"enforced": False},
        after_state={"enforced": True})
    assert r.before_state == {"enforced": False}

@pytest.mark.asyncio
async def test_count_audit_entries():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=42)
    assert await svc.count_audit_entries(s, organization_id=1) == 42


# ---- Compliance Policies ----

@pytest.mark.asyncio
async def test_list_policies():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_policy(1), _policy(2)])
    r = await svc.list_policies(s, organization_id=1)
    assert len(r) == 2

@pytest.mark.asyncio
async def test_list_policies_by_type():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_policy(ptype="encryption")])
    r = await svc.list_policies(
        s, organization_id=1, policy_type="encryption")
    assert len(r) == 1

@pytest.mark.asyncio
async def test_list_policies_enforced_only():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_policy(enforced=True)])
    r = await svc.list_policies(
        s, organization_id=1, enforced_only=True)
    assert len(r) == 1

@pytest.mark.asyncio
async def test_create_policy():
    svc, s = _svc(), _sess()
    r = await svc.create_policy(
        s, organization_id=1, policy_type="data_retention",
        name="Retain 7 years", rules={"years": 7})
    s.add.assert_called_once()
    assert r.name == "Retain 7 years" and r.rules == {"years": 7}

@pytest.mark.asyncio
async def test_update_policy(monkeypatch):
    svc, s = _svc(), _sess()
    p = _policy()
    monkeypatch.setattr(svc, "_get_org_policy", AsyncMock(return_value=p))
    r = await svc.update_policy(
        s, 1, 1, name="Updated", is_enforced=True,
        description="Desc", rules={"years": 10})
    assert r.name == "Updated" and r.is_enforced is True
    assert r.description == "Desc" and r.rules == {"years": 10}

@pytest.mark.asyncio
async def test_update_policy_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_org_policy",
        AsyncMock(side_effect=ValueError("not found")))
    with pytest.raises(ValueError):
        await svc.update_policy(s, 999, 1)

@pytest.mark.asyncio
async def test_evaluate_policy(monkeypatch):
    svc, s = _svc(), _sess()
    p = _policy()
    monkeypatch.setattr(svc, "_get_org_policy", AsyncMock(return_value=p))
    r = await svc.evaluate_policy(s, 1, 1)
    assert r.last_evaluated_at is not None
    assert "last_evaluation" in r.rules

@pytest.mark.asyncio
async def test_delete_policy(monkeypatch):
    svc, s = _svc(), _sess()
    p = _policy()
    monkeypatch.setattr(svc, "_get_org_policy", AsyncMock(return_value=p))
    assert await svc.delete_policy(s, 1, 1) is True
    s.delete.assert_awaited_once_with(p)

@pytest.mark.asyncio
async def test_delete_policy_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_org_policy",
        AsyncMock(side_effect=ValueError("not found")))
    with pytest.raises(ValueError):
        await svc.delete_policy(s, 999, 1)


# ---- Tenant Settings ----

@pytest.mark.asyncio
async def test_get_tenant_settings():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=_tenant())
    r = await svc.get_tenant_settings(s, organization_id=1)
    assert r is not None and r.max_users == 50

@pytest.mark.asyncio
async def test_get_tenant_settings_none():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=None)
    assert await svc.get_tenant_settings(s, organization_id=999) is None

@pytest.mark.asyncio
async def test_upsert_tenant_create(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "get_tenant_settings", AsyncMock(return_value=None))
    r = await svc.upsert_tenant_settings(
        s, organization_id=1, max_users=100, data_region="eu-west")
    s.add.assert_called_once()
    assert r.max_users == 100 and r.data_region == "eu-west"

@pytest.mark.asyncio
async def test_upsert_tenant_update(monkeypatch):
    svc, s = _svc(), _sess()
    existing = _tenant()
    monkeypatch.setattr(svc, "get_tenant_settings", AsyncMock(return_value=existing))
    r = await svc.upsert_tenant_settings(
        s, organization_id=1, max_users=200,
        max_patents_tracked=50000, is_isolated=True,
        allowed_features={"sso": True},
        data_region="ap-southeast",
        custom_branding={"logo": "url"})
    assert r.max_users == 200 and r.is_isolated is True
    assert r.data_region == "ap-southeast"
    s.add.assert_not_called()


# ---- Admin Stats ----

@pytest.mark.asyncio
async def test_get_admin_stats(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "count_audit_entries", AsyncMock(return_value=100))
    monkeypatch.setattr(svc, "list_policies",
        AsyncMock(return_value=[_policy(enforced=True), _policy(enforced=False)]))
    monkeypatch.setattr(svc, "get_sso_config",
        AsyncMock(return_value=_sso(enabled=True)))
    monkeypatch.setattr(svc, "get_tenant_settings",
        AsyncMock(return_value=_tenant()))
    r = await svc.get_admin_stats(s, organization_id=1)
    assert r["audit_entry_count"] == 100
    assert r["policy_count"] == 2
    assert r["enforced_policy_count"] == 1
    assert r["sso_enabled"] is True

@pytest.mark.asyncio
async def test_get_admin_stats_no_sso_no_tenant(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "count_audit_entries", AsyncMock(return_value=0))
    monkeypatch.setattr(svc, "list_policies", AsyncMock(return_value=[]))
    monkeypatch.setattr(svc, "get_sso_config", AsyncMock(return_value=None))
    monkeypatch.setattr(svc, "get_tenant_settings", AsyncMock(return_value=None))
    r = await svc.get_admin_stats(s, organization_id=1)
    assert r["sso_enabled"] is False and r["tenant_max_users"] == 50


# ---- Stubs and helpers ----

@pytest.mark.asyncio
async def test_run_evaluation_stub():
    r = await _svc()._run_evaluation("data_retention", {"years": 7})
    assert r["compliant"] is True

@pytest.mark.asyncio
async def test_get_org_policy_success():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=_policy(pid=3))
    assert (await svc._get_org_policy(s, 3, 1)).id == 3

@pytest.mark.asyncio
async def test_get_org_policy_not_found():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="policy not found"):
        await svc._get_org_policy(s, 999, 1)
