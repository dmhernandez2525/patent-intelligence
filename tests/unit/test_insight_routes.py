"""Tests for insight API routes."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.api.routes import insights as insights_mod


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

def _insight(iid=1, uid=1, pid=None, itype="summary"):
    return SimpleNamespace(
        id=iid, user_id=uid, patent_id=pid,
        insight_type=itype, status="completed",
        query_text=None, result_text="Summary result",
        result_data={"sections": ["background"]},
        model_used="gpt-4", token_count=100,
        error_message=None, completed_at=None, created_at=None)

def _template(tid=1, itype="summary"):
    return SimpleNamespace(
        id=tid, name="tmpl", insight_type=itype,
        prompt_template="Analyze {patent}",
        description="Desc", is_default=False)

def _patch(mp, name, rv=None, exc=None):
    mock = AsyncMock(side_effect=exc) if exc else AsyncMock(return_value=rv)
    mp.setattr(insights_mod, "insight_service",
        SimpleNamespace(**{name: mock}))

def _patch_act(mp):
    act = SimpleNamespace(log_event=AsyncMock())
    mp.setattr(insights_mod, "activity_service", act)
    return act

# ---- Insights list/create ----

@pytest.mark.asyncio
async def test_list_insights(monkeypatch):
    _patch(monkeypatch, "list_insights", rv=[_insight(1), _insight(2)])
    r = await insights_mod.list_insights(
        insight_type=None, patent_id=None,
        current_user=_user(), session=_session())
    assert len(r.insights) == 2 and r.total == 2

@pytest.mark.asyncio
async def test_list_insights_with_filters(monkeypatch):
    _patch(monkeypatch, "list_insights", rv=[_insight(1, itype="fto_analysis")])
    r = await insights_mod.list_insights(
        insight_type="fto_analysis", patent_id=10,
        current_user=_user(), session=_session())
    assert len(r.insights) == 1

@pytest.mark.asyncio
async def test_list_insights_empty(monkeypatch):
    _patch(monkeypatch, "list_insights", rv=[])
    r = await insights_mod.list_insights(
        insight_type=None, patent_id=None,
        current_user=_user(), session=_session())
    assert r.total == 0

@pytest.mark.asyncio
async def test_create_insight(monkeypatch):
    _patch(monkeypatch, "create_insight", rv=_insight(5))
    _patch_act(monkeypatch)
    payload = SimpleNamespace(insight_type="summary", query_text=None, patent_id=None)
    r = await insights_mod.create_insight(
        payload=payload, request=_req(),
        current_user=_user(), session=_session())
    assert r.id == 5

@pytest.mark.asyncio
async def test_create_insight_logs_activity(monkeypatch):
    _patch(monkeypatch, "create_insight", rv=_insight(5))
    act = _patch_act(monkeypatch)
    payload = SimpleNamespace(insight_type="summary", query_text=None, patent_id=None)
    await insights_mod.create_insight(
        payload=payload, request=_req(),
        current_user=_user(), session=_session())
    act.log_event.assert_awaited_once()
    call_kw = act.log_event.call_args[1]
    assert call_kw["event_type"] == "insight.created"

# ---- Get / Generate / Delete ----

@pytest.mark.asyncio
async def test_get_insight(monkeypatch):
    _patch(monkeypatch, "get_insight", rv=_insight(3))
    r = await insights_mod.get_insight(
        insight_id=3, current_user=_user(), session=_session())
    assert r.id == 3

@pytest.mark.asyncio
async def test_get_insight_not_found(monkeypatch):
    _patch(monkeypatch, "get_insight", exc=ValueError("not found"))
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await insights_mod.get_insight(
            insight_id=999, current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404

@pytest.mark.asyncio
async def test_generate_insight(monkeypatch):
    _patch(monkeypatch, "generate_insight", rv=_insight(4, itype="claim_analysis"))
    _patch_act(monkeypatch)
    r = await insights_mod.generate_insight(
        insight_id=4, request=_req(),
        current_user=_user(), session=_session())
    assert r.id == 4

@pytest.mark.asyncio
async def test_generate_insight_not_found(monkeypatch):
    _patch(monkeypatch, "generate_insight", exc=ValueError("not found"))
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await insights_mod.generate_insight(
            insight_id=999, request=_req(),
            current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404

@pytest.mark.asyncio
async def test_generate_insight_logs_activity(monkeypatch):
    _patch(monkeypatch, "generate_insight", rv=_insight(4))
    act = _patch_act(monkeypatch)
    await insights_mod.generate_insight(
        insight_id=4, request=_req(),
        current_user=_user(), session=_session())
    call_kw = act.log_event.call_args[1]
    assert call_kw["event_type"] == "insight.generated"
    assert call_kw["resource_id"] == "4"

@pytest.mark.asyncio
async def test_delete_insight(monkeypatch):
    _patch(monkeypatch, "delete_insight", rv=True)
    _patch_act(monkeypatch)
    r = await insights_mod.delete_insight(
        insight_id=3, request=_req(),
        current_user=_user(), session=_session())
    assert r == {"success": True}

@pytest.mark.asyncio
async def test_delete_insight_not_found(monkeypatch):
    _patch(monkeypatch, "delete_insight", exc=ValueError("not found"))
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await insights_mod.delete_insight(
            insight_id=999, request=_req(),
            current_user=_user(), session=_session())
    assert exc_info.value.status_code == 404

@pytest.mark.asyncio
async def test_delete_insight_logs_activity(monkeypatch):
    _patch(monkeypatch, "delete_insight", rv=True)
    act = _patch_act(monkeypatch)
    await insights_mod.delete_insight(
        insight_id=7, request=_req(),
        current_user=_user(), session=_session())
    call_kw = act.log_event.call_args[1]
    assert call_kw["event_type"] == "insight.deleted"
    assert call_kw["resource_id"] == "7"

# ---- Templates ----

@pytest.mark.asyncio
async def test_list_templates(monkeypatch):
    _patch(monkeypatch, "list_templates", rv=[_template(1), _template(2)])
    r = await insights_mod.list_templates(
        insight_type=None, current_user=_user(), session=_session())
    assert len(r.templates) == 2

@pytest.mark.asyncio
async def test_list_templates_by_type(monkeypatch):
    _patch(monkeypatch, "list_templates", rv=[_template(itype="fto_analysis")])
    r = await insights_mod.list_templates(
        insight_type="fto_analysis", current_user=_user(), session=_session())
    assert len(r.templates) == 1

@pytest.mark.asyncio
async def test_list_templates_empty(monkeypatch):
    _patch(monkeypatch, "list_templates", rv=[])
    r = await insights_mod.list_templates(
        insight_type=None, current_user=_user(), session=_session())
    assert len(r.templates) == 0
