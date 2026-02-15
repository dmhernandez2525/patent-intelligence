"""Tests for the AlertNotifierService."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.alert_channel import (
    AlertDelivery,
    AlertSchedule,
    NotificationChannel,
)
from src.services.alert_notifier_service import (
    MAX_RETRIES,
    AlertNotifierService,
)


class _R:
    def __init__(self, val=None, rows=None):
        self._v, self._rows = val, rows or []
    def scalar_one_or_none(self): return self._v
    def scalars(self): return SimpleNamespace(all=lambda: self._rows)

def _svc(): return AlertNotifierService()
def _alert(aid=1): return SimpleNamespace(id=aid)

def _channel(cid=1, uid=1, active=True, ctype="email"):
    return NotificationChannel(
        id=cid, user_id=uid, channel_type=ctype,
        name="ch", config={}, is_active=active)

def _schedule(sid=1, uid=1, chid=1):
    return AlertSchedule(
        id=sid, user_id=uid, channel_id=chid,
        frequency="daily", delivery_hour=9, delivery_day=1,
        alert_types=[], min_priority="low", is_active=True)

def _delivery(did=1, aid=1, chid=1, attempts=0):
    return AlertDelivery(
        id=did, alert_id=aid, channel_id=chid,
        status="pending", attempt_count=attempts,
        max_retries=MAX_RETRIES, last_error=None,
        next_retry_at=None, sent_at=None)

def _sess():
    s = AsyncMock()
    s.add = MagicMock()
    s.flush, s.refresh, s.delete, s.get = (
        AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock())
    return s

@pytest.mark.asyncio
async def test_list_channels_returns_list():
    svc, s = _svc(), _sess()
    chs = [_channel(1), _channel(2)]
    s.execute.return_value = _R(rows=chs)
    r = await svc.list_channels(s, user_id=1)
    assert r == chs and len(r) == 2

@pytest.mark.asyncio
async def test_list_channels_empty():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[])
    assert await svc.list_channels(s, user_id=99) == []

@pytest.mark.asyncio
async def test_create_channel_success():
    svc, s = _svc(), _sess()
    r = await svc.create_channel(
        s, user_id=1, channel_type="email",
        name="My Email", config={"email": "a@b.com"})
    s.add.assert_called_once()
    s.flush.assert_awaited_once()
    assert r.channel_type == "email"
    assert r.name == "My Email" and r.is_active is True

@pytest.mark.asyncio
async def test_create_channel_default_config():
    svc, s = _svc(), _sess()
    r = await svc.create_channel(
        s, user_id=1, channel_type="slack", name="S")
    assert r.config == {}

@pytest.mark.asyncio
async def test_update_channel_success(monkeypatch):
    svc, s = _svc(), _sess()
    ch = _channel()
    monkeypatch.setattr(svc, "_get_user_channel",
        AsyncMock(return_value=ch))
    r = await svc.update_channel(
        s, channel_id=1, user_id=1,
        name="Up", config={"x": 1}, is_active=False)
    assert r.name == "Up" and r.is_active is False
    assert r.config == {"x": 1}

@pytest.mark.asyncio
async def test_update_channel_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_channel",
        AsyncMock(side_effect=ValueError("not found")))
    with pytest.raises(ValueError, match="not found"):
        await svc.update_channel(s, 999, user_id=1)

@pytest.mark.asyncio
async def test_delete_channel_success(monkeypatch):
    svc, s = _svc(), _sess()
    ch = _channel()
    monkeypatch.setattr(svc, "_get_user_channel",
        AsyncMock(return_value=ch))
    assert await svc.delete_channel(s, 1, user_id=1) is True
    s.delete.assert_awaited_once_with(ch)

@pytest.mark.asyncio
async def test_delete_channel_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_channel",
        AsyncMock(side_effect=ValueError("not found")))
    with pytest.raises(ValueError, match="not found"):
        await svc.delete_channel(s, 999, user_id=1)

@pytest.mark.asyncio
async def test_get_schedules_returns_list():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(
        rows=[_schedule(1), _schedule(2)])
    assert len(await svc.get_schedules(s, user_id=1)) == 2

@pytest.mark.asyncio
async def test_create_schedule_success(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_channel",
        AsyncMock(return_value=_channel()))
    r = await svc.create_schedule(
        s, user_id=1, channel_id=1, frequency="daily",
        delivery_hour=10, delivery_day=3,
        alert_types=["new"], min_priority="high")
    s.add.assert_called_once()
    assert r.frequency == "daily" and r.min_priority == "high"

@pytest.mark.asyncio
async def test_create_schedule_channel_not_owned(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_channel",
        AsyncMock(side_effect=ValueError("not found")))
    with pytest.raises(ValueError, match="not found"):
        await svc.create_schedule(s, user_id=1, channel_id=99)

@pytest.mark.asyncio
async def test_update_schedule_success(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_schedule",
        AsyncMock(return_value=_schedule()))
    r = await svc.update_schedule(
        s, schedule_id=1, user_id=1, frequency="weekly",
        delivery_hour=14, delivery_day=5,
        alert_types=["expiry"], min_priority="medium",
        is_active=False)
    assert r.frequency == "weekly" and r.delivery_hour == 14
    assert r.delivery_day == 5 and r.is_active is False

@pytest.mark.asyncio
async def test_update_schedule_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_schedule",
        AsyncMock(side_effect=ValueError("not found")))
    with pytest.raises(ValueError, match="not found"):
        await svc.update_schedule(s, 999, user_id=1)

@pytest.mark.asyncio
async def test_delete_schedule_success(monkeypatch):
    svc, s = _svc(), _sess()
    sched = _schedule()
    monkeypatch.setattr(svc, "_get_user_schedule",
        AsyncMock(return_value=sched))
    assert await svc.delete_schedule(s, 1, user_id=1) is True
    s.delete.assert_awaited_once_with(sched)

@pytest.mark.asyncio
async def test_delete_schedule_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_schedule",
        AsyncMock(side_effect=ValueError("not found")))
    with pytest.raises(ValueError, match="not found"):
        await svc.delete_schedule(s, 999, user_id=1)

@pytest.mark.asyncio
async def test_dispatch_alert_creates_deliveries(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_alert",
        AsyncMock(return_value=_alert(10)))
    s.execute.return_value = _R(
        rows=[_channel(1), _channel(2)])
    r = await svc.dispatch_alert(s, alert_id=10, user_id=1)
    assert len(r) == 2 and s.add.call_count == 2

@pytest.mark.asyncio
async def test_dispatch_alert_no_active_channels(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_alert",
        AsyncMock(return_value=_alert()))
    s.execute.return_value = _R(rows=[])
    assert await svc.dispatch_alert(s, 1, user_id=1) == []
    s.add.assert_not_called()

@pytest.mark.asyncio
async def test_process_pending_marks_delivered(monkeypatch):
    svc, s = _svc(), _sess()
    d = _delivery(did=1, aid=1, chid=1)
    s.execute.return_value = _R(rows=[d])
    s.get = AsyncMock(side_effect=[_channel(1), _alert(1)])
    monkeypatch.setattr(svc, "_send_to_channel",
        AsyncMock(return_value=True))
    assert await svc.process_pending_deliveries(s) == 1
    assert d.status == "sent" and d.sent_at is not None

@pytest.mark.asyncio
async def test_process_pending_inactive_channel():
    svc, s = _svc(), _sess()
    d = _delivery(did=1, aid=1, chid=1, attempts=MAX_RETRIES)
    d.attempt_count = MAX_RETRIES
    s.execute.return_value = _R(rows=[d])
    s.get = AsyncMock(return_value=None)
    assert await svc.process_pending_deliveries(s) == 1
    assert d.status == "failed"
    assert d.last_error == "Channel inactive or deleted"

@pytest.mark.asyncio
async def test_send_email_returns_true():
    assert await _svc()._send_email(
        {"email": "a@b.com"}, _alert()) is True

@pytest.mark.asyncio
async def test_send_webhook_returns_true():
    assert await _svc()._send_webhook(
        {"url": "http://x"}, _alert()) is True

@pytest.mark.asyncio
async def test_send_slack_returns_true():
    assert await _svc()._send_slack(
        {"channel": "#a"}, _alert()) is True

@pytest.mark.asyncio
async def test_send_teams_returns_true():
    assert await _svc()._send_teams(
        {"webhook_url": "http://x"}, _alert()) is True

def test_mark_delivered_sets_sent():
    d = _delivery()
    _svc()._mark_delivered(d)
    assert d.status == "sent"
    assert d.sent_at is not None and d.last_error is None

def test_mark_failed_retrying():
    d = _delivery(attempts=1)
    d.attempt_count = 1
    _svc()._mark_failed(d, "error msg")
    assert d.status == "retrying" and d.last_error == "error msg"
    assert d.next_retry_at is not None

def test_mark_failed_exceeds_retries():
    d = _delivery(attempts=MAX_RETRIES)
    d.attempt_count = MAX_RETRIES
    _svc()._mark_failed(d, "final failure")
    assert d.status == "failed"
    assert d.last_error == "final failure"

@pytest.mark.asyncio
async def test_get_user_channel_success():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=_channel(1, uid=5))
    assert (await svc._get_user_channel(s, 1, 5)).id == 1

@pytest.mark.asyncio
async def test_get_user_channel_not_found():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="not found"):
        await svc._get_user_channel(s, 999, 1)

@pytest.mark.asyncio
async def test_get_user_channel_wrong_user():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="not found"):
        await svc._get_user_channel(s, 1, 999)

@pytest.mark.asyncio
async def test_send_to_channel_unknown_type():
    assert await _svc()._send_to_channel(
        _channel(ctype="sms"), _alert()) is False
