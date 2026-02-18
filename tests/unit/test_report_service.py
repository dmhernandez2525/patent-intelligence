"""Tests for the ReportService."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.report import ReportSchedule, ReportTemplate, ResearchReport
from src.services.report_service import ReportService


class _R:
    def __init__(self, val=None, rows=None):
        self._v, self._rows = val, rows or []
    def scalar_one_or_none(self): return self._v
    def scalars(self): return SimpleNamespace(all=lambda: self._rows)

def _svc(): return ReportService()
def _sess():
    s = AsyncMock()
    s.add = MagicMock()
    s.flush, s.refresh, s.delete = AsyncMock(), AsyncMock(), AsyncMock()
    return s

def _report(rid=1, uid=1, pid=None, rtype="landscape",
            fmt="pdf", status="pending"):
    return ResearchReport(
        id=rid, user_id=uid, project_id=pid, title="Test Report",
        report_type=rtype, output_format=fmt, status=status, config={})

def _template(tid=1, rtype="landscape"):
    return ReportTemplate(
        id=tid, name=f"tmpl-{tid}", report_type=rtype,
        description="desc", template_config={},
        is_default=False, is_system=True)

def _schedule(sid=1, uid=1, freq="weekly"):
    return ReportSchedule(
        id=sid, user_id=uid, report_type="landscape",
        output_format="pdf", project_id=None, config={},
        frequency=freq, is_active=True,
        next_run_at=datetime.now(UTC))

# -- Report CRUD -----------------------------------------------------------
@pytest.mark.asyncio
async def test_list_reports_returns_list():
    svc, s = _svc(), _sess()
    rpts = [_report(1), _report(2)]
    s.execute.return_value = _R(rows=rpts)
    r = await svc.list_reports(s, user_id=1)
    assert r == rpts and len(r) == 2

@pytest.mark.asyncio
async def test_list_reports_empty():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[])
    assert await svc.list_reports(s, user_id=99) == []

@pytest.mark.asyncio
async def test_list_reports_with_project_filter():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_report(1, pid=5)])
    r = await svc.list_reports(s, user_id=1, project_id=5)
    assert len(r) == 1
    s.execute.assert_awaited_once()

@pytest.mark.asyncio
async def test_list_reports_with_status_filter():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_report(1, status="completed")])
    assert len(await svc.list_reports(s, user_id=1, status="completed")) == 1

@pytest.mark.asyncio
async def test_create_report_success():
    svc, s = _svc(), _sess()
    r = await svc.create_report(
        s, user_id=1, title="Landscape Q4",
        report_type="landscape", output_format="excel",
        project_id=10, config={"scope": "wide"})
    s.add.assert_called_once()
    s.flush.assert_awaited_once()
    assert r.report_type == "landscape" and r.output_format == "excel"
    assert r.project_id == 10 and r.config == {"scope": "wide"}

@pytest.mark.asyncio
async def test_create_report_default_format():
    svc, s = _svc(), _sess()
    r = await svc.create_report(s, user_id=1, title="Quick", report_type="custom")
    assert r.output_format == "pdf" and r.config == {} and r.status == "pending"

@pytest.mark.asyncio
async def test_get_report_success(monkeypatch):
    svc, s = _svc(), _sess()
    rpt = _report(5, uid=2)
    monkeypatch.setattr(svc, "_get_user_report", AsyncMock(return_value=rpt))
    assert (await svc.get_report(s, 5, user_id=2)) is rpt

@pytest.mark.asyncio
async def test_get_report_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_report",
        AsyncMock(side_effect=ValueError("Report not found")))
    with pytest.raises(ValueError, match="not found"):
        await svc.get_report(s, 999, user_id=1)

@pytest.mark.asyncio
async def test_delete_report_success(monkeypatch):
    svc, s = _svc(), _sess()
    rpt = _report(3)
    monkeypatch.setattr(svc, "_get_user_report", AsyncMock(return_value=rpt))
    assert await svc.delete_report(s, 3, user_id=1) is True
    s.delete.assert_awaited_once_with(rpt)

@pytest.mark.asyncio
async def test_delete_report_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_report",
        AsyncMock(side_effect=ValueError("Report not found")))
    with pytest.raises(ValueError, match="not found"):
        await svc.delete_report(s, 999, user_id=1)

# -- Generation -------------------------------------------------------------
@pytest.mark.asyncio
async def test_generate_report_landscape(monkeypatch):
    svc, s = _svc(), _sess()
    rpt = _report(1, rtype="landscape")
    monkeypatch.setattr(svc, "_get_user_report", AsyncMock(return_value=rpt))
    stub = {"file_path": "/f.pdf", "file_size": 100, "page_count": 5}
    monkeypatch.setattr(svc, "_generate_landscape", AsyncMock(return_value=stub))
    r = await svc.generate_report(s, 1, user_id=1)
    assert r.status == "completed"
    assert r.file_path == "/f.pdf" and r.page_count == 5

@pytest.mark.asyncio
async def test_generate_report_custom_fallback(monkeypatch):
    svc, s = _svc(), _sess()
    rpt = _report(1, rtype="unknown_type")
    monkeypatch.setattr(svc, "_get_user_report", AsyncMock(return_value=rpt))
    stub = {"file_path": "/c.pdf", "file_size": 50, "page_count": 2}
    monkeypatch.setattr(svc, "_generate_custom", AsyncMock(return_value=stub))
    r = await svc.generate_report(s, 1, user_id=1)
    assert r.status == "completed" and r.file_path == "/c.pdf"

@pytest.mark.asyncio
async def test_generate_report_failure(monkeypatch):
    svc, s = _svc(), _sess()
    rpt = _report(1, rtype="landscape")
    monkeypatch.setattr(svc, "_get_user_report", AsyncMock(return_value=rpt))
    monkeypatch.setattr(svc, "_generate_landscape",
        AsyncMock(side_effect=RuntimeError("gen boom")))
    r = await svc.generate_report(s, 1, user_id=1)
    assert r.status == "failed" and r.error_message == "gen boom"

@pytest.mark.asyncio
async def test_generate_landscape_stub():
    r = await _svc()._generate_landscape({}, 1)
    assert r["file_path"].endswith("landscape.pdf")
    assert r["file_size"] == 0 and r["page_count"] == 0

@pytest.mark.asyncio
async def test_generate_competitive_stub():
    r = await _svc()._generate_competitive({}, 2)
    assert "competitive" in r["file_path"]

@pytest.mark.asyncio
async def test_generate_expiration_stub():
    r = await _svc()._generate_expiration({}, 3)
    assert "expiration" in r["file_path"]

@pytest.mark.asyncio
async def test_generate_patent_analysis_stub():
    r = await _svc()._generate_patent_analysis({}, 4)
    assert "patent_analysis" in r["file_path"]

@pytest.mark.asyncio
async def test_generate_custom_stub():
    r = await _svc()._generate_custom({}, None)
    assert "custom" in r["file_path"]

# -- Templates ---------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_templates_all():
    svc, s = _svc(), _sess()
    ts = [_template(1), _template(2)]
    s.execute.return_value = _R(rows=ts)
    assert await svc.list_templates(s) == ts

@pytest.mark.asyncio
async def test_list_templates_by_type():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_template(1, rtype="competitive")])
    r = await svc.list_templates(s, report_type="competitive")
    assert len(r) == 1
    s.execute.assert_awaited_once()

@pytest.mark.asyncio
async def test_get_template_success():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=_template(7))
    assert (await svc.get_template(s, 7)).id == 7

@pytest.mark.asyncio
async def test_get_template_not_found():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="template not found"):
        await svc.get_template(s, 999)

# -- Schedules ---------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_schedule_success():
    svc, s = _svc(), _sess()
    r = await svc.create_schedule(
        s, user_id=1, report_type="landscape",
        output_format="excel", project_id=5,
        config={"x": 1}, frequency="daily")
    s.add.assert_called_once()
    s.flush.assert_awaited_once()
    assert r.frequency == "daily" and r.output_format == "excel"
    assert r.is_active is True

@pytest.mark.asyncio
async def test_list_schedules_returns_list():
    svc, s = _svc(), _sess()
    ss = [_schedule(1), _schedule(2)]
    s.execute.return_value = _R(rows=ss)
    r = await svc.list_schedules(s, user_id=1)
    assert r == ss and len(r) == 2

@pytest.mark.asyncio
async def test_delete_schedule_success(monkeypatch):
    svc, s = _svc(), _sess()
    sch = _schedule(3)
    monkeypatch.setattr(svc, "_get_user_schedule", AsyncMock(return_value=sch))
    assert await svc.delete_schedule(s, 3, user_id=1) is True
    s.delete.assert_awaited_once_with(sch)

@pytest.mark.asyncio
async def test_delete_schedule_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_schedule",
        AsyncMock(side_effect=ValueError("schedule not found")))
    with pytest.raises(ValueError, match="schedule not found"):
        await svc.delete_schedule(s, 999, user_id=1)

# -- Internal helpers --------------------------------------------------------
@pytest.mark.asyncio
async def test_get_user_report_success():
    svc, s = _svc(), _sess()
    rpt = _report(4, uid=2)
    s.execute.return_value = _R(val=rpt)
    assert (await svc._get_user_report(s, 4, 2)) is rpt

@pytest.mark.asyncio
async def test_get_user_report_not_found():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="Report not found"):
        await svc._get_user_report(s, 999, 1)

@pytest.mark.asyncio
async def test_get_user_schedule_success():
    svc, s = _svc(), _sess()
    sch = _schedule(6, uid=3)
    s.execute.return_value = _R(val=sch)
    assert (await svc._get_user_schedule(s, 6, 3)) is sch

@pytest.mark.asyncio
async def test_get_user_schedule_not_found():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="schedule not found"):
        await svc._get_user_schedule(s, 999, 1)

@pytest.mark.parametrize("freq,days", [("daily", 1), ("weekly", 7), ("monthly", 30)])
def test_advance_next_run(freq, days):
    sch = _schedule(freq=freq)
    before = datetime.now(UTC)
    _svc()._advance_next_run(sch)
    assert sch.next_run_at >= before + timedelta(days=days)

@pytest.mark.asyncio
async def test_process_due_schedules():
    svc, s = _svc(), _sess()
    sch = _schedule(1, uid=1, freq="daily")
    sch.next_run_at = datetime.now(UTC) - timedelta(hours=1)
    s.execute.return_value = _R(rows=[sch])
    count = await svc.process_due_schedules(s)
    assert count == 1
    s.add.assert_called_once()
    s.flush.assert_awaited_once()
    assert sch.next_run_at > datetime.now(UTC)
