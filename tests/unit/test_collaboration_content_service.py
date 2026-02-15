"""Unit tests for collaborative content service."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.models.collaboration_content import MentionNotification, PatentComment, PatentCommentThread
from src.models.user import User
from src.services.collaboration_content_service import collaboration_content_service


class _Result:
    def __init__(self, scalar_value=None, rows=None):
        self._scalar_value = scalar_value
        self._rows = rows or []

    def scalar_one_or_none(self):
        return self._scalar_value

    def scalars(self):
        return SimpleNamespace(all=lambda: self._rows)


@pytest.mark.asyncio
async def test_add_comment_rejects_invalid_parent(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    thread = PatentCommentThread(id=5, patent_id=10, title="Discussion", created_by_user_id=1)
    monkeypatch.setattr(
        collaboration_content_service,
        "_load_thread",
        AsyncMock(return_value=thread),
    )
    session.execute.return_value = _Result(scalar_value=None)

    with pytest.raises(ValueError, match="Parent comment"):
        await collaboration_content_service.add_comment(
            session,
            thread_id=5,
            user_id=2,
            text="reply",
            parent_comment_id=99,
        )


@pytest.mark.asyncio
async def test_add_comment_creates_mentions(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = AsyncMock()
    thread = PatentCommentThread(id=1, patent_id=7, title="T", created_by_user_id=1)
    monkeypatch.setattr(
        collaboration_content_service,
        "_load_thread",
        AsyncMock(return_value=thread),
    )
    mentioned_user = User(
        id=11,
        email="mentioned@example.com",
        hashed_password="".join(["h", "x"]),
        role="viewer",
        is_active=True,
    )
    session.execute.return_value = _Result(rows=[mentioned_user])

    comment = await collaboration_content_service.add_comment(
        session,
        thread_id=1,
        user_id=1,
        text="Please review @mentioned@example.com",
    )

    assert comment.thread_id == 1
    assert session.add.call_count >= 2


@pytest.mark.asyncio
async def test_edit_and_delete_comment_enforces_author() -> None:
    session = AsyncMock()
    comment = PatentComment(id=9, thread_id=1, user_id=5, text="hello")
    session.execute.return_value = _Result(scalar_value=comment)
    session.flush = AsyncMock()

    with pytest.raises(PermissionError):
        await collaboration_content_service.edit_comment(session, comment_id=9, user_id=6, text="x")

    updated = await collaboration_content_service.edit_comment(
        session,
        comment_id=9,
        user_id=5,
        text="updated",
    )
    assert updated.text == "updated"

    deleted = await collaboration_content_service.delete_comment(
        session,
        comment_id=9,
        user_id=5,
    )
    assert deleted.is_deleted is True


@pytest.mark.asyncio
async def test_mark_mention_read_returns_false_when_missing() -> None:
    session = AsyncMock()
    session.execute.return_value = _Result(scalar_value=None)

    success = await collaboration_content_service.mark_mention_read(
        session,
        mention_id=4,
        user_id=1,
    )

    assert success is False


@pytest.mark.asyncio
async def test_list_mentions_returns_rows() -> None:
    session = AsyncMock()
    mention = MentionNotification(
        id=3,
        user_id=1,
        comment_id=10,
        message="mentioned",
        is_read=False,
    )
    session.execute.return_value = _Result(rows=[mention])

    rows = await collaboration_content_service.list_mentions(session, user_id=1, unread_only=True)
    assert len(rows) == 1
    assert rows[0].id == 3
