"""Additional tests for collaboration content service covering internal methods."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.collaboration_content import (
    CollaborativeAnnotation,
    MentionNotification,
    PatentCommentThread,
)
from src.models.research_project import ResearchProjectMember
from src.services.collaboration_content_service import CollaborationContentService


class _R:
    def __init__(self, val=None, rows=None):
        self._v = val
        self._rows = rows or []

    def scalar_one_or_none(self):
        return self._v

    def scalars(self):
        return SimpleNamespace(all=lambda: self._rows)


def _svc():
    return CollaborationContentService()


def _session():
    s = AsyncMock()
    s.add = MagicMock()
    s.flush = AsyncMock()
    s.refresh = AsyncMock()
    return s


@pytest.mark.asyncio
async def test_add_annotation_creates_and_returns():
    svc, s = _svc(), _session()
    result = await svc.add_annotation(s, patent_id=5, user_id=2, text="  Note  ")
    assert result.patent_id == 5
    assert result.text == "Note"
    s.add.assert_called_once()
    s.flush.assert_awaited_once()
    s.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_annotations_returns_results():
    svc, s = _svc(), AsyncMock()
    ann = CollaborativeAnnotation(id=1, patent_id=5, user_id=2, text="Test")
    ann.created_at = datetime.now(UTC)
    ann.updated_at = None
    s.execute.return_value = _R(rows=[ann])
    result = await svc.list_annotations(s, patent_id=5)
    assert len(result) == 1
    assert result[0].id == 1


@pytest.mark.asyncio
async def test_create_thread_without_project():
    svc, s = _svc(), _session()
    thread = await svc.create_thread(s, patent_id=10, user_id=3, title=" Thread A ")
    assert thread.patent_id == 10
    assert thread.title == "Thread A"
    assert thread.project_id is None
    s.add.assert_called_once()


@pytest.mark.asyncio
async def test_create_thread_with_project_membership():
    svc, s = _svc(), _session()
    member = ResearchProjectMember(project_id=7, user_id=3, permission="editor")
    s.execute.return_value = _R(val=member)
    thread = await svc.create_thread(
        s, patent_id=10, user_id=3, title="T", project_id=7,
    )
    assert thread.project_id == 7


@pytest.mark.asyncio
async def test_create_thread_project_no_membership():
    svc, s = _svc(), AsyncMock()
    s.execute.return_value = _R(val=None)
    with pytest.raises(PermissionError, match="membership required"):
        await svc.create_thread(s, patent_id=10, user_id=3, title="T", project_id=7)


@pytest.mark.asyncio
async def test_list_threads_returns_results():
    svc, s = _svc(), AsyncMock()
    t = PatentCommentThread(id=1, patent_id=5, title="T", created_by_user_id=1)
    t.comments = []
    t.created_at = datetime.now(UTC)
    s.execute.return_value = _R(rows=[t])
    result = await svc.list_threads(s, patent_id=5)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_mark_mention_read_success():
    svc, s = _svc(), AsyncMock()
    s.flush = AsyncMock()
    mention = MentionNotification(id=3, user_id=1, comment_id=5, message="m")
    mention.is_read = False
    mention.read_at = None
    s.execute.return_value = _R(val=mention)
    result = await svc.mark_mention_read(s, mention_id=3, user_id=1)
    assert result is True
    assert mention.is_read is True
    assert mention.read_at is not None


@pytest.mark.asyncio
async def test_load_thread_success():
    svc, s = _svc(), AsyncMock()
    thread = PatentCommentThread(id=5, patent_id=10, title="T", created_by_user_id=1)
    s.execute.return_value = _R(val=thread)
    result = await svc._load_thread(s, 5)
    assert result.id == 5


@pytest.mark.asyncio
async def test_load_thread_not_found():
    svc, s = _svc(), AsyncMock()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="thread not found"):
        await svc._load_thread(s, 999)


@pytest.mark.asyncio
async def test_load_comment_not_found():
    svc, s = _svc(), AsyncMock()
    s.execute.return_value = _R(val=None)
    with pytest.raises(ValueError, match="Comment not found"):
        await svc._load_comment(s, 999)


@pytest.mark.asyncio
async def test_delete_comment_non_author():
    """Covers the permission check line in delete_comment."""
    from src.models.collaboration_content import PatentComment

    svc, s = _svc(), AsyncMock()
    comment = PatentComment(id=9, thread_id=1, user_id=5, text="hello")
    s.execute.return_value = _R(val=comment)
    with pytest.raises(PermissionError, match="Only author"):
        await svc.delete_comment(s, comment_id=9, user_id=999)


@pytest.mark.asyncio
async def test_create_mentions_skips_self():
    """Covers the self-mention skip path."""
    svc, s = _svc(), _session()
    from src.models.collaboration_content import PatentComment
    from src.models.user import User

    comment = PatentComment(id=5, thread_id=1, user_id=1, text="cc @me@example.com")
    comment.id = 5
    me = User(
        id=1, email="me@example.com",
        hashed_password="".join(["h", "x"]), role="viewer", is_active=True,
    )
    s.execute.return_value = _R(rows=[me])
    await svc._create_mentions(s, comment, patent_id=10)
    s.add.assert_not_called()


@pytest.mark.asyncio
async def test_create_mentions_no_emails():
    """Covers early return when no @mentions in text."""
    svc, s = _svc(), _session()
    from src.models.collaboration_content import PatentComment

    comment = PatentComment(id=5, thread_id=1, user_id=1, text="No mentions here")
    await svc._create_mentions(s, comment, patent_id=10)
    s.add.assert_not_called()
