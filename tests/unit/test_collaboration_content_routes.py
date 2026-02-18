"""Unit tests for collaboration content and mentions routes."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from src.api.routes import collaboration_content as _cc
from src.api.routes import collaboration_mentions as _cm
from src.models.user import User

_NOW = datetime.now(UTC)
_svc = _cc.collaboration_content_service
_msvc = _cm.collaboration_content_service


def _req() -> Request:
    return Request({
        "type": "http", "method": "POST", "path": "/",
        "headers": [], "client": ("127.0.0.1", 7777),
    })


def _user() -> User:
    return User(
        id=1, email="t@example.com",
        hashed_password="".join(["h", "x"]),
        role="analyst", is_active=True,
    )


def _ses() -> AsyncMock:
    s = AsyncMock()
    s.commit = AsyncMock()
    return s


def _ann(aid: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        id=aid, patent_id=10, user_id=1,
        text="note", created_at=_NOW, updated_at=_NOW,
    )


def _thread(tid: int = 1, comments: list | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=tid, patent_id=10, project_id=None,
        title="Discussion", created_by_user_id=1,
        comments=comments or [], created_at=_NOW,
    )


def _cmt(cid: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        id=cid, thread_id=1, user_id=1,
        parent_comment_id=None, text="hello",
        is_deleted=False, edited_at=None, created_at=_NOW,
    )


def _mention(mid: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        id=mid, user_id=1, comment_id=5, message="pinged",
        is_read=False, read_at=None, created_at=_NOW,
    )


def _act(mp: pytest.MonkeyPatch) -> None:
    mp.setattr(_cc.activity_service, "log_event", AsyncMock())


@pytest.mark.asyncio
async def test_create_and_list_annotations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ses = _ses()
    monkeypatch.setattr(_svc, "add_annotation", AsyncMock(return_value=_ann()))
    _act(monkeypatch)
    payload = _cc.AnnotationCreateRequest(text="note")
    created = await _cc.create_annotation(
        patent_id=10, payload=payload, request=_req(),
        current_user=_user(), session=ses,
    )
    assert created.id == 1 and created.patent_id == 10
    monkeypatch.setattr(
        _svc, "list_annotations",
        AsyncMock(return_value=[_ann(), _ann(aid=2)]),
    )
    listed = await _cc.list_annotations(
        patent_id=10, current_user=_user(), session=ses,
    )
    assert len(listed) == 2 and listed[1].id == 2


@pytest.mark.asyncio
async def test_create_thread_and_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ses = _ses()
    monkeypatch.setattr(_svc, "create_thread", AsyncMock(return_value=_thread()))
    _act(monkeypatch)
    payload = _cc.CommentThreadCreateRequest(title="Discussion")
    r = await _cc.create_comment_thread(
        patent_id=10, payload=payload,
        current_user=_user(), session=ses,
    )
    assert r.id == 1 and r.comments == []
    monkeypatch.setattr(
        _svc, "list_threads",
        AsyncMock(return_value=[_thread(), _thread(tid=2)]),
    )
    listed = await _cc.list_comment_threads(
        patent_id=10, current_user=_user(), session=_ses(),
    )
    assert len(listed) == 2 and listed[0].title == "Discussion"


@pytest.mark.asyncio
async def test_create_thread_permission_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        _svc, "create_thread",
        AsyncMock(side_effect=PermissionError("no")),
    )
    payload = _cc.CommentThreadCreateRequest(title="Discussion")
    with pytest.raises(HTTPException) as exc:
        await _cc.create_comment_thread(
            patent_id=10, payload=payload,
            current_user=_user(), session=_ses(),
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_add_comment_success(monkeypatch: pytest.MonkeyPatch) -> None:
    ses = _ses()
    monkeypatch.setattr(_svc, "add_comment", AsyncMock(return_value=_cmt()))
    _act(monkeypatch)
    payload = _cc.CommentCreateRequest(text="hello")
    r = await _cc.add_comment(
        thread_id=1, payload=payload,
        current_user=_user(), session=ses,
    )
    assert r.id == 1 and r.text == "hello"


@pytest.mark.asyncio
async def test_add_comment_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        _svc, "add_comment", AsyncMock(side_effect=ValueError("bad")),
    )
    payload = _cc.CommentCreateRequest(text="hello")
    with pytest.raises(HTTPException) as exc:
        await _cc.add_comment(
            thread_id=99, payload=payload,
            current_user=_user(), session=_ses(),
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_edit_comment_success(monkeypatch: pytest.MonkeyPatch) -> None:
    ses = _ses()
    monkeypatch.setattr(_svc, "edit_comment", AsyncMock(return_value=_cmt()))
    _act(monkeypatch)
    payload = _cc.CommentUpdateRequest(text="updated")
    r = await _cc.edit_comment(
        comment_id=1, payload=payload,
        current_user=_user(), session=ses,
    )
    assert r.id == 1


@pytest.mark.asyncio
async def test_edit_comment_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _cc.CommentUpdateRequest(text="updated")
    monkeypatch.setattr(
        _svc, "edit_comment", AsyncMock(side_effect=ValueError("nope")),
    )
    with pytest.raises(HTTPException) as exc:
        await _cc.edit_comment(
            comment_id=99, payload=payload,
            current_user=_user(), session=_ses(),
        )
    assert exc.value.status_code == 404
    monkeypatch.setattr(
        _svc, "edit_comment", AsyncMock(side_effect=PermissionError("no")),
    )
    with pytest.raises(HTTPException) as exc:
        await _cc.edit_comment(
            comment_id=1, payload=payload,
            current_user=_user(), session=_ses(),
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_comment_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ses = _ses()
    monkeypatch.setattr(_svc, "delete_comment", AsyncMock())
    _act(monkeypatch)
    r = await _cc.delete_comment(
        comment_id=1, current_user=_user(), session=ses,
    )
    assert r == {"success": True}


@pytest.mark.asyncio
async def test_delete_comment_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        _svc, "delete_comment", AsyncMock(side_effect=ValueError("gone")),
    )
    with pytest.raises(HTTPException) as exc:
        await _cc.delete_comment(
            comment_id=99, current_user=_user(), session=_ses(),
        )
    assert exc.value.status_code == 404
    monkeypatch.setattr(
        _svc, "delete_comment", AsyncMock(side_effect=PermissionError("no")),
    )
    with pytest.raises(HTTPException) as exc:
        await _cc.delete_comment(
            comment_id=1, current_user=_user(), session=_ses(),
        )
    assert exc.value.status_code == 403


# -- collaboration_mentions routes --


@pytest.mark.asyncio
async def test_list_mentions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        _msvc, "list_mentions",
        AsyncMock(return_value=[_mention(), _mention(mid=2)]),
    )
    r = await _cm.list_mentions(
        unread_only=False, current_user=_user(), session=_ses(),
    )
    assert len(r.notifications) == 2
    assert r.notifications[0].message == "pinged"


@pytest.mark.asyncio
async def test_mark_mention_read(monkeypatch: pytest.MonkeyPatch) -> None:
    ses = _ses()
    monkeypatch.setattr(
        _msvc, "mark_mention_read", AsyncMock(return_value=True),
    )
    r = await _cm.mark_mention_read(
        mention_id=1, current_user=_user(), session=ses,
    )
    assert r == {"success": True}
    monkeypatch.setattr(
        _msvc, "mark_mention_read", AsyncMock(return_value=False),
    )
    with pytest.raises(HTTPException) as exc:
        await _cm.mark_mention_read(
            mention_id=99, current_user=_user(), session=_ses(),
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_team_activity_feed(monkeypatch: pytest.MonkeyPatch) -> None:
    entry = {
        "id": 1, "user_id": 1, "event_type": "comment.created",
        "resource_type": "comment", "resource_id": "42",
        "event_metadata": {}, "created_at": _NOW.isoformat(),
    }
    monkeypatch.setattr(
        _cm.team_activity_service,
        "get_feed", AsyncMock(return_value=[entry]),
    )
    r = await _cm.team_activity_feed(
        limit=50, current_user=_user(), session=_ses(),
    )
    assert len(r.entries) == 1
    assert r.entries[0].event_type == "comment.created"
