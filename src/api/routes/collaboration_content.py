"""API routes for annotations, comments, and comment threads."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_user
from src.api.schemas.collaboration_content import (
    AnnotationCreateRequest,
    AnnotationResponse,
    CommentCreateRequest,
    CommentResponse,
    CommentThreadCreateRequest,
    CommentThreadResponse,
    CommentUpdateRequest,
)
from src.database.connection import get_session
from src.models.collaboration_content import PatentCommentThread
from src.models.user import User
from src.services.activity_service import activity_service
from src.services.collaboration_content_service import collaboration_content_service

router = APIRouter()


def _comment_response(
    comment_id: int, thread_id: int, user_id: int, parent_comment_id: int | None,
    text: str, is_deleted: bool, edited_at: str | None, created_at: str | None,
) -> CommentResponse:
    return CommentResponse(
        id=comment_id, thread_id=thread_id, user_id=user_id,
        parent_comment_id=parent_comment_id, text=text, is_deleted=is_deleted,
        edited_at=edited_at, created_at=created_at,
    )


def _thread_response(thread: PatentCommentThread) -> CommentThreadResponse:
    comments = [
        _comment_response(
            comment_id=c.id, thread_id=c.thread_id, user_id=c.user_id,
            parent_comment_id=c.parent_comment_id, text=c.text,
            is_deleted=c.is_deleted,
            edited_at=c.edited_at.isoformat() if c.edited_at else None,
            created_at=c.created_at.isoformat() if c.created_at else None,
        )
        for c in thread.comments
    ]
    return CommentThreadResponse(
        id=thread.id, patent_id=thread.patent_id, project_id=thread.project_id,
        title=thread.title, created_by_user_id=thread.created_by_user_id,
        comments=comments,
        created_at=thread.created_at.isoformat() if thread.created_at else None,
    )


@router.post(
    "/patents/{patent_id}/annotations",
    response_model=AnnotationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_annotation(
    patent_id: int,
    payload: AnnotationCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AnnotationResponse:
    annotation = await collaboration_content_service.add_annotation(
        session, patent_id=patent_id, user_id=current_user.id, text=payload.text,
    )
    await activity_service.log_event(
        session, event_type="collaboration.annotation.created",
        user_id=current_user.id, resource_type="annotation",
        resource_id=str(annotation.id), event_metadata={"patent_id": patent_id},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    return AnnotationResponse(
        id=annotation.id, patent_id=annotation.patent_id, user_id=annotation.user_id,
        text=annotation.text,
        created_at=annotation.created_at.isoformat() if annotation.created_at else None,
        updated_at=annotation.updated_at.isoformat() if annotation.updated_at else None,
    )


@router.get("/patents/{patent_id}/annotations", response_model=list[AnnotationResponse])
async def list_annotations(
    patent_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[AnnotationResponse]:
    del current_user
    annotations = await collaboration_content_service.list_annotations(session, patent_id)
    return [
        AnnotationResponse(
            id=a.id, patent_id=a.patent_id, user_id=a.user_id, text=a.text,
            created_at=a.created_at.isoformat() if a.created_at else None,
            updated_at=a.updated_at.isoformat() if a.updated_at else None,
        )
        for a in annotations
    ]


@router.post(
    "/patents/{patent_id}/threads",
    response_model=CommentThreadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment_thread(
    patent_id: int,
    payload: CommentThreadCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CommentThreadResponse:
    try:
        thread = await collaboration_content_service.create_thread(
            session, patent_id=patent_id, user_id=current_user.id,
            title=payload.title, project_id=payload.project_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    await activity_service.log_event(
        session, event_type="collaboration.comment_thread.created",
        user_id=current_user.id, resource_type="comment_thread",
        resource_id=str(thread.id),
        event_metadata={"patent_id": patent_id, "project_id": payload.project_id},
    )
    await session.commit()
    return _thread_response(thread)


@router.get("/patents/{patent_id}/threads", response_model=list[CommentThreadResponse])
async def list_comment_threads(
    patent_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[CommentThreadResponse]:
    del current_user
    threads = await collaboration_content_service.list_threads(session, patent_id)
    return [_thread_response(thread) for thread in threads]


@router.post(
    "/threads/{thread_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    thread_id: int,
    payload: CommentCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CommentResponse:
    try:
        comment = await collaboration_content_service.add_comment(
            session, thread_id=thread_id, user_id=current_user.id,
            text=payload.text, parent_comment_id=payload.parent_comment_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await activity_service.log_event(
        session, event_type="collaboration.comment.created",
        user_id=current_user.id, resource_type="comment",
        resource_id=str(comment.id), event_metadata={"thread_id": thread_id},
    )
    await session.commit()
    return _comment_response(
        comment_id=comment.id, thread_id=comment.thread_id,
        user_id=comment.user_id, parent_comment_id=comment.parent_comment_id,
        text=comment.text, is_deleted=comment.is_deleted,
        edited_at=comment.edited_at.isoformat() if comment.edited_at else None,
        created_at=comment.created_at.isoformat() if comment.created_at else None,
    )


@router.patch("/comments/{comment_id}", response_model=CommentResponse)
async def edit_comment(
    comment_id: int,
    payload: CommentUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CommentResponse:
    try:
        comment = await collaboration_content_service.edit_comment(
            session, comment_id=comment_id, user_id=current_user.id, text=payload.text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    await activity_service.log_event(
        session, event_type="collaboration.comment.edited",
        user_id=current_user.id, resource_type="comment",
        resource_id=str(comment.id),
    )
    await session.commit()
    return _comment_response(
        comment_id=comment.id, thread_id=comment.thread_id,
        user_id=comment.user_id, parent_comment_id=comment.parent_comment_id,
        text=comment.text, is_deleted=comment.is_deleted,
        edited_at=comment.edited_at.isoformat() if comment.edited_at else None,
        created_at=comment.created_at.isoformat() if comment.created_at else None,
    )


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    try:
        await collaboration_content_service.delete_comment(
            session, comment_id=comment_id, user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    await activity_service.log_event(
        session, event_type="collaboration.comment.deleted",
        user_id=current_user.id, resource_type="comment",
        resource_id=str(comment_id),
    )
    await session.commit()
    return {"success": True}
