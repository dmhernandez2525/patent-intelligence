"""Tests for enterprise feature API routes."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.api.routes import enterprise as ent_mod


def _user(uid=1):
    return SimpleNamespace(id=uid, email="u@test.com", role="admin")

def _session():
    s = AsyncMock()
    s.commit = AsyncMock()
    return s

def _sso(sid=1, oid=1, provider="okta"):
    return SimpleNamespace(
        id=sid, organization_id=oid, provider=provider,
        entity_id="https://idp.example.com", metadata_url=None,
        is_enabled=True, auto_provision=False,
        default_role="viewer", created_at=None)

def _audit(aid=1, oid=1, action="user.login"):
    return SimpleNamespace(
        id=aid, organization_id=oid, user_id=1, action=action,
        resource_type=None, resource_id=None, before_state=None,
        after_state=None, ip_address=None, compliance_tags=None,
        created_at=None)

def _policy(pid=1, oid=1):
    return SimpleNamespace(
        id=pid, organization_id=oid, policy_type="data_retention",
        name="Test", description=None, rules={},
        is_enforced=False, last_evaluated_at=None, created_at=None)

def _tenant(tid=1, oid=1):
    return SimpleNamespace(
        id=tid, organization_id=oid, max_users=50,
        max_patents_tracked=10000, allowed_features={},
        data_region="us-east", is_isolated=False,
        custom_branding=None, created_at=None)

def _patch(mp, name, rv=None, exc=None):
    mock = AsyncMock(side_effect=exc) if exc else AsyncMock(return_value=rv)
    mp.setattr(ent_mod, "enterprise_service",
        SimpleNamespace(**{name: mock}))


# ---- SSO Config ----

@pytest.mark.asyncio
async def test_get_sso_config(monkeypatch):
    _patch(monkeypatch, "get_sso_config", rv=_sso())
    r = await ent_mod.get_sso_config(
        org_id=1, current_user=_user(), session=_session())
    assert r.provider == "okta"

@pytest.mark.asyncio
async def test_get_sso_config_not_found(monkeypatch):
    _patch(monkeypatch, "get_sso_config", rv=None)
    with pytest.raises(HTTPException) as exc_info:
        await ent_mod.get_sso_config(
            org_id=999, current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404

@pytest.mark.asyncio
async def test_upsert_sso_config(monkeypatch):
    _patch(monkeypatch, "upsert_sso_config", rv=_sso())
    payload = SimpleNamespace(
        provider="okta", entity_id="https://idp.example.com",
        metadata_url=None, certificate=None,
        is_enabled=True, auto_provision=False, default_role="viewer")
    r = await ent_mod.upsert_sso_config(
        org_id=1, payload=payload,
        current_user=_user(), session=_session())
    assert r.provider == "okta"

@pytest.mark.asyncio
async def test_delete_sso_config(monkeypatch):
    _patch(monkeypatch, "delete_sso_config", rv=True)
    r = await ent_mod.delete_sso_config(
        org_id=1, current_user=_user(), session=_session())
    assert r == {"success": True}

@pytest.mark.asyncio
async def test_delete_sso_config_not_found(monkeypatch):
    _patch(monkeypatch, "delete_sso_config", exc=ValueError("not found"))
    with pytest.raises(HTTPException) as exc_info:
        await ent_mod.delete_sso_config(
            org_id=999, current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404


# ---- Audit Log ----

@pytest.mark.asyncio
async def test_list_audit_entries(monkeypatch):
    svc_ns = SimpleNamespace(
        list_audit_entries=AsyncMock(return_value=[_audit(1), _audit(2)]),
        count_audit_entries=AsyncMock(return_value=2))
    monkeypatch.setattr(ent_mod, "enterprise_service", svc_ns)
    r = await ent_mod.list_audit_entries(
        org_id=1, action=None, user_id=None,
        limit=50, offset=0,
        current_user=_user(), session=_session())
    assert len(r.entries) == 2 and r.total == 2


# ---- Compliance Policies ----

@pytest.mark.asyncio
async def test_list_policies(monkeypatch):
    _patch(monkeypatch, "list_policies", rv=[_policy(1), _policy(2)])
    r = await ent_mod.list_policies(
        org_id=1, policy_type=None, enforced=False,
        current_user=_user(), session=_session())
    assert len(r.policies) == 2

@pytest.mark.asyncio
async def test_create_policy(monkeypatch):
    _patch(monkeypatch, "create_policy", rv=_policy(5))
    payload = SimpleNamespace(
        policy_type="data_retention", name="Retain",
        description=None, rules={}, is_enforced=False)
    r = await ent_mod.create_policy(
        org_id=1, payload=payload,
        current_user=_user(), session=_session())
    assert r.id == 5

@pytest.mark.asyncio
async def test_update_policy(monkeypatch):
    p = _policy(1)
    p.name = "Updated"
    _patch(monkeypatch, "update_policy", rv=p)
    payload = SimpleNamespace(model_dump=lambda exclude_unset: {"name": "Updated"})
    r = await ent_mod.update_policy(
        org_id=1, policy_id=1, payload=payload,
        current_user=_user(), session=_session())
    assert r.name == "Updated"

@pytest.mark.asyncio
async def test_update_policy_not_found(monkeypatch):
    _patch(monkeypatch, "update_policy", exc=ValueError("not found"))
    payload = SimpleNamespace(model_dump=lambda exclude_unset: {"name": "X"})
    with pytest.raises(HTTPException) as exc_info:
        await ent_mod.update_policy(
            org_id=1, policy_id=999, payload=payload,
            current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404

@pytest.mark.asyncio
async def test_update_policy_no_updates(monkeypatch):
    payload = SimpleNamespace(model_dump=lambda exclude_unset: {})
    with pytest.raises(HTTPException) as exc_info:
        await ent_mod.update_policy(
            org_id=1, policy_id=1, payload=payload,
            current_user=_user(), session=_session())
    assert exc_info.value.status_code == 400

@pytest.mark.asyncio
async def test_evaluate_policy(monkeypatch):
    _patch(monkeypatch, "evaluate_policy", rv=_policy(1))
    r = await ent_mod.evaluate_policy(
        org_id=1, policy_id=1,
        current_user=_user(), session=_session())
    assert r.id == 1

@pytest.mark.asyncio
async def test_evaluate_policy_not_found(monkeypatch):
    _patch(monkeypatch, "evaluate_policy", exc=ValueError("not found"))
    with pytest.raises(HTTPException) as exc_info:
        await ent_mod.evaluate_policy(
            org_id=1, policy_id=999,
            current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404

@pytest.mark.asyncio
async def test_delete_policy(monkeypatch):
    _patch(monkeypatch, "delete_policy", rv=True)
    r = await ent_mod.delete_policy(
        org_id=1, policy_id=1,
        current_user=_user(), session=_session())
    assert r == {"success": True}

@pytest.mark.asyncio
async def test_delete_policy_not_found(monkeypatch):
    _patch(monkeypatch, "delete_policy", exc=ValueError("not found"))
    with pytest.raises(HTTPException) as exc_info:
        await ent_mod.delete_policy(
            org_id=1, policy_id=999,
            current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404


# ---- Tenant Settings ----

@pytest.mark.asyncio
async def test_get_tenant_settings(monkeypatch):
    _patch(monkeypatch, "get_tenant_settings", rv=_tenant())
    r = await ent_mod.get_tenant_settings(
        org_id=1, current_user=_user(), session=_session())
    assert r.max_users == 50

@pytest.mark.asyncio
async def test_get_tenant_settings_not_found(monkeypatch):
    _patch(monkeypatch, "get_tenant_settings", rv=None)
    with pytest.raises(HTTPException) as exc_info:
        await ent_mod.get_tenant_settings(
            org_id=999, current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404

@pytest.mark.asyncio
async def test_upsert_tenant_settings(monkeypatch):
    _patch(monkeypatch, "upsert_tenant_settings", rv=_tenant())
    payload = SimpleNamespace(
        model_dump=lambda exclude_unset: {"max_users": 100})
    r = await ent_mod.upsert_tenant_settings(
        org_id=1, payload=payload,
        current_user=_user(), session=_session())
    assert r.max_users == 50


# ---- Admin Dashboard ----

@pytest.mark.asyncio
async def test_get_admin_stats(monkeypatch):
    _patch(monkeypatch, "get_admin_stats", rv={
        "audit_entry_count": 100, "policy_count": 2,
        "enforced_policy_count": 1, "sso_enabled": True,
        "tenant_max_users": 50, "tenant_is_isolated": False})
    r = await ent_mod.get_admin_stats(
        org_id=1, current_user=_user(), session=_session())
    assert r.audit_entry_count == 100
