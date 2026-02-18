"""Tests for custom analytics API routes."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.api.routes import analytics as analytics_mod


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

def _query(qid=1, name="Test Query"):
    return SimpleNamespace(
        id=qid, name=name, description=None,
        query_config={}, filters={}, status="saved",
        is_public=False, last_run_at=None, run_count=0, created_at=None)

def _metric(mid=1, name="Test Metric"):
    return SimpleNamespace(
        id=mid, name=name, metric_type="count",
        definition={}, current_value=None,
        last_computed_at=None, created_at=None)

def _schedule(sid=1):
    return SimpleNamespace(
        id=sid, query_id=None, metric_id=None,
        frequency="daily", is_active=True,
        next_run_at=None, created_at=None)

def _patch(mp, name, rv=None, exc=None):
    mock = AsyncMock(side_effect=exc) if exc else AsyncMock(return_value=rv)
    mp.setattr(analytics_mod, "analytics_service",
        SimpleNamespace(**{name: mock}))

def _patch_act(mp):
    act = SimpleNamespace(log_event=AsyncMock())
    mp.setattr(analytics_mod, "activity_service", act)
    return act


# ---- Saved Queries ----

@pytest.mark.asyncio
async def test_list_queries(monkeypatch):
    _patch(monkeypatch, "list_queries", rv=[_query(1), _query(2)])
    r = await analytics_mod.list_queries(
        status_filter=None, public=False,
        current_user=_user(), session=_session())
    assert len(r.queries) == 2

@pytest.mark.asyncio
async def test_create_query(monkeypatch):
    _patch(monkeypatch, "create_query", rv=_query(5))
    _patch_act(monkeypatch)
    payload = SimpleNamespace(
        name="New", description=None,
        query_config={}, filters={}, is_public=False)
    r = await analytics_mod.create_query(
        payload=payload, request=_req(),
        current_user=_user(), session=_session())
    assert r.id == 5

@pytest.mark.asyncio
async def test_create_query_logs_activity(monkeypatch):
    _patch(monkeypatch, "create_query", rv=_query(5))
    act = _patch_act(monkeypatch)
    payload = SimpleNamespace(
        name="New", description=None,
        query_config={}, filters={}, is_public=False)
    await analytics_mod.create_query(
        payload=payload, request=_req(),
        current_user=_user(), session=_session())
    assert act.log_event.call_args[1]["event_type"] == "analytics.query.created"

@pytest.mark.asyncio
async def test_update_query(monkeypatch):
    _patch(monkeypatch, "update_query", rv=_query(1, name="Updated"))
    payload = SimpleNamespace(model_dump=lambda exclude_unset: {"name": "Updated"})
    r = await analytics_mod.update_query(
        query_id=1, payload=payload,
        current_user=_user(), session=_session())
    assert r.name == "Updated"

@pytest.mark.asyncio
async def test_update_query_not_found(monkeypatch):
    _patch(monkeypatch, "update_query", exc=ValueError("not found"))
    payload = SimpleNamespace(model_dump=lambda exclude_unset: {"name": "X"})
    with pytest.raises(HTTPException) as exc_info:
        await analytics_mod.update_query(
            query_id=999, payload=payload,
            current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404

@pytest.mark.asyncio
async def test_update_query_no_updates(monkeypatch):
    payload = SimpleNamespace(model_dump=lambda exclude_unset: {})
    with pytest.raises(HTTPException) as exc_info:
        await analytics_mod.update_query(
            query_id=1, payload=payload,
            current_user=_user(), session=_session())
    assert exc_info.value.status_code == 400

@pytest.mark.asyncio
async def test_delete_query(monkeypatch):
    _patch(monkeypatch, "delete_query", rv=True)
    r = await analytics_mod.delete_query(
        query_id=1, current_user=_user(), session=_session())
    assert r == {"success": True}

@pytest.mark.asyncio
async def test_delete_query_not_found(monkeypatch):
    _patch(monkeypatch, "delete_query", exc=ValueError("not found"))
    with pytest.raises(HTTPException) as exc_info:
        await analytics_mod.delete_query(
            query_id=999, current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404

@pytest.mark.asyncio
async def test_run_query(monkeypatch):
    q = _query(1)
    q.last_run_at = None
    q.run_count = 1
    _patch(monkeypatch, "run_query", rv=q)
    r = await analytics_mod.run_query(
        query_id=1, current_user=_user(), session=_session())
    assert r.run_count == 1

@pytest.mark.asyncio
async def test_run_query_not_found(monkeypatch):
    _patch(monkeypatch, "run_query", exc=ValueError("not found"))
    with pytest.raises(HTTPException) as exc_info:
        await analytics_mod.run_query(
            query_id=999, current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404

# ---- Custom Metrics ----

@pytest.mark.asyncio
async def test_list_metrics(monkeypatch):
    _patch(monkeypatch, "list_metrics", rv=[_metric(1), _metric(2)])
    r = await analytics_mod.list_metrics(
        metric_type=None, current_user=_user(), session=_session())
    assert len(r.metrics) == 2

@pytest.mark.asyncio
async def test_create_metric(monkeypatch):
    _patch(monkeypatch, "create_metric", rv=_metric(7))
    _patch_act(monkeypatch)
    payload = SimpleNamespace(
        name="Metric", metric_type="count", definition={})
    r = await analytics_mod.create_metric(
        payload=payload, request=_req(),
        current_user=_user(), session=_session())
    assert r.id == 7

@pytest.mark.asyncio
async def test_update_metric(monkeypatch):
    _patch(monkeypatch, "update_metric", rv=_metric(1, name="New"))
    payload = SimpleNamespace(model_dump=lambda exclude_unset: {"name": "New"})
    r = await analytics_mod.update_metric(
        metric_id=1, payload=payload,
        current_user=_user(), session=_session())
    assert r.name == "New"

@pytest.mark.asyncio
async def test_update_metric_not_found(monkeypatch):
    _patch(monkeypatch, "update_metric", exc=ValueError("not found"))
    payload = SimpleNamespace(model_dump=lambda exclude_unset: {"name": "X"})
    with pytest.raises(HTTPException) as exc_info:
        await analytics_mod.update_metric(
            metric_id=999, payload=payload,
            current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404

@pytest.mark.asyncio
async def test_update_metric_no_updates(monkeypatch):
    payload = SimpleNamespace(model_dump=lambda exclude_unset: {})
    with pytest.raises(HTTPException) as exc_info:
        await analytics_mod.update_metric(
            metric_id=1, payload=payload,
            current_user=_user(), session=_session())
    assert exc_info.value.status_code == 400

@pytest.mark.asyncio
async def test_delete_metric(monkeypatch):
    _patch(monkeypatch, "delete_metric", rv=True)
    r = await analytics_mod.delete_metric(
        metric_id=1, current_user=_user(), session=_session())
    assert r == {"success": True}

@pytest.mark.asyncio
async def test_delete_metric_not_found(monkeypatch):
    _patch(monkeypatch, "delete_metric", exc=ValueError("not found"))
    with pytest.raises(HTTPException) as exc_info:
        await analytics_mod.delete_metric(
            metric_id=999, current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404

@pytest.mark.asyncio
async def test_compute_metric(monkeypatch):
    m = _metric(1)
    m.current_value = {"value": 42}
    _patch(monkeypatch, "compute_metric", rv=m)
    r = await analytics_mod.compute_metric(
        metric_id=1, current_user=_user(), session=_session())
    assert r.current_value == {"value": 42}

@pytest.mark.asyncio
async def test_compute_metric_not_found(monkeypatch):
    _patch(monkeypatch, "compute_metric", exc=ValueError("not found"))
    with pytest.raises(HTTPException) as exc_info:
        await analytics_mod.compute_metric(
            metric_id=999, current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404

# ---- Schedules ----

@pytest.mark.asyncio
async def test_list_schedules(monkeypatch):
    _patch(monkeypatch, "list_schedules", rv=[_schedule(1), _schedule(2)])
    r = await analytics_mod.list_schedules(
        active=False, current_user=_user(), session=_session())
    assert len(r.schedules) == 2

@pytest.mark.asyncio
async def test_create_schedule(monkeypatch):
    _patch(monkeypatch, "create_schedule", rv=_schedule(3))
    _patch_act(monkeypatch)
    payload = SimpleNamespace(
        frequency="daily", query_id=None, metric_id=None)
    r = await analytics_mod.create_schedule(
        payload=payload, request=_req(),
        current_user=_user(), session=_session())
    assert r.id == 3

@pytest.mark.asyncio
async def test_create_schedule_logs_activity(monkeypatch):
    _patch(monkeypatch, "create_schedule", rv=_schedule(3))
    act = _patch_act(monkeypatch)
    payload = SimpleNamespace(
        frequency="weekly", query_id=None, metric_id=None)
    await analytics_mod.create_schedule(
        payload=payload, request=_req(),
        current_user=_user(), session=_session())
    assert act.log_event.call_args[1]["event_type"] == "analytics.schedule.created"

@pytest.mark.asyncio
async def test_update_schedule(monkeypatch):
    s = _schedule(1)
    s.frequency = "weekly"
    _patch(monkeypatch, "update_schedule", rv=s)
    payload = SimpleNamespace(model_dump=lambda exclude_unset: {"frequency": "weekly"})
    r = await analytics_mod.update_schedule(
        schedule_id=1, payload=payload,
        current_user=_user(), session=_session())
    assert r.frequency == "weekly"

@pytest.mark.asyncio
async def test_update_schedule_not_found(monkeypatch):
    _patch(monkeypatch, "update_schedule", exc=ValueError("not found"))
    payload = SimpleNamespace(model_dump=lambda exclude_unset: {"is_active": False})
    with pytest.raises(HTTPException) as exc_info:
        await analytics_mod.update_schedule(
            schedule_id=999, payload=payload,
            current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404

@pytest.mark.asyncio
async def test_update_schedule_no_updates(monkeypatch):
    payload = SimpleNamespace(model_dump=lambda exclude_unset: {})
    with pytest.raises(HTTPException) as exc_info:
        await analytics_mod.update_schedule(
            schedule_id=1, payload=payload,
            current_user=_user(), session=_session())
    assert exc_info.value.status_code == 400

@pytest.mark.asyncio
async def test_delete_schedule(monkeypatch):
    _patch(monkeypatch, "delete_schedule", rv=True)
    r = await analytics_mod.delete_schedule(
        schedule_id=1, current_user=_user(), session=_session())
    assert r == {"success": True}

@pytest.mark.asyncio
async def test_delete_schedule_not_found(monkeypatch):
    _patch(monkeypatch, "delete_schedule", exc=ValueError("not found"))
    with pytest.raises(HTTPException) as exc_info:
        await analytics_mod.delete_schedule(
            schedule_id=999, current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404
