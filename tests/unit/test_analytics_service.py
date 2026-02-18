"""Tests for the AnalyticsService."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.analytics import AnalyticsSchedule, CustomMetric, SavedQuery
from src.services.analytics_service import AnalyticsService


class _R:
    def __init__(self, val=None, rows=None):
        self._v, self._rows = val, rows or []
    def scalar_one_or_none(self): return self._v
    def scalars(self): return SimpleNamespace(all=lambda: self._rows)

def _svc(): return AnalyticsService()

def _sess():
    s = AsyncMock()
    s.add = MagicMock()
    s.flush, s.refresh, s.delete = AsyncMock(), AsyncMock(), AsyncMock()
    return s

def _query(qid=1, uid=1, name="Test Query", status="saved"):
    return SavedQuery(
        id=qid, user_id=uid, name=name, description=None,
        query_config={}, filters={}, status=status,
        is_public=False, last_run_at=None, run_count=0)

def _metric(mid=1, uid=1, name="Test Metric", mtype="count"):
    return CustomMetric(
        id=mid, user_id=uid, name=name, metric_type=mtype,
        definition={}, current_value=None, last_computed_at=None)

def _schedule(sid=1, uid=1, freq="daily", active=True):
    return AnalyticsSchedule(
        id=sid, user_id=uid, query_id=None, metric_id=None,
        frequency=freq, is_active=active, next_run_at=None)


# ---- Saved Queries ----

@pytest.mark.asyncio
async def test_list_queries():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_query(1), _query(2)])
    r = await svc.list_queries(s, user_id=1)
    assert len(r) == 2

@pytest.mark.asyncio
async def test_list_queries_with_status():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_query(status="draft")])
    r = await svc.list_queries(s, user_id=1, status="draft")
    assert len(r) == 1

@pytest.mark.asyncio
async def test_list_queries_public_only():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[])
    r = await svc.list_queries(s, user_id=1, public_only=True)
    assert len(r) == 0

@pytest.mark.asyncio
async def test_create_query():
    svc, s = _svc(), _sess()
    r = await svc.create_query(s, user_id=1, name="New Query")
    s.add.assert_called_once()
    assert r.name == "New Query" and r.status == "saved"

@pytest.mark.asyncio
async def test_create_query_with_config():
    svc, s = _svc(), _sess()
    cfg = {"type": "patent_search", "fields": ["title"]}
    r = await svc.create_query(
        s, user_id=1, name="Q", query_config=cfg, is_public=True)
    assert r.query_config == cfg and r.is_public is True

@pytest.mark.asyncio
async def test_update_query(monkeypatch):
    svc, s = _svc(), _sess()
    q = _query()
    monkeypatch.setattr(svc, "_get_user_query", AsyncMock(return_value=q))
    r = await svc.update_query(s, 1, 1, name="Updated", status="archived")
    assert r.name == "Updated" and r.status == "archived"

@pytest.mark.asyncio
async def test_update_query_config_and_filters(monkeypatch):
    svc, s = _svc(), _sess()
    q = _query()
    monkeypatch.setattr(svc, "_get_user_query", AsyncMock(return_value=q))
    r = await svc.update_query(
        s, 1, 1, query_config={"new": True}, filters={"cpc": "H01L"})
    assert r.query_config == {"new": True} and r.filters == {"cpc": "H01L"}

@pytest.mark.asyncio
async def test_update_query_public(monkeypatch):
    svc, s = _svc(), _sess()
    q = _query()
    monkeypatch.setattr(svc, "_get_user_query", AsyncMock(return_value=q))
    r = await svc.update_query(s, 1, 1, is_public=True, description="Desc")
    assert r.is_public is True and r.description == "Desc"

@pytest.mark.asyncio
async def test_update_query_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_query",
        AsyncMock(side_effect=ValueError("not found")))
    with pytest.raises(ValueError, match="not found"):
        await svc.update_query(s, 999, 1)

@pytest.mark.asyncio
async def test_delete_query(monkeypatch):
    svc, s = _svc(), _sess()
    q = _query()
    monkeypatch.setattr(svc, "_get_user_query", AsyncMock(return_value=q))
    assert await svc.delete_query(s, 1, 1) is True
    s.delete.assert_awaited_once_with(q)

@pytest.mark.asyncio
async def test_delete_query_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_query",
        AsyncMock(side_effect=ValueError("not found")))
    with pytest.raises(ValueError):
        await svc.delete_query(s, 999, 1)

@pytest.mark.asyncio
async def test_run_query(monkeypatch):
    svc, s = _svc(), _sess()
    q = _query()
    monkeypatch.setattr(svc, "_get_user_query", AsyncMock(return_value=q))
    r = await svc.run_query(s, 1, 1)
    assert r.run_count == 1 and r.last_run_at is not None
    assert "last_result" in r.query_config

@pytest.mark.asyncio
async def test_run_query_increments_count(monkeypatch):
    svc, s = _svc(), _sess()
    q = _query()
    q.run_count = 5
    monkeypatch.setattr(svc, "_get_user_query", AsyncMock(return_value=q))
    r = await svc.run_query(s, 1, 1)
    assert r.run_count == 6


# ---- Custom Metrics ----

@pytest.mark.asyncio
async def test_list_metrics():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_metric(1), _metric(2)])
    r = await svc.list_metrics(s, user_id=1)
    assert len(r) == 2

@pytest.mark.asyncio
async def test_list_metrics_by_type():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_metric(mtype="trend")])
    r = await svc.list_metrics(s, user_id=1, metric_type="trend")
    assert len(r) == 1

@pytest.mark.asyncio
async def test_create_metric():
    svc, s = _svc(), _sess()
    r = await svc.create_metric(s, user_id=1, name="Pat Count", metric_type="count")
    s.add.assert_called_once()
    assert r.name == "Pat Count" and r.metric_type == "count"

@pytest.mark.asyncio
async def test_create_metric_with_definition():
    svc, s = _svc(), _sess()
    defn = {"source": "patents", "field": "filing_date"}
    r = await svc.create_metric(
        s, user_id=1, name="M", metric_type="sum", definition=defn)
    assert r.definition == defn

@pytest.mark.asyncio
async def test_update_metric(monkeypatch):
    svc, s = _svc(), _sess()
    m = _metric()
    monkeypatch.setattr(svc, "_get_user_metric", AsyncMock(return_value=m))
    r = await svc.update_metric(s, 1, 1, name="New Name", metric_type="average")
    assert r.name == "New Name" and r.metric_type == "average"

@pytest.mark.asyncio
async def test_update_metric_definition(monkeypatch):
    svc, s = _svc(), _sess()
    m = _metric()
    monkeypatch.setattr(svc, "_get_user_metric", AsyncMock(return_value=m))
    r = await svc.update_metric(s, 1, 1, definition={"new_def": True})
    assert r.definition == {"new_def": True}

@pytest.mark.asyncio
async def test_update_metric_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_metric",
        AsyncMock(side_effect=ValueError("not found")))
    with pytest.raises(ValueError):
        await svc.update_metric(s, 999, 1)

@pytest.mark.asyncio
async def test_delete_metric(monkeypatch):
    svc, s = _svc(), _sess()
    m = _metric()
    monkeypatch.setattr(svc, "_get_user_metric", AsyncMock(return_value=m))
    assert await svc.delete_metric(s, 1, 1) is True
    s.delete.assert_awaited_once_with(m)

@pytest.mark.asyncio
async def test_delete_metric_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_metric",
        AsyncMock(side_effect=ValueError("not found")))
    with pytest.raises(ValueError):
        await svc.delete_metric(s, 999, 1)

@pytest.mark.asyncio
@pytest.mark.parametrize("mtype,key", [
    ("count", "value"), ("sum", "value"), ("average", "value"),
    ("trend", "values"), ("distribution", "buckets"),
])
async def test_compute_metric_types(monkeypatch, mtype, key):
    svc, s = _svc(), _sess()
    m = _metric(mtype=mtype)
    monkeypatch.setattr(svc, "_get_user_metric", AsyncMock(return_value=m))
    r = await svc.compute_metric(s, 1, 1)
    assert key in r.current_value and r.last_computed_at is not None

@pytest.mark.asyncio
async def test_compute_metric_unknown_type(monkeypatch):
    svc, s = _svc(), _sess()
    m = _metric(mtype="unknown")
    monkeypatch.setattr(svc, "_get_user_metric", AsyncMock(return_value=m))
    r = await svc.compute_metric(s, 1, 1)
    assert r.current_value == {"value": None}


# ---- Schedules ----

@pytest.mark.asyncio
async def test_list_schedules():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_schedule(1), _schedule(2)])
    r = await svc.list_schedules(s, user_id=1)
    assert len(r) == 2

@pytest.mark.asyncio
async def test_list_schedules_active_only():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_schedule(active=True)])
    r = await svc.list_schedules(s, user_id=1, active_only=True)
    assert len(r) == 1

@pytest.mark.asyncio
async def test_create_schedule():
    svc, s = _svc(), _sess()
    r = await svc.create_schedule(s, user_id=1)
    s.add.assert_called_once()
    assert r.frequency == "daily" and r.is_active is True

@pytest.mark.asyncio
async def test_create_schedule_weekly():
    svc, s = _svc(), _sess()
    r = await svc.create_schedule(s, user_id=1, frequency="weekly", query_id=5)
    assert r.frequency == "weekly" and r.query_id == 5

@pytest.mark.asyncio
async def test_update_schedule(monkeypatch):
    svc, s = _svc(), _sess()
    sc = _schedule()
    monkeypatch.setattr(svc, "_get_user_schedule", AsyncMock(return_value=sc))
    r = await svc.update_schedule(s, 1, 1, frequency="hourly", is_active=False)
    assert r.frequency == "hourly" and r.is_active is False

@pytest.mark.asyncio
async def test_update_schedule_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_schedule",
        AsyncMock(side_effect=ValueError("not found")))
    with pytest.raises(ValueError):
        await svc.update_schedule(s, 999, 1)

@pytest.mark.asyncio
async def test_delete_schedule(monkeypatch):
    svc, s = _svc(), _sess()
    sc = _schedule()
    monkeypatch.setattr(svc, "_get_user_schedule", AsyncMock(return_value=sc))
    assert await svc.delete_schedule(s, 1, 1) is True
    s.delete.assert_awaited_once_with(sc)

@pytest.mark.asyncio
async def test_delete_schedule_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_schedule",
        AsyncMock(side_effect=ValueError("not found")))
    with pytest.raises(ValueError):
        await svc.delete_schedule(s, 999, 1)

@pytest.mark.asyncio
async def test_process_due_schedules():
    svc, s = _svc(), _sess()
    past = datetime.now(UTC) - timedelta(hours=1)
    sc1 = _schedule(sid=1, freq="daily")
    sc1.next_run_at = past
    sc2 = _schedule(sid=2, freq="hourly")
    sc2.next_run_at = past
    s.execute.return_value = _R(rows=[sc1, sc2])
    count = await svc.process_due_schedules(s)
    assert count == 2

@pytest.mark.asyncio
async def test_process_due_schedules_none_due():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[])
    count = await svc.process_due_schedules(s)
    assert count == 0


# ---- Stubs and helpers ----

@pytest.mark.asyncio
async def test_execute_query_stub():
    r = await _svc()._execute_query({"type": "search"}, {"cpc": "H01L"})
    assert "total_results" in r and r["total_results"] == 0

@pytest.mark.asyncio
async def test_compute_metric_value_stub():
    r = await _svc()._compute_metric_value("count", {})
    assert r == {"value": 0}

@pytest.mark.asyncio
async def test_get_user_query_success():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=_query(qid=3))
    assert (await svc._get_user_query(s, 3, 1)).id == 3

@pytest.mark.asyncio
async def test_get_user_query_not_found():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="query not found"):
        await svc._get_user_query(s, 999, 1)

@pytest.mark.asyncio
async def test_get_user_metric_success():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=_metric(mid=5))
    assert (await svc._get_user_metric(s, 5, 1)).id == 5

@pytest.mark.asyncio
async def test_get_user_metric_not_found():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="metric not found"):
        await svc._get_user_metric(s, 999, 1)

@pytest.mark.asyncio
async def test_get_user_schedule_success():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=_schedule(sid=7))
    assert (await svc._get_user_schedule(s, 7, 1)).id == 7

@pytest.mark.asyncio
async def test_get_user_schedule_not_found():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="schedule not found"):
        await svc._get_user_schedule(s, 999, 1)
