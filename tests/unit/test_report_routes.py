"""Unit tests for report API routes."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from src.api.routes import reports as mod
from src.models.user import User

_SVC = "report_service"
_ACT = "activity_service"


def _user() -> User:
    return User(id=1, email="t@example.com",
                hashed_password="".join(["h", "x"]),
                role="analyst", is_active=True)


def _req() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/",
                    "headers": [], "client": ("127.0.0.1", 7777)})


def _report(rid=1, uid=1, pid=None):
    return SimpleNamespace(
        id=rid, user_id=uid, project_id=pid, title="Test Report",
        report_type="landscape", output_format="pdf", status="completed",
        config={}, file_size=1024, page_count=5,
        error_message=None, generated_at=None, created_at=None)


def _template(tid=1):
    return SimpleNamespace(
        id=tid, name="Standard", report_type="landscape",
        description="Default template", template_config={},
        is_default=True, is_system=True)


def _schedule(sid=1, pid=None):
    return SimpleNamespace(
        id=sid, report_type="landscape", output_format="pdf",
        project_id=pid, config={}, frequency="weekly",
        next_run_at=None, is_active=True)


def _patch(mp, method, val=None, exc=None):
    m = AsyncMock(side_effect=exc, return_value=val)
    mp.setattr(getattr(mod, _SVC), method, m)
    return m


def _patch_act(mp):
    m = AsyncMock()
    mp.setattr(getattr(mod, _ACT), "log_event", m)
    return m


def _session():
    s = AsyncMock()
    s.commit = AsyncMock()
    return s


async def _assert_http(coro, code):
    with pytest.raises(HTTPException) as ei:
        await coro
    assert ei.value.status_code == code


@pytest.mark.asyncio
async def test_list_reports(monkeypatch):
    _patch(monkeypatch, "list_reports", [_report(1), _report(2)])
    r = await mod.list_reports(project_id=None, status_filter=None,
                               current_user=_user(), session=_session())
    assert r.total == 2
    assert r.reports[0].id == 1 and r.reports[1].id == 2


@pytest.mark.asyncio
async def test_list_reports_with_filters(monkeypatch):
    mock = _patch(monkeypatch, "list_reports", [_report(3, pid=1)])
    r = await mod.list_reports(project_id=1, status_filter="completed",
                               current_user=_user(), session=_session())
    assert r.total == 1 and r.reports[0].id == 3
    kw = mock.call_args.kwargs
    assert kw["project_id"] == 1 and kw["status"] == "completed"


@pytest.mark.asyncio
async def test_list_reports_empty(monkeypatch):
    _patch(monkeypatch, "list_reports", [])
    r = await mod.list_reports(project_id=None, status_filter=None,
                               current_user=_user(), session=_session())
    assert r.total == 0 and r.reports == []


@pytest.mark.asyncio
async def test_create_report(monkeypatch):
    _patch(monkeypatch, "create_report", _report(5))
    _patch_act(monkeypatch)
    pl = mod.ReportCreateRequest(title="New Report", report_type="landscape")
    r = await mod.create_report(payload=pl, request=_req(),
                                current_user=_user(), session=_session())
    assert r.id == 5 and r.title == "Test Report"


@pytest.mark.asyncio
async def test_create_report_logs_activity(monkeypatch):
    _patch(monkeypatch, "create_report", _report(6))
    act = _patch_act(monkeypatch)
    pl = mod.ReportCreateRequest(title="Logged", report_type="competitive")
    await mod.create_report(payload=pl, request=_req(),
                            current_user=_user(), session=_session())
    act.assert_called_once()
    kw = act.call_args.kwargs
    assert kw["event_type"] == "report.created"
    assert kw["resource_type"] == "report"


@pytest.mark.asyncio
async def test_get_report(monkeypatch):
    _patch(monkeypatch, "get_report", _report(1))
    r = await mod.get_report(report_id=1, current_user=_user(),
                             session=_session())
    assert r.id == 1 and r.report_type == "landscape"


@pytest.mark.asyncio
async def test_get_report_not_found(monkeypatch):
    _patch(monkeypatch, "get_report", exc=ValueError("not found"))
    await _assert_http(
        mod.get_report(999, current_user=_user(), session=_session()), 404)


@pytest.mark.asyncio
async def test_generate_report(monkeypatch):
    _patch(monkeypatch, "generate_report", _report(1))
    _patch_act(monkeypatch)
    r = await mod.generate_report(report_id=1, request=_req(),
                                  current_user=_user(), session=_session())
    assert r.id == 1 and r.status == "completed"


@pytest.mark.asyncio
async def test_generate_report_not_found(monkeypatch):
    _patch(monkeypatch, "generate_report", exc=ValueError("not found"))
    _patch_act(monkeypatch)
    await _assert_http(
        mod.generate_report(999, _req(),
                            current_user=_user(), session=_session()), 404)


@pytest.mark.asyncio
async def test_generate_report_logs_activity(monkeypatch):
    _patch(monkeypatch, "generate_report", _report(7))
    act = _patch_act(monkeypatch)
    await mod.generate_report(report_id=7, request=_req(),
                              current_user=_user(), session=_session())
    act.assert_called_once()
    kw = act.call_args.kwargs
    assert kw["event_type"] == "report.generated"
    assert kw["resource_id"] == "7"


@pytest.mark.asyncio
async def test_delete_report(monkeypatch):
    _patch(monkeypatch, "delete_report", True)
    _patch_act(monkeypatch)
    r = await mod.delete_report(report_id=1, request=_req(),
                                current_user=_user(), session=_session())
    assert r == {"success": True}


@pytest.mark.asyncio
async def test_delete_report_not_found(monkeypatch):
    _patch(monkeypatch, "delete_report", exc=ValueError("not found"))
    _patch_act(monkeypatch)
    await _assert_http(
        mod.delete_report(999, _req(),
                          current_user=_user(), session=_session()), 404)


@pytest.mark.asyncio
async def test_delete_report_logs_activity(monkeypatch):
    _patch(monkeypatch, "delete_report", True)
    act = _patch_act(monkeypatch)
    await mod.delete_report(report_id=3, request=_req(),
                            current_user=_user(), session=_session())
    act.assert_called_once()
    kw = act.call_args.kwargs
    assert kw["event_type"] == "report.deleted"
    assert kw["resource_id"] == "3"


@pytest.mark.asyncio
async def test_list_templates(monkeypatch):
    _patch(monkeypatch, "list_templates", [_template(1), _template(2)])
    r = await mod.list_templates(report_type=None,
                                 current_user=_user(), session=_session())
    assert len(r.templates) == 2 and r.templates[0].name == "Standard"


@pytest.mark.asyncio
async def test_list_templates_by_type(monkeypatch):
    mock = _patch(monkeypatch, "list_templates", [_template(3)])
    r = await mod.list_templates(report_type="landscape",
                                 current_user=_user(), session=_session())
    assert len(r.templates) == 1
    assert mock.call_args.kwargs["report_type"] == "landscape"


@pytest.mark.asyncio
async def test_list_templates_empty(monkeypatch):
    _patch(monkeypatch, "list_templates", [])
    r = await mod.list_templates(report_type="custom",
                                 current_user=_user(), session=_session())
    assert r.templates == []


@pytest.mark.asyncio
async def test_create_schedule(monkeypatch):
    _patch(monkeypatch, "create_schedule", _schedule(4))
    _patch_act(monkeypatch)
    pl = mod.ScheduleCreateRequest(report_type="landscape", frequency="daily")
    r = await mod.create_schedule(payload=pl, request=_req(),
                                  current_user=_user(), session=_session())
    assert r.id == 4 and r.frequency == "weekly"


@pytest.mark.asyncio
async def test_create_schedule_logs_activity(monkeypatch):
    _patch(monkeypatch, "create_schedule", _schedule(5))
    act = _patch_act(monkeypatch)
    pl = mod.ScheduleCreateRequest(report_type="competitive",
                                   frequency="monthly")
    await mod.create_schedule(payload=pl, request=_req(),
                              current_user=_user(), session=_session())
    act.assert_called_once()
    kw = act.call_args.kwargs
    assert kw["event_type"] == "report.schedule.created"
    assert kw["resource_type"] == "report_schedule"


@pytest.mark.asyncio
async def test_list_schedules(monkeypatch):
    _patch(monkeypatch, "list_schedules", [_schedule(1), _schedule(2)])
    r = await mod.list_schedules(current_user=_user(), session=_session())
    assert len(r.schedules) == 2 and r.schedules[0].id == 1


@pytest.mark.asyncio
async def test_list_schedules_empty(monkeypatch):
    _patch(monkeypatch, "list_schedules", [])
    r = await mod.list_schedules(current_user=_user(), session=_session())
    assert r.schedules == []


@pytest.mark.asyncio
async def test_delete_schedule(monkeypatch):
    _patch(monkeypatch, "delete_schedule", True)
    _patch_act(monkeypatch)
    r = await mod.delete_schedule(schedule_id=1, request=_req(),
                                  current_user=_user(), session=_session())
    assert r == {"success": True}


@pytest.mark.asyncio
async def test_delete_schedule_not_found(monkeypatch):
    _patch(monkeypatch, "delete_schedule", exc=ValueError("not found"))
    _patch_act(monkeypatch)
    await _assert_http(
        mod.delete_schedule(999, _req(),
                            current_user=_user(), session=_session()), 404)


@pytest.mark.asyncio
async def test_delete_schedule_logs_activity(monkeypatch):
    _patch(monkeypatch, "delete_schedule", True)
    act = _patch_act(monkeypatch)
    await mod.delete_schedule(schedule_id=8, request=_req(),
                              current_user=_user(), session=_session())
    act.assert_called_once()
    kw = act.call_args.kwargs
    assert kw["event_type"] == "report.schedule.deleted"
    assert kw["resource_id"] == "8"
