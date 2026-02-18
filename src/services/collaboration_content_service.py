"""Collaborative annotations, comments, and mention notifications."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.collaboration_content import (
    CollaborativeAnnotation,
    MentionNotification,
    PatentComment,
    PatentCommentThread,
)
from src.models.research_project import ResearchProjectMember
from src.models.user import User

_MENTION_PATTERN = re.compile(r"@([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")


class CollaborationContentService:
    """Create and manage collaborative content artifacts."""

    async def add_annotation(
        self,
        session: AsyncSession,
        patent_id: int,
        user_id: int,
        text: str,
    ) -> CollaborativeAnnotation:
        annotation = CollaborativeAnnotation(patent_id=patent_id, user_id=user_id, text=text.strip())
        session.add(annotation)
        await session.flush()
        await session.refresh(annotation)
        return annotation

    async def list_annotations(
        self,
        session: AsyncSession,
        patent_id: int,
    ) -> list[CollaborativeAnnotation]:
        result = await session.execute(
            select(CollaborativeAnnotation)
            .where(CollaborativeAnnotation.patent_id == patent_id)
            .order_by(CollaborativeAnnotation.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_thread(
        self,
        session: AsyncSession,
        patent_id: int,
        user_id: int,
        title: str,
        project_id: int | None = None,
    ) -> PatentCommentThread:
        if project_id is not None:
            membership = await session.execute(
                select(ResearchProjectMember).where(
                    and_(
                        ResearchProjectMember.project_id == project_id,
                        ResearchProjectMember.user_id == user_id,
                    )
                )
            )
            if membership.scalar_one_or_none() is None:
                raise PermissionError("Project membership required for project thread")

        thread = PatentCommentThread(
            patent_id=patent_id,
            title=title.strip(),
            created_by_user_id=user_id,
            project_id=project_id,
        )
        session.add(thread)
        await session.flush()
        await session.refresh(thread)
        return thread

    async def list_threads(
        self,
        session: AsyncSession,
        patent_id: int,
    ) -> list[PatentCommentThread]:
        result = await session.execute(
            select(PatentCommentThread)
            .where(PatentCommentThread.patent_id == patent_id)
            .options(selectinload(PatentCommentThread.comments))
            .order_by(PatentCommentThread.created_at.desc())
        )
        return list(result.scalars().all())

    async def add_comment(
        self,
        session: AsyncSession,
        thread_id: int,
        user_id: int,
        text: str,
        parent_comment_id: int | None = None,
    ) -> PatentComment:
        thread = await self._load_thread(session, thread_id)
        if parent_comment_id is not None:
            parent_result = await session.execute(
                select(PatentComment).where(PatentComment.id == parent_comment_id)
            )
            parent = parent_result.scalar_one_or_none()
            if parent is None or parent.thread_id != thread_id:
                raise ValueError("Parent comment does not belong to this thread")

        comment = PatentComment(
            thread_id=thread.id,
            user_id=user_id,
            parent_comment_id=parent_comment_id,
            text=text.strip(),
        )
        session.add(comment)
        await session.flush()
        await self._create_mentions(session, comment, thread.patent_id)
        await session.refresh(comment)
        return comment

    async def edit_comment(
        self,
        session: AsyncSession,
        comment_id: int,
        user_id: int,
        text: str,
    ) -> PatentComment:
        comment = await self._load_comment(session, comment_id)
        if comment.user_id != user_id:
            raise PermissionError("Only author can edit comment")
        comment.text = text.strip()
        comment.edited_at = datetime.now(UTC)
        await session.flush()
        return comment

    async def delete_comment(self, session: AsyncSession, comment_id: int, user_id: int) -> PatentComment:
        comment = await self._load_comment(session, comment_id)
        if comment.user_id != user_id:
            raise PermissionError("Only author can delete comment")
        comment.is_deleted = True
        comment.text = "[deleted]"
        comment.edited_at = datetime.now(UTC)
        await session.flush()
        return comment

    async def list_mentions(
        self,
        session: AsyncSession,
        user_id: int,
        unread_only: bool,
    ) -> list[MentionNotification]:
        query = select(MentionNotification).where(MentionNotification.user_id == user_id)
        if unread_only:
            query = query.where(MentionNotification.is_read == False)
        query = query.order_by(MentionNotification.created_at.desc())
        result = await session.execute(query)
        return list(result.scalars().all())

    async def mark_mention_read(
        self,
        session: AsyncSession,
        mention_id: int,
        user_id: int,
    ) -> bool:
        result = await session.execute(
            select(MentionNotification).where(
                and_(
                    MentionNotification.id == mention_id,
                    MentionNotification.user_id == user_id,
                )
            )
        )
        mention = result.scalar_one_or_none()
        if mention is None:
            return False
        mention.is_read = True
        mention.read_at = datetime.now(UTC)
        await session.flush()
        return True

    async def _create_mentions(
        self,
        session: AsyncSession,
        comment: PatentComment,
        patent_id: int,
    ) -> None:
        emails = {match.group(1).lower() for match in _MENTION_PATTERN.finditer(comment.text)}
        if not emails:
            return
        users_result = await session.execute(select(User).where(User.email.in_(emails)))
        users = users_result.scalars().all()
        for user in users:
            if user.id == comment.user_id:
                continue
            mention = MentionNotification(
                user_id=user.id,
                comment_id=comment.id,
                message=f"You were mentioned in a comment on patent {patent_id}",
            )
            session.add(mention)

    async def _load_thread(self, session: AsyncSession, thread_id: int) -> PatentCommentThread:
        result = await session.execute(
            select(PatentCommentThread).where(PatentCommentThread.id == thread_id)
        )
        thread = result.scalar_one_or_none()
        if thread is None:
            raise ValueError("Comment thread not found")
        return thread

    async def _load_comment(self, session: AsyncSession, comment_id: int) -> PatentComment:
        result = await session.execute(select(PatentComment).where(PatentComment.id == comment_id))
        comment = result.scalar_one_or_none()
        if comment is None:
            raise ValueError("Comment not found")
        return comment


collaboration_content_service = CollaborationContentService()
