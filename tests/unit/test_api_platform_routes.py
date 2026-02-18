"""Tests for API platform routes."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.api.routes import api_platform as plat_mod


def _user(uid=1):
    return SimpleNamespace(id=uid, email="u@test.com", role="analyst")

def _session():
    s = AsyncMock()
    s.commit = AsyncMock()
    return s

def _req():
    return SimpleNamespace(
        client=SimpleNamespace(host="127.0.0.1"),
        headers={"User-Agent": "test"})

def _key(kid=1, name="Test Key"):
    return SimpleNamespace(
        id=kid, name=name, key_prefix="pi_test12345",
        tier="free", scopes={}, rate_limit_per_minute=100,
        is_active=True, last_used_at=None, expires_at=None,
        created_at=None)

def _webhook(wid=1, url="https://example.com/hook"):
    return SimpleNamespace(
        id=wid, url=url, events={}, is_active=True,
        description=None, failure_count=0,
        last_triggered_at=None, created_at=None)

def _delivery(did=1):
    return SimpleNamespace(
        id=did, endpoint_id=1, event_type="patent.created",
        payload={"id": 1}, response_status=200,
        success=True, attempt_count=1,
        next_retry_at=None, created_at=None)

def _patch(mp, name, rv=None, exc=None):
    mock = AsyncMock(side_effect=exc) if exc else AsyncMock(return_value=rv)
    mp.setattr(plat_mod, "api_platform_service",
        SimpleNamespace(**{name: mock}))

def _patch_act(mp):
    act = SimpleNamespace(log_event=AsyncMock())
    mp.setattr(plat_mod, "activity_service", act)
    return act


# ---- API Keys ----

@pytest.mark.asyncio
async def test_list_api_keys(monkeypatch):
    _patch(monkeypatch, "list_api_keys", rv=[_key(1), _key(2)])
    r = await plat_mod.list_api_keys(
        active=False, current_user=_user(), session=_session())
    assert len(r.keys) == 2

@pytest.mark.asyncio
async def test_create_api_key(monkeypatch):
    _patch(monkeypatch, "create_api_key", rv=(_key(5), "pi_rawkey123"))
    _patch_act(monkeypatch)
    payload = SimpleNamespace(
        name="Key", tier="free", scopes={}, expires_in_days=None)
    r = await plat_mod.create_api_key(
        payload=payload, request=_req(),
        current_user=_user(), session=_session())
    assert r.id == 5 and r.raw_key == "pi_rawkey123"

@pytest.mark.asyncio
async def test_create_api_key_logs_activity(monkeypatch):
    _patch(monkeypatch, "create_api_key", rv=(_key(5), "pi_rawkey123"))
    act = _patch_act(monkeypatch)
    payload = SimpleNamespace(
        name="Key", tier="standard", scopes={}, expires_in_days=None)
    await plat_mod.create_api_key(
        payload=payload, request=_req(),
        current_user=_user(), session=_session())
    assert act.log_event.call_args[1]["event_type"] == "api.key.created"

@pytest.mark.asyncio
async def test_revoke_api_key(monkeypatch):
    _patch(monkeypatch, "revoke_api_key", rv=True)
    r = await plat_mod.revoke_api_key(
        key_id=1, current_user=_user(), session=_session())
    assert r == {"success": True}

@pytest.mark.asyncio
async def test_revoke_api_key_not_found(monkeypatch):
    _patch(monkeypatch, "revoke_api_key", exc=ValueError("not found"))
    with pytest.raises(HTTPException) as exc_info:
        await plat_mod.revoke_api_key(
            key_id=999, current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404

@pytest.mark.asyncio
async def test_delete_api_key(monkeypatch):
    _patch(monkeypatch, "delete_api_key", rv=True)
    r = await plat_mod.delete_api_key(
        key_id=1, current_user=_user(), session=_session())
    assert r == {"success": True}

@pytest.mark.asyncio
async def test_delete_api_key_not_found(monkeypatch):
    _patch(monkeypatch, "delete_api_key", exc=ValueError("not found"))
    with pytest.raises(HTTPException) as exc_info:
        await plat_mod.delete_api_key(
            key_id=999, current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404


# ---- Webhooks ----

@pytest.mark.asyncio
async def test_list_webhooks(monkeypatch):
    _patch(monkeypatch, "list_webhooks", rv=[_webhook(1)])
    r = await plat_mod.list_webhooks(
        active=False, current_user=_user(), session=_session())
    assert len(r.webhooks) == 1

@pytest.mark.asyncio
async def test_create_webhook(monkeypatch):
    _patch(monkeypatch, "create_webhook", rv=_webhook(3))
    _patch_act(monkeypatch)
    payload = SimpleNamespace(
        url="https://example.com", events={}, description=None)
    r = await plat_mod.create_webhook(
        payload=payload, request=_req(),
        current_user=_user(), session=_session())
    assert r.id == 3

@pytest.mark.asyncio
async def test_update_webhook(monkeypatch):
    wh = _webhook(1)
    wh.url = "https://new.example.com"
    _patch(monkeypatch, "update_webhook", rv=wh)
    payload = SimpleNamespace(
        model_dump=lambda exclude_unset: {"url": "https://new.example.com"})
    r = await plat_mod.update_webhook(
        webhook_id=1, payload=payload,
        current_user=_user(), session=_session())
    assert r.url == "https://new.example.com"

@pytest.mark.asyncio
async def test_update_webhook_not_found(monkeypatch):
    _patch(monkeypatch, "update_webhook", exc=ValueError("not found"))
    payload = SimpleNamespace(
        model_dump=lambda exclude_unset: {"url": "https://x.com"})
    with pytest.raises(HTTPException) as exc_info:
        await plat_mod.update_webhook(
            webhook_id=999, payload=payload,
            current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404

@pytest.mark.asyncio
async def test_update_webhook_no_updates(monkeypatch):
    payload = SimpleNamespace(model_dump=lambda exclude_unset: {})
    with pytest.raises(HTTPException) as exc_info:
        await plat_mod.update_webhook(
            webhook_id=1, payload=payload,
            current_user=_user(), session=_session())
    assert exc_info.value.status_code == 400

@pytest.mark.asyncio
async def test_delete_webhook(monkeypatch):
    _patch(monkeypatch, "delete_webhook", rv=True)
    r = await plat_mod.delete_webhook(
        webhook_id=1, current_user=_user(), session=_session())
    assert r == {"success": True}

@pytest.mark.asyncio
async def test_delete_webhook_not_found(monkeypatch):
    _patch(monkeypatch, "delete_webhook", exc=ValueError("not found"))
    with pytest.raises(HTTPException) as exc_info:
        await plat_mod.delete_webhook(
            webhook_id=999, current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404


# ---- Deliveries ----

@pytest.mark.asyncio
async def test_list_deliveries(monkeypatch):
    _patch(monkeypatch, "list_deliveries", rv=[_delivery(1), _delivery(2)])
    r = await plat_mod.list_deliveries(
        webhook_id=1, limit=50,
        current_user=_user(), session=_session())
    assert len(r.deliveries) == 2


# ---- Usage Stats ----

@pytest.mark.asyncio
async def test_get_usage_stats(monkeypatch):
    _patch(monkeypatch, "get_usage_stats",
        rv={"api_key_count": 3, "webhook_count": 2})
    r = await plat_mod.get_usage_stats(
        current_user=_user(), session=_session())
    assert r.api_key_count == 3 and r.webhook_count == 2
