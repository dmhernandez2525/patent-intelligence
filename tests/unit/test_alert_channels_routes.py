"""Unit tests for alert channel and schedule routes."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from src.api.routes import alert_channels as mod
from src.models.user import User

_SVC = "alert_notifier_service"
_ACT = "activity_service"


def _user() -> User:
    return User(
        id=1, email="t@example.com",
        hashed_password="".join(["h", "x"]),
        role="analyst", is_active=True)


def _req() -> Request:
    return Request({
        "type": "http", "method": "POST", "path": "/",
        "headers": [], "client": ("127.0.0.1", 7777)})


def _ch(cid=1, ctype="email"):
    return SimpleNamespace(
        id=cid, channel_type=ctype, name="ch",
        config={}, is_active=True, created_at=None)


def _sched(sid=1, chid=1):
    return SimpleNamespace(
        id=sid, channel_id=chid, frequency="daily",
        delivery_hour=9, delivery_day=1,
        alert_types=[], min_priority="low", is_active=True)


def _delivery(did=1, aid=1, chid=1):
    return SimpleNamespace(
        id=did, alert_id=aid, channel_id=chid,
        status="pending", attempt_count=0,
        last_error=None, sent_at=None)


def _patch(mp, method, val=None, exc=None):
    m = AsyncMock(side_effect=exc, return_value=val)
    mp.setattr(getattr(mod, _SVC), method, m)
    return m


def _patch_act(mp):
    mp.setattr(getattr(mod, _ACT), "log_event", AsyncMock())


def _session():
    s = AsyncMock()
    s.commit = AsyncMock()
    return s


async def _assert_http(coro, code):
    with pytest.raises(HTTPException) as ei:
        await coro
    assert ei.value.status_code == code


@pytest.mark.asyncio
async def test_list_channels(monkeypatch):
    _patch(monkeypatch, "list_channels", [_ch(1), _ch(2)])
    r = await mod.list_channels(
        current_user=_user(), session=_session())
    assert len(r.channels) == 2 and r.channels[0].id == 1


@pytest.mark.asyncio
async def test_create_channel_success(monkeypatch):
    _patch(monkeypatch, "create_channel", _ch(5))
    _patch_act(monkeypatch)
    pl = mod.ChannelCreateRequest(
        channel_type="email", name="Test",
        config={"email": "a@b.com"})
    r = await mod.create_channel(
        payload=pl, request=_req(),
        current_user=_user(), session=_session())
    assert r.id == 5


@pytest.mark.asyncio
async def test_create_channel_value_error(monkeypatch):
    _patch(monkeypatch, "create_channel", exc=ValueError("bad"))
    _patch_act(monkeypatch)
    pl = mod.ChannelCreateRequest(
        channel_type="email", name="Test")
    await _assert_http(mod.create_channel(
        pl, _req(), current_user=_user(), session=_session()),
        400)


@pytest.mark.asyncio
async def test_update_channel_success(monkeypatch):
    _patch(monkeypatch, "update_channel", _ch())
    _patch_act(monkeypatch)
    pl = mod.ChannelUpdateRequest(name="Up")
    r = await mod.update_channel(
        channel_id=1, payload=pl,
        current_user=_user(), session=_session())
    assert r.name == "ch"


@pytest.mark.asyncio
async def test_update_channel_no_updates(monkeypatch):
    pl = mod.ChannelUpdateRequest()
    await _assert_http(mod.update_channel(
        1, pl, current_user=_user(), session=_session()),
        400)


@pytest.mark.asyncio
async def test_update_channel_not_found(monkeypatch):
    _patch(monkeypatch, "update_channel",
        exc=ValueError("not found"))
    pl = mod.ChannelUpdateRequest(name="X")
    await _assert_http(mod.update_channel(
        99, pl, current_user=_user(), session=_session()),
        404)


@pytest.mark.asyncio
async def test_update_channel_forbidden(monkeypatch):
    _patch(monkeypatch, "update_channel",
        exc=PermissionError("denied"))
    pl = mod.ChannelUpdateRequest(name="X")
    await _assert_http(mod.update_channel(
        1, pl, current_user=_user(), session=_session()),
        403)


@pytest.mark.asyncio
async def test_delete_channel_success(monkeypatch):
    _patch(monkeypatch, "delete_channel", True)
    _patch_act(monkeypatch)
    r = await mod.delete_channel(
        channel_id=1,
        current_user=_user(), session=_session())
    assert r == {"success": True}


@pytest.mark.asyncio
async def test_delete_channel_errors(monkeypatch):
    s = _session()
    _patch(monkeypatch, "delete_channel", exc=ValueError("x"))
    await _assert_http(
        mod.delete_channel(1, current_user=_user(), session=s),
        404)
    _patch(monkeypatch, "delete_channel",
        exc=PermissionError("x"))
    await _assert_http(
        mod.delete_channel(1, current_user=_user(), session=s),
        403)


@pytest.mark.asyncio
async def test_list_schedules(monkeypatch):
    _patch(monkeypatch, "get_schedules",
        [_sched(1), _sched(2)])
    r = await mod.list_schedules(
        current_user=_user(), session=_session())
    assert len(r.schedules) == 2


@pytest.mark.asyncio
async def test_create_schedule_success(monkeypatch):
    _patch(monkeypatch, "create_schedule", _sched(3))
    _patch_act(monkeypatch)
    pl = mod.ScheduleCreateRequest(
        channel_id=1, frequency="daily")
    r = await mod.create_schedule(
        payload=pl, request=_req(),
        current_user=_user(), session=_session())
    assert r.id == 3


@pytest.mark.asyncio
async def test_create_schedule_value_error(monkeypatch):
    _patch(monkeypatch, "create_schedule",
        exc=ValueError("bad channel"))
    _patch_act(monkeypatch)
    pl = mod.ScheduleCreateRequest(
        channel_id=99, frequency="daily")
    await _assert_http(mod.create_schedule(
        pl, _req(), current_user=_user(), session=_session()),
        400)


@pytest.mark.asyncio
async def test_update_schedule_success(monkeypatch):
    _patch(monkeypatch, "update_schedule", _sched())
    _patch_act(monkeypatch)
    pl = mod.ScheduleUpdateRequest(frequency="weekly")
    r = await mod.update_schedule(
        schedule_id=1, payload=pl,
        current_user=_user(), session=_session())
    assert r.frequency == "daily"


@pytest.mark.asyncio
async def test_update_schedule_no_updates(monkeypatch):
    pl = mod.ScheduleUpdateRequest()
    await _assert_http(mod.update_schedule(
        1, pl, current_user=_user(), session=_session()),
        400)


@pytest.mark.asyncio
async def test_update_schedule_not_found(monkeypatch):
    _patch(monkeypatch, "update_schedule",
        exc=ValueError("not found"))
    pl = mod.ScheduleUpdateRequest(frequency="daily")
    await _assert_http(mod.update_schedule(
        99, pl, current_user=_user(), session=_session()),
        404)


@pytest.mark.asyncio
async def test_update_schedule_forbidden(monkeypatch):
    _patch(monkeypatch, "update_schedule",
        exc=PermissionError("denied"))
    pl = mod.ScheduleUpdateRequest(frequency="daily")
    await _assert_http(mod.update_schedule(
        1, pl, current_user=_user(), session=_session()),
        403)


@pytest.mark.asyncio
async def test_delete_schedule_success(monkeypatch):
    _patch(monkeypatch, "delete_schedule", True)
    _patch_act(monkeypatch)
    r = await mod.delete_schedule(
        schedule_id=1,
        current_user=_user(), session=_session())
    assert r == {"success": True}


@pytest.mark.asyncio
async def test_delete_schedule_errors(monkeypatch):
    s = _session()
    _patch(monkeypatch, "delete_schedule",
        exc=ValueError("x"))
    await _assert_http(mod.delete_schedule(
        1, current_user=_user(), session=s), 404)
    _patch(monkeypatch, "delete_schedule",
        exc=PermissionError("x"))
    await _assert_http(mod.delete_schedule(
        1, current_user=_user(), session=s), 403)


@pytest.mark.asyncio
async def test_dispatch_alert_success(monkeypatch):
    ds = [_delivery(1, 10, 1), _delivery(2, 10, 2)]
    _patch(monkeypatch, "dispatch_alert", ds)
    _patch_act(monkeypatch)
    r = await mod.dispatch_alert(
        alert_id=10,
        current_user=_user(), session=_session())
    assert r.total_dispatched == 2 and len(r.deliveries) == 2


@pytest.mark.asyncio
async def test_dispatch_alert_errors(monkeypatch):
    s = _session()
    _patch(monkeypatch, "dispatch_alert",
        exc=ValueError("alert not found"))
    await _assert_http(mod.dispatch_alert(
        99, current_user=_user(), session=s), 404)
    _patch(monkeypatch, "dispatch_alert",
        exc=PermissionError("x"))
    await _assert_http(mod.dispatch_alert(
        1, current_user=_user(), session=s), 403)


@pytest.mark.asyncio
async def test_process_deliveries(monkeypatch):
    _patch(monkeypatch, "process_pending_deliveries", 5)
    r = await mod.process_deliveries(session=_session())
    assert r == {"processed": 5}
