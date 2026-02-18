"""Tests for the CompetitiveService."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.competitive import (
    AcquisitionTarget,
    CompetitorMonitor,
    PortfolioComparison,
)
from src.services.competitive_service import CompetitiveService


class _R:
    def __init__(self, val=None, rows=None):
        self._v, self._rows = val, rows or []
    def scalar_one_or_none(self): return self._v
    def scalars(self): return SimpleNamespace(all=lambda: self._rows)

def _svc(): return CompetitiveService()

def _sess():
    s = AsyncMock()
    s.add = MagicMock()
    s.flush, s.refresh, s.delete = AsyncMock(), AsyncMock(), AsyncMock()
    return s

def _monitor(mid=1, uid=1, name="Acme Corp", status="active"):
    return CompetitorMonitor(
        id=mid, user_id=uid, competitor_name=name,
        aliases=[], cpc_focus=[], status=status, notes=None)

def _comparison(cid=1, uid=1):
    return PortfolioComparison(
        id=cid, user_id=uid, entity_a="Acme", entity_b="Beta",
        status="pending", comparison_data={}, overlap_score=None,
        summary=None, error_message=None, computed_at=None)

def _target(tid=1, uid=1, name="Startup X"):
    return AcquisitionTarget(
        id=tid, user_id=uid, target_name=name,
        rationale=None, patent_count=0, relevance_score=None,
        cpc_overlap=[], analysis_data={}, is_starred=False)

# ---- Monitors ----

@pytest.mark.asyncio
async def test_list_monitors():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_monitor(1), _monitor(2)])
    r = await svc.list_monitors(s, user_id=1)
    assert len(r) == 2

@pytest.mark.asyncio
async def test_list_monitors_with_status():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_monitor(status="paused")])
    r = await svc.list_monitors(s, user_id=1, status="paused")
    assert len(r) == 1

@pytest.mark.asyncio
async def test_create_monitor():
    svc, s = _svc(), _sess()
    r = await svc.create_monitor(s, user_id=1, competitor_name="Acme")
    s.add.assert_called_once()
    assert r.competitor_name == "Acme" and r.status == "active"

@pytest.mark.asyncio
async def test_update_monitor(monkeypatch):
    svc, s = _svc(), _sess()
    m = _monitor()
    monkeypatch.setattr(svc, "_get_user_monitor", AsyncMock(return_value=m))
    r = await svc.update_monitor(s, 1, 1, competitor_name="New", status="paused")
    assert r.competitor_name == "New" and r.status == "paused"

@pytest.mark.asyncio
async def test_update_monitor_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_monitor",
        AsyncMock(side_effect=ValueError("not found")))
    with pytest.raises(ValueError, match="not found"):
        await svc.update_monitor(s, 999, 1)

@pytest.mark.asyncio
async def test_delete_monitor(monkeypatch):
    svc, s = _svc(), _sess()
    m = _monitor()
    monkeypatch.setattr(svc, "_get_user_monitor", AsyncMock(return_value=m))
    assert await svc.delete_monitor(s, 1, 1) is True
    s.delete.assert_awaited_once_with(m)

@pytest.mark.asyncio
async def test_delete_monitor_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_monitor",
        AsyncMock(side_effect=ValueError("not found")))
    with pytest.raises(ValueError):
        await svc.delete_monitor(s, 999, 1)

# ---- Comparisons ----

@pytest.mark.asyncio
async def test_list_comparisons():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_comparison(1), _comparison(2)])
    assert len(await svc.list_comparisons(s, user_id=1)) == 2

@pytest.mark.asyncio
async def test_create_comparison():
    svc, s = _svc(), _sess()
    r = await svc.create_comparison(s, user_id=1, entity_a="A", entity_b="B")
    s.add.assert_called_once()
    assert r.entity_a == "A" and r.status == "pending"

@pytest.mark.asyncio
async def test_compute_comparison_success(monkeypatch):
    svc, s = _svc(), _sess()
    comp = _comparison()
    monkeypatch.setattr(svc, "_get_user_comparison", AsyncMock(return_value=comp))
    r = await svc.compute_comparison(s, 1, 1)
    assert r.status == "completed" and r.overlap_score is not None

@pytest.mark.asyncio
async def test_compute_comparison_failure(monkeypatch):
    svc, s = _svc(), _sess()
    comp = _comparison()
    monkeypatch.setattr(svc, "_get_user_comparison", AsyncMock(return_value=comp))
    monkeypatch.setattr(svc, "_run_comparison",
        AsyncMock(side_effect=RuntimeError("API error")))
    r = await svc.compute_comparison(s, 1, 1)
    assert r.status == "failed" and "API error" in r.error_message

@pytest.mark.asyncio
async def test_delete_comparison(monkeypatch):
    svc, s = _svc(), _sess()
    comp = _comparison()
    monkeypatch.setattr(svc, "_get_user_comparison", AsyncMock(return_value=comp))
    assert await svc.delete_comparison(s, 1, 1) is True

# ---- Targets ----

@pytest.mark.asyncio
async def test_list_targets():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_target(1), _target(2)])
    assert len(await svc.list_targets(s, user_id=1)) == 2

@pytest.mark.asyncio
async def test_list_targets_starred():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_target(1)])
    r = await svc.list_targets(s, user_id=1, starred_only=True)
    assert len(r) == 1

@pytest.mark.asyncio
async def test_create_target():
    svc, s = _svc(), _sess()
    r = await svc.create_target(s, user_id=1, target_name="Startup",
        rationale="Strong IP", patent_count=50, relevance_score=0.8)
    s.add.assert_called_once()
    assert r.target_name == "Startup" and r.patent_count == 50

@pytest.mark.asyncio
async def test_update_target(monkeypatch):
    svc, s = _svc(), _sess()
    t = _target()
    monkeypatch.setattr(svc, "_get_user_target", AsyncMock(return_value=t))
    r = await svc.update_target(s, 1, 1, target_name="New", is_starred=True)
    assert r.target_name == "New" and r.is_starred is True

@pytest.mark.asyncio
async def test_update_target_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_target",
        AsyncMock(side_effect=ValueError("not found")))
    with pytest.raises(ValueError):
        await svc.update_target(s, 999, 1)

@pytest.mark.asyncio
async def test_delete_target(monkeypatch):
    svc, s = _svc(), _sess()
    t = _target()
    monkeypatch.setattr(svc, "_get_user_target", AsyncMock(return_value=t))
    assert await svc.delete_target(s, 1, 1) is True

@pytest.mark.asyncio
async def test_delete_target_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_target",
        AsyncMock(side_effect=ValueError("not found")))
    with pytest.raises(ValueError):
        await svc.delete_target(s, 999, 1)

# ---- Stubs and helpers ----

@pytest.mark.asyncio
async def test_run_comparison_stub():
    r = await _svc()._run_comparison("Acme", "Beta")
    assert "comparison_data" in r and r["overlap_score"] == 0.0

@pytest.mark.asyncio
async def test_get_user_monitor_success():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=_monitor(mid=3))
    assert (await svc._get_user_monitor(s, 3, 1)).id == 3

@pytest.mark.asyncio
async def test_get_user_monitor_not_found():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="monitor not found"):
        await svc._get_user_monitor(s, 999, 1)

@pytest.mark.asyncio
async def test_get_user_comparison_success():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=_comparison(cid=5))
    assert (await svc._get_user_comparison(s, 5, 1)).id == 5

@pytest.mark.asyncio
async def test_get_user_comparison_not_found():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="comparison not found"):
        await svc._get_user_comparison(s, 999, 1)

@pytest.mark.asyncio
async def test_get_user_target_success():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=_target(tid=7))
    assert (await svc._get_user_target(s, 7, 1)).id == 7

@pytest.mark.asyncio
async def test_get_user_target_not_found():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="target not found"):
        await svc._get_user_target(s, 999, 1)
