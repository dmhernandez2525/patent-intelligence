"""Tests for competitive intelligence API routes."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.api.routes import competitive as comp_mod


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

def _monitor(mid=1, name="Acme"):
    return SimpleNamespace(
        id=mid, competitor_name=name, aliases=[], cpc_focus=[],
        status="active", notes=None, last_checked_at=None, created_at=None)

def _comparison(cid=1):
    return SimpleNamespace(
        id=cid, entity_a="Acme", entity_b="Beta",
        status="completed", comparison_data={"shared_cpc": []},
        overlap_score=0.5, summary="Good overlap",
        error_message=None, computed_at=None, created_at=None)

def _target(tid=1, name="Startup"):
    return SimpleNamespace(
        id=tid, target_name=name, rationale="Strong IP",
        patent_count=10, relevance_score=0.7,
        cpc_overlap=["H01L"], analysis_data={},
        is_starred=False, created_at=None)

def _patch(mp, name, rv=None, exc=None):
    mock = AsyncMock(side_effect=exc) if exc else AsyncMock(return_value=rv)
    mp.setattr(comp_mod, "competitive_service",
        SimpleNamespace(**{name: mock}))

def _patch_act(mp):
    act = SimpleNamespace(log_event=AsyncMock())
    mp.setattr(comp_mod, "activity_service", act)
    return act

# ---- Monitors ----

@pytest.mark.asyncio
async def test_list_monitors(monkeypatch):
    _patch(monkeypatch, "list_monitors", rv=[_monitor(1), _monitor(2)])
    r = await comp_mod.list_monitors(
        status_filter=None, current_user=_user(), session=_session())
    assert len(r.monitors) == 2

@pytest.mark.asyncio
async def test_create_monitor(monkeypatch):
    _patch(monkeypatch, "create_monitor", rv=_monitor(5))
    _patch_act(monkeypatch)
    payload = SimpleNamespace(
        competitor_name="Acme", aliases=[], cpc_focus=[], notes=None)
    r = await comp_mod.create_monitor(
        payload=payload, request=_req(),
        current_user=_user(), session=_session())
    assert r.id == 5

@pytest.mark.asyncio
async def test_create_monitor_logs_activity(monkeypatch):
    _patch(monkeypatch, "create_monitor", rv=_monitor(5))
    act = _patch_act(monkeypatch)
    payload = SimpleNamespace(
        competitor_name="Acme", aliases=[], cpc_focus=[], notes=None)
    await comp_mod.create_monitor(
        payload=payload, request=_req(),
        current_user=_user(), session=_session())
    assert act.log_event.call_args[1]["event_type"] == "competitive.monitor.created"

@pytest.mark.asyncio
async def test_update_monitor(monkeypatch):
    _patch(monkeypatch, "update_monitor", rv=_monitor(1, name="New"))
    payload = SimpleNamespace(model_dump=lambda exclude_unset: {"competitor_name": "New"})
    r = await comp_mod.update_monitor(
        monitor_id=1, payload=payload,
        current_user=_user(), session=_session())
    assert r.competitor_name == "New"

@pytest.mark.asyncio
async def test_update_monitor_not_found(monkeypatch):
    _patch(monkeypatch, "update_monitor", exc=ValueError("not found"))
    payload = SimpleNamespace(model_dump=lambda exclude_unset: {"status": "paused"})
    with pytest.raises(HTTPException) as exc_info:
        await comp_mod.update_monitor(
            monitor_id=999, payload=payload,
            current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404

@pytest.mark.asyncio
async def test_update_monitor_no_updates(monkeypatch):
    payload = SimpleNamespace(model_dump=lambda exclude_unset: {})
    with pytest.raises(HTTPException) as exc_info:
        await comp_mod.update_monitor(
            monitor_id=1, payload=payload,
            current_user=_user(), session=_session())
    assert exc_info.value.status_code == 400

@pytest.mark.asyncio
async def test_delete_monitor(monkeypatch):
    _patch(monkeypatch, "delete_monitor", rv=True)
    r = await comp_mod.delete_monitor(
        monitor_id=1, current_user=_user(), session=_session())
    assert r == {"success": True}

@pytest.mark.asyncio
async def test_delete_monitor_not_found(monkeypatch):
    _patch(monkeypatch, "delete_monitor", exc=ValueError("not found"))
    with pytest.raises(HTTPException) as exc_info:
        await comp_mod.delete_monitor(
            monitor_id=999, current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404

# ---- Comparisons ----

@pytest.mark.asyncio
async def test_list_comparisons(monkeypatch):
    _patch(monkeypatch, "list_comparisons", rv=[_comparison(1)])
    r = await comp_mod.list_comparisons(
        current_user=_user(), session=_session())
    assert len(r.comparisons) == 1

@pytest.mark.asyncio
async def test_create_comparison(monkeypatch):
    _patch(monkeypatch, "create_comparison", rv=_comparison(3))
    _patch_act(monkeypatch)
    payload = SimpleNamespace(entity_a="Acme", entity_b="Beta")
    r = await comp_mod.create_comparison(
        payload=payload, request=_req(),
        current_user=_user(), session=_session())
    assert r.id == 3

@pytest.mark.asyncio
async def test_compute_comparison(monkeypatch):
    _patch(monkeypatch, "compute_comparison", rv=_comparison(1))
    r = await comp_mod.compute_comparison(
        comparison_id=1, current_user=_user(), session=_session())
    assert r.status == "completed"

@pytest.mark.asyncio
async def test_compute_comparison_not_found(monkeypatch):
    _patch(monkeypatch, "compute_comparison", exc=ValueError("not found"))
    with pytest.raises(HTTPException) as exc_info:
        await comp_mod.compute_comparison(
            comparison_id=999, current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404

@pytest.mark.asyncio
async def test_delete_comparison(monkeypatch):
    _patch(monkeypatch, "delete_comparison", rv=True)
    r = await comp_mod.delete_comparison(
        comparison_id=1, current_user=_user(), session=_session())
    assert r == {"success": True}

# ---- Targets ----

@pytest.mark.asyncio
async def test_list_targets(monkeypatch):
    _patch(monkeypatch, "list_targets", rv=[_target(1), _target(2)])
    r = await comp_mod.list_targets(
        starred=False, current_user=_user(), session=_session())
    assert len(r.targets) == 2

@pytest.mark.asyncio
async def test_create_target(monkeypatch):
    _patch(monkeypatch, "create_target", rv=_target(7))
    _patch_act(monkeypatch)
    payload = SimpleNamespace(
        target_name="Startup", rationale=None,
        patent_count=0, relevance_score=None, cpc_overlap=[])
    r = await comp_mod.create_target(
        payload=payload, request=_req(),
        current_user=_user(), session=_session())
    assert r.id == 7

@pytest.mark.asyncio
async def test_update_target(monkeypatch):
    _patch(monkeypatch, "update_target", rv=_target(1, name="New"))
    payload = SimpleNamespace(model_dump=lambda exclude_unset: {"target_name": "New"})
    r = await comp_mod.update_target(
        target_id=1, payload=payload,
        current_user=_user(), session=_session())
    assert r.target_name == "New"

@pytest.mark.asyncio
async def test_update_target_not_found(monkeypatch):
    _patch(monkeypatch, "update_target", exc=ValueError("not found"))
    payload = SimpleNamespace(model_dump=lambda exclude_unset: {"is_starred": True})
    with pytest.raises(HTTPException) as exc_info:
        await comp_mod.update_target(
            target_id=999, payload=payload,
            current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404

@pytest.mark.asyncio
async def test_delete_target(monkeypatch):
    _patch(monkeypatch, "delete_target", rv=True)
    r = await comp_mod.delete_target(
        target_id=1, current_user=_user(), session=_session())
    assert r == {"success": True}

@pytest.mark.asyncio
async def test_delete_target_not_found(monkeypatch):
    _patch(monkeypatch, "delete_target", exc=ValueError("not found"))
    with pytest.raises(HTTPException) as exc_info:
        await comp_mod.delete_target(
            target_id=999, current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404
