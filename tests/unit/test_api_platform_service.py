"""Tests for the ApiPlatformService."""
import hashlib
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.api_platform import ApiKey, WebhookDelivery, WebhookEndpoint
from src.services.api_platform_service import ApiPlatformService

_TEST_RAW_KEY = "pi_test12345_abcdef"  # noqa: S105
_TEST_KEY_HASH = hashlib.sha256(_TEST_RAW_KEY.encode()).hexdigest()


class _R:
    def __init__(self, val=None, rows=None):
        self._v, self._rows = val, rows or []
    def scalar_one_or_none(self): return self._v
    def scalar_one(self): return self._v
    def scalars(self): return SimpleNamespace(all=lambda: self._rows)

def _svc(): return ApiPlatformService()

def _sess():
    s = AsyncMock()
    s.add = MagicMock()
    s.flush, s.refresh, s.delete = AsyncMock(), AsyncMock(), AsyncMock()
    return s

def _key(kid=1, uid=1, tier="free", active=True):
    return ApiKey(
        id=kid, user_id=uid, name="Test Key",
        key_hash=_TEST_KEY_HASH, key_prefix=_TEST_RAW_KEY[:12],
        tier=tier, scopes={}, rate_limit_per_minute=100,
        is_active=active, last_used_at=None, expires_at=None)

_TEST_SECRET = "secret123"  # noqa: S105

def _webhook(wid=1, uid=1, active=True):
    return WebhookEndpoint(
        id=wid, user_id=uid, url="https://example.com/hook",
        secret=_TEST_SECRET, events={}, is_active=active,
        description=None, failure_count=0, last_triggered_at=None)

def _delivery(did=1, eid=1, success=True):
    return WebhookDelivery(
        id=did, endpoint_id=eid, event_type="patent.created",
        payload={"patent_id": 1}, response_status=200,
        response_body="OK", success=success,
        attempt_count=1, next_retry_at=None)


# ---- API Keys ----

@pytest.mark.asyncio
async def test_list_api_keys():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_key(1), _key(2)])
    r = await svc.list_api_keys(s, user_id=1)
    assert len(r) == 2

@pytest.mark.asyncio
async def test_list_api_keys_active_only():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_key(active=True)])
    r = await svc.list_api_keys(s, user_id=1, active_only=True)
    assert len(r) == 1

@pytest.mark.asyncio
async def test_create_api_key():
    svc, s = _svc(), _sess()
    api_key, raw_key = await svc.create_api_key(
        s, user_id=1, name="My Key", tier="standard")
    s.add.assert_called_once()
    assert api_key.name == "My Key" and api_key.tier == "standard"
    assert raw_key.startswith("pi_")
    assert api_key.rate_limit_per_minute == 1000

@pytest.mark.asyncio
async def test_create_api_key_with_expiry():
    svc, s = _svc(), _sess()
    api_key, _ = await svc.create_api_key(
        s, user_id=1, name="Temp", expires_in_days=30)
    assert api_key.expires_at is not None

@pytest.mark.asyncio
async def test_create_api_key_with_scopes():
    svc, s = _svc(), _sess()
    api_key, _ = await svc.create_api_key(
        s, user_id=1, name="Scoped",
        scopes={"patents": "read", "search": "read"})
    assert api_key.scopes == {"patents": "read", "search": "read"}

@pytest.mark.asyncio
async def test_validate_api_key_success(monkeypatch):
    svc, s = _svc(), _sess()
    k = _key()
    s.execute.return_value = _R(val=k)
    r = await svc.validate_api_key(s, _TEST_RAW_KEY)
    assert r is not None and r.last_used_at is not None

@pytest.mark.asyncio
async def test_validate_api_key_not_found():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=None)
    assert await svc.validate_api_key(s, "pi_invalid") is None

@pytest.mark.asyncio
async def test_validate_api_key_expired():
    svc, s = _svc(), _sess()
    k = _key()
    k.expires_at = datetime.now(UTC) - timedelta(days=1)
    s.execute.return_value = _R(val=k)
    assert await svc.validate_api_key(s, _TEST_RAW_KEY) is None

@pytest.mark.asyncio
async def test_revoke_api_key(monkeypatch):
    svc, s = _svc(), _sess()
    k = _key()
    monkeypatch.setattr(svc, "_get_user_key", AsyncMock(return_value=k))
    assert await svc.revoke_api_key(s, 1, 1) is True
    assert k.is_active is False

@pytest.mark.asyncio
async def test_revoke_api_key_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_key",
        AsyncMock(side_effect=ValueError("not found")))
    with pytest.raises(ValueError):
        await svc.revoke_api_key(s, 999, 1)

@pytest.mark.asyncio
async def test_delete_api_key(monkeypatch):
    svc, s = _svc(), _sess()
    k = _key()
    monkeypatch.setattr(svc, "_get_user_key", AsyncMock(return_value=k))
    assert await svc.delete_api_key(s, 1, 1) is True
    s.delete.assert_awaited_once_with(k)

@pytest.mark.asyncio
async def test_delete_api_key_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_key",
        AsyncMock(side_effect=ValueError("not found")))
    with pytest.raises(ValueError):
        await svc.delete_api_key(s, 999, 1)


# ---- Webhooks ----

@pytest.mark.asyncio
async def test_list_webhooks():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_webhook(1), _webhook(2)])
    r = await svc.list_webhooks(s, user_id=1)
    assert len(r) == 2

@pytest.mark.asyncio
async def test_list_webhooks_active_only():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_webhook(active=True)])
    r = await svc.list_webhooks(s, user_id=1, active_only=True)
    assert len(r) == 1

@pytest.mark.asyncio
async def test_create_webhook():
    svc, s = _svc(), _sess()
    r = await svc.create_webhook(
        s, user_id=1, url="https://example.com/hook",
        events={"patent.created": True})
    s.add.assert_called_once()
    assert r.url == "https://example.com/hook"
    assert r.secret is not None and len(r.secret) > 0

@pytest.mark.asyncio
async def test_update_webhook(monkeypatch):
    svc, s = _svc(), _sess()
    wh = _webhook()
    monkeypatch.setattr(svc, "_get_user_webhook", AsyncMock(return_value=wh))
    r = await svc.update_webhook(
        s, 1, 1, url="https://new.example.com",
        events={"all": True}, description="New desc", is_active=False)
    assert r.url == "https://new.example.com" and r.is_active is False
    assert r.description == "New desc"

@pytest.mark.asyncio
async def test_update_webhook_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_webhook",
        AsyncMock(side_effect=ValueError("not found")))
    with pytest.raises(ValueError):
        await svc.update_webhook(s, 999, 1)

@pytest.mark.asyncio
async def test_delete_webhook(monkeypatch):
    svc, s = _svc(), _sess()
    wh = _webhook()
    monkeypatch.setattr(svc, "_get_user_webhook", AsyncMock(return_value=wh))
    assert await svc.delete_webhook(s, 1, 1) is True
    s.delete.assert_awaited_once_with(wh)

@pytest.mark.asyncio
async def test_delete_webhook_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_webhook",
        AsyncMock(side_effect=ValueError("not found")))
    with pytest.raises(ValueError):
        await svc.delete_webhook(s, 999, 1)


# ---- Deliveries ----

@pytest.mark.asyncio
async def test_trigger_webhook():
    svc, s = _svc(), _sess()
    d = await svc.trigger_webhook(
        s, endpoint_id=1, event_type="patent.created",
        payload={"id": 42})
    s.add.assert_called_once()
    assert d.success is True and d.response_status == 200

@pytest.mark.asyncio
async def test_trigger_webhook_failure(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_deliver_payload",
        AsyncMock(return_value={"status": 500, "body": "Error", "success": False}))
    d = await svc.trigger_webhook(
        s, endpoint_id=1, event_type="patent.created", payload={})
    assert d.success is False and d.next_retry_at is not None

@pytest.mark.asyncio
async def test_list_deliveries():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_delivery(1), _delivery(2)])
    r = await svc.list_deliveries(s, endpoint_id=1)
    assert len(r) == 2

@pytest.mark.asyncio
async def test_retry_failed_deliveries():
    svc, s = _svc(), _sess()
    past = datetime.now(UTC) - timedelta(minutes=10)
    d1 = _delivery(did=1, success=False)
    d1.next_retry_at = past
    d1.attempt_count = 1
    s.execute.return_value = _R(rows=[d1])
    count = await svc.retry_failed_deliveries(s)
    assert count == 1 and d1.attempt_count == 2

@pytest.mark.asyncio
async def test_retry_failed_deliveries_none():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[])
    assert await svc.retry_failed_deliveries(s) == 0

@pytest.mark.asyncio
async def test_retry_maxed_out(monkeypatch):
    svc, s = _svc(), _sess()
    past = datetime.now(UTC) - timedelta(minutes=10)
    d = _delivery(did=1, success=False)
    d.next_retry_at = past
    d.attempt_count = 2
    monkeypatch.setattr(svc, "_deliver_payload",
        AsyncMock(return_value={"status": 500, "success": False}))
    s.execute.return_value = _R(rows=[d])
    await svc.retry_failed_deliveries(s)
    assert d.attempt_count == 3 and d.next_retry_at is None


# ---- Usage Stats ----

@pytest.mark.asyncio
async def test_get_usage_stats():
    svc, s = _svc(), _sess()
    s.execute.side_effect = [_R(val=3), _R(val=5)]
    r = await svc.get_usage_stats(s, user_id=1)
    assert r["api_key_count"] == 3 and r["webhook_count"] == 5


# ---- Stubs and helpers ----

@pytest.mark.asyncio
async def test_deliver_payload_stub():
    r = await _svc()._deliver_payload(1, "test.event", {})
    assert r["success"] is True and r["status"] == 200

@pytest.mark.asyncio
async def test_get_user_key_success():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=_key(kid=3))
    assert (await svc._get_user_key(s, 3, 1)).id == 3

@pytest.mark.asyncio
async def test_get_user_key_not_found():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="API key not found"):
        await svc._get_user_key(s, 999, 1)

@pytest.mark.asyncio
async def test_get_user_webhook_success():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=_webhook(wid=5))
    assert (await svc._get_user_webhook(s, 5, 1)).id == 5

@pytest.mark.asyncio
async def test_get_user_webhook_not_found():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="Webhook endpoint not found"):
        await svc._get_user_webhook(s, 999, 1)
