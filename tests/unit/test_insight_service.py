"""Tests for the InsightService."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.insight import InsightTemplate, PatentInsight
from src.services.insight_service import DEFAULT_MODEL, InsightService


class _R:
    def __init__(self, val=None, rows=None):
        self._v, self._rows = val, rows or []
    def scalar_one_or_none(self): return self._v
    def scalars(self): return SimpleNamespace(all=lambda: self._rows)

def _svc(): return InsightService()

def _sess():
    s = AsyncMock()
    s.add = MagicMock()
    s.flush, s.refresh, s.delete = AsyncMock(), AsyncMock(), AsyncMock()
    return s

def _insight(iid=1, uid=1, pid=None, itype="summary", status="pending"):
    return PatentInsight(
        id=iid, user_id=uid, patent_id=pid,
        insight_type=itype, status=status,
        query_text=None, result_text=None,
        result_data={}, model_used=None,
        token_count=None, error_message=None,
        completed_at=None)

def _template(tid=1, itype="summary"):
    return InsightTemplate(
        id=tid, name=f"tmpl_{tid}", insight_type=itype,
        prompt_template="Analyze patent {number}",
        description="Test", is_default=False)

# ---- CRUD ----

@pytest.mark.asyncio
async def test_list_insights_returns_list():
    svc, s = _svc(), _sess()
    rows = [_insight(1), _insight(2)]
    s.execute.return_value = _R(rows=rows)
    r = await svc.list_insights(s, user_id=1)
    assert r == rows and len(r) == 2

@pytest.mark.asyncio
async def test_list_insights_empty():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[])
    assert await svc.list_insights(s, user_id=99) == []

@pytest.mark.asyncio
async def test_list_insights_with_type_filter():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_insight(itype="fto_analysis")])
    r = await svc.list_insights(s, user_id=1, insight_type="fto_analysis")
    assert len(r) == 1 and r[0].insight_type == "fto_analysis"

@pytest.mark.asyncio
async def test_list_insights_with_patent_filter():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_insight(pid=10)])
    r = await svc.list_insights(s, user_id=1, patent_id=10)
    assert len(r) == 1

@pytest.mark.asyncio
async def test_get_insight_success(monkeypatch):
    svc, s = _svc(), _sess()
    ins = _insight(iid=5, uid=1)
    monkeypatch.setattr(svc, "_get_user_insight", AsyncMock(return_value=ins))
    assert (await svc.get_insight(s, 5, 1)).id == 5

@pytest.mark.asyncio
async def test_get_insight_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_insight",
        AsyncMock(side_effect=ValueError("Insight not found")))
    with pytest.raises(ValueError, match="not found"):
        await svc.get_insight(s, 999, 1)

@pytest.mark.asyncio
async def test_create_insight_success():
    svc, s = _svc(), _sess()
    r = await svc.create_insight(s, user_id=1, insight_type="summary")
    s.add.assert_called_once()
    s.flush.assert_awaited_once()
    assert r.insight_type == "summary" and r.status == "pending"

@pytest.mark.asyncio
async def test_create_insight_with_query():
    svc, s = _svc(), _sess()
    r = await svc.create_insight(s, user_id=1, insight_type="nl_query",
        query_text="Find lithium battery patents", patent_id=42)
    assert r.query_text == "Find lithium battery patents" and r.patent_id == 42

@pytest.mark.asyncio
async def test_delete_insight_success(monkeypatch):
    svc, s = _svc(), _sess()
    ins = _insight(iid=3)
    monkeypatch.setattr(svc, "_get_user_insight", AsyncMock(return_value=ins))
    assert await svc.delete_insight(s, 3, 1) is True
    s.delete.assert_awaited_once_with(ins)

@pytest.mark.asyncio
async def test_delete_insight_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_insight",
        AsyncMock(side_effect=ValueError("Insight not found")))
    with pytest.raises(ValueError, match="not found"):
        await svc.delete_insight(s, 999, 1)

# ---- Generation ----

@pytest.mark.asyncio
async def test_generate_insight_summary(monkeypatch):
    svc, s = _svc(), _sess()
    ins = _insight(iid=1, itype="summary")
    monkeypatch.setattr(svc, "_get_user_insight", AsyncMock(return_value=ins))
    r = await svc.generate_insight(s, 1, 1)
    assert r.status == "completed" and r.model_used == DEFAULT_MODEL
    assert r.completed_at is not None

@pytest.mark.asyncio
async def test_generate_insight_claim_analysis(monkeypatch):
    svc, s = _svc(), _sess()
    ins = _insight(iid=2, itype="claim_analysis")
    monkeypatch.setattr(svc, "_get_user_insight", AsyncMock(return_value=ins))
    r = await svc.generate_insight(s, 2, 1)
    assert r.status == "completed" and "claim_scope" in r.result_data

@pytest.mark.asyncio
async def test_generate_insight_patentability(monkeypatch):
    svc, s = _svc(), _sess()
    ins = _insight(iid=3, itype="patentability")
    monkeypatch.setattr(svc, "_get_user_insight", AsyncMock(return_value=ins))
    r = await svc.generate_insight(s, 3, 1)
    assert r.status == "completed" and "novelty_score" in r.result_data

@pytest.mark.asyncio
async def test_generate_insight_fto(monkeypatch):
    svc, s = _svc(), _sess()
    ins = _insight(iid=4, itype="fto_analysis")
    monkeypatch.setattr(svc, "_get_user_insight", AsyncMock(return_value=ins))
    r = await svc.generate_insight(s, 4, 1)
    assert r.status == "completed" and "risk_level" in r.result_data

@pytest.mark.asyncio
async def test_generate_insight_nl_query(monkeypatch):
    svc, s = _svc(), _sess()
    ins = _insight(iid=5, itype="nl_query")
    ins.query_text = "battery patents"
    monkeypatch.setattr(svc, "_get_user_insight", AsyncMock(return_value=ins))
    r = await svc.generate_insight(s, 5, 1)
    assert r.status == "completed" and "battery patents" in r.result_text

@pytest.mark.asyncio
async def test_generate_insight_competitive_brief(monkeypatch):
    svc, s = _svc(), _sess()
    ins = _insight(iid=6, itype="competitive_brief")
    monkeypatch.setattr(svc, "_get_user_insight", AsyncMock(return_value=ins))
    r = await svc.generate_insight(s, 6, 1)
    assert r.status == "completed" and "competitors" in r.result_data

@pytest.mark.asyncio
async def test_generate_insight_unknown_type(monkeypatch):
    svc, s = _svc(), _sess()
    ins = _insight(iid=7, itype="unknown_type")
    monkeypatch.setattr(svc, "_get_user_insight", AsyncMock(return_value=ins))
    r = await svc.generate_insight(s, 7, 1)
    assert r.status == "failed" and "Unknown insight type" in r.error_message

@pytest.mark.asyncio
async def test_generate_insight_failure(monkeypatch):
    svc, s = _svc(), _sess()
    ins = _insight(iid=8, itype="summary")
    monkeypatch.setattr(svc, "_get_user_insight", AsyncMock(return_value=ins))
    monkeypatch.setattr(svc, "_generate_summary",
        AsyncMock(side_effect=RuntimeError("AI service down")))
    r = await svc.generate_insight(s, 8, 1)
    assert r.status == "failed" and "AI service down" in r.error_message

@pytest.mark.asyncio
async def test_generate_insight_not_found(monkeypatch):
    svc, s = _svc(), _sess()
    monkeypatch.setattr(svc, "_get_user_insight",
        AsyncMock(side_effect=ValueError("Insight not found")))
    with pytest.raises(ValueError, match="not found"):
        await svc.generate_insight(s, 999, 1)

# ---- Stubs ----

@pytest.mark.asyncio
async def test_stub_summary():
    r = await _svc()._generate_summary(_insight(), _sess())
    assert r["model_used"] == DEFAULT_MODEL and "sections" in r["result_data"]

@pytest.mark.asyncio
async def test_stub_claim_analysis():
    r = await _svc()._generate_claim_analysis(_insight(), _sess())
    assert "independent_claims" in r["result_data"]

@pytest.mark.asyncio
async def test_stub_patentability():
    r = await _svc()._generate_patentability(_insight(), _sess())
    assert r["result_data"]["novelty_score"] == 0.0

@pytest.mark.asyncio
async def test_stub_fto():
    r = await _svc()._generate_fto(_insight(), _sess())
    assert r["result_data"]["risk_level"] == "unknown"

@pytest.mark.asyncio
async def test_stub_nl_query():
    ins = _insight()
    ins.query_text = "test query"
    r = await _svc()._generate_nl_query(ins, _sess())
    assert "test query" in r["result_text"]

@pytest.mark.asyncio
async def test_stub_competitive_brief():
    r = await _svc()._generate_competitive_brief(_insight(), _sess())
    assert "competitors" in r["result_data"]

# ---- Templates ----

@pytest.mark.asyncio
async def test_list_templates_all():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_template(1), _template(2)])
    assert len(await svc.list_templates(s)) == 2

@pytest.mark.asyncio
async def test_list_templates_by_type():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(rows=[_template(itype="fto_analysis")])
    r = await svc.list_templates(s, insight_type="fto_analysis")
    assert len(r) == 1

@pytest.mark.asyncio
async def test_get_template_success():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=_template(tid=5))
    assert (await svc.get_template(s, 5)).id == 5

@pytest.mark.asyncio
async def test_get_template_not_found():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="Template not found"):
        await svc.get_template(s, 999)

# ---- Internal helpers ----

@pytest.mark.asyncio
async def test_get_user_insight_success():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=_insight(iid=3, uid=1))
    assert (await svc._get_user_insight(s, 3, 1)).id == 3

@pytest.mark.asyncio
async def test_get_user_insight_not_found():
    svc, s = _svc(), _sess()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="Insight not found"):
        await svc._get_user_insight(s, 999, 1)
