"""API routes for shared watchlist collaboration."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_user
from src.api.schemas.collaboration_shared import (
    InviteActionResponse,
    SharedWatchlistAddItemRequest,
    SharedWatchlistCreateRequest,
    SharedWatchlistInviteRequest,
    SharedWatchlistInviteResponse,
    SharedWatchlistItemResponse,
    SharedWatchlistListItemResponse,
    SharedWatchlistListResponse,
    SharedWatchlistMemberResponse,
    SharedWatchlistResponse,
)
from src.database.connection import get_session
from src.models.user import User
from src.services.activity_service import activity_service
from src.services.shared_watchlist_service import shared_watchlist_service

router = APIRouter()


@router.get("/watchlists", response_model=SharedWatchlistListResponse)
async def list_shared_watchlists(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SharedWatchlistListResponse:
    watchlists = await shared_watchlist_service.list_for_user(session, current_user.id)
    return SharedWatchlistListResponse(
        watchlists=[SharedWatchlistListItemResponse(**watchlist) for watchlist in watchlists]
    )


@router.post(
    "/watchlists",
    response_model=SharedWatchlistResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_shared_watchlist(
    payload: SharedWatchlistCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SharedWatchlistResponse:
    watchlist = await shared_watchlist_service.create_watchlist(
        session,
        owner_id=current_user.id,
        name=payload.name,
        description=payload.description,
    )
    await activity_service.log_event(
        session,
        event_type="collaboration.watchlist.created",
        user_id=current_user.id,
        resource_type="shared_watchlist",
        resource_id=str(watchlist.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    return SharedWatchlistResponse(
        id=watchlist.id,
        name=watchlist.name,
        description=watchlist.description,
        owner_id=watchlist.owner_id,
        members=[SharedWatchlistMemberResponse(user_id=current_user.id, permission="owner")],
        items=[],
    )


@router.get("/watchlists/{watchlist_id}", response_model=SharedWatchlistResponse)
async def get_shared_watchlist(
    watchlist_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SharedWatchlistResponse:
    try:
        watchlist = await shared_watchlist_service.get_watchlist(session, watchlist_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    return SharedWatchlistResponse(
        id=watchlist.id,
        name=watchlist.name,
        description=watchlist.description,
        owner_id=watchlist.owner_id,
        members=[
            SharedWatchlistMemberResponse(user_id=member.user_id, permission=member.permission)
            for member in watchlist.members
        ],
        items=[
            SharedWatchlistItemResponse(
                id=item.id,
                item_type=item.item_type,
                item_value=item.item_value,
                patent_id=item.patent_id,
                added_by_user_id=item.added_by_user_id,
            )
            for item in watchlist.items
        ],
    )


@router.post("/watchlists/{watchlist_id}/items", response_model=SharedWatchlistItemResponse)
async def add_shared_watchlist_item(
    watchlist_id: int,
    payload: SharedWatchlistAddItemRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SharedWatchlistItemResponse:
    try:
        item = await shared_watchlist_service.add_item(
            session,
            watchlist_id=watchlist_id,
            actor_user_id=current_user.id,
            item_type=payload.item_type,
            item_value=payload.item_value,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    await activity_service.log_event(
        session,
        event_type="collaboration.watchlist.item_added",
        user_id=current_user.id,
        resource_type="shared_watchlist_item",
        resource_id=str(item.id),
        event_metadata={"watchlist_id": watchlist_id},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    return SharedWatchlistItemResponse(
        id=item.id,
        item_type=item.item_type,
        item_value=item.item_value,
        patent_id=item.patent_id,
        added_by_user_id=item.added_by_user_id,
    )


@router.post("/watchlists/{watchlist_id}/invites", response_model=SharedWatchlistInviteResponse)
async def invite_watchlist_collaborator(
    watchlist_id: int,
    payload: SharedWatchlistInviteRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SharedWatchlistInviteResponse:
    try:
        invite = await shared_watchlist_service.invite_collaborator(
            session,
            watchlist_id=watchlist_id,
            actor_user_id=current_user.id,
            invited_email=payload.email,
            permission=payload.permission,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    await activity_service.log_event(
        session,
        event_type="collaboration.watchlist.invited",
        user_id=current_user.id,
        resource_type="shared_watchlist_invite",
        resource_id=str(invite.id),
        event_metadata={"watchlist_id": watchlist_id, "invited_email": invite.invited_email},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    return SharedWatchlistInviteResponse(
        id=invite.id,
        invited_email=invite.invited_email,
        permission=invite.permission,
        invite_token=invite.invite_token,
        status=invite.status,
        expires_at=invite.expires_at.isoformat(),
    )


@router.post("/watchlists/invites/{invite_token}/accept", response_model=InviteActionResponse)
async def accept_watchlist_invite(
    invite_token: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InviteActionResponse:
    try:
        await shared_watchlist_service.accept_invite(session, invite_token, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    await activity_service.log_event(
        session,
        event_type="collaboration.watchlist.invite_accepted",
        user_id=current_user.id,
        resource_type="shared_watchlist_invite",
        resource_id=invite_token,
    )
    await session.commit()
    return InviteActionResponse(success=True, status="accepted")


@router.post("/watchlists/invites/{invite_token}/decline", response_model=InviteActionResponse)
async def decline_watchlist_invite(
    invite_token: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InviteActionResponse:
    try:
        await shared_watchlist_service.decline_invite(session, invite_token, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    await activity_service.log_event(
        session,
        event_type="collaboration.watchlist.invite_declined",
        user_id=current_user.id,
        resource_type="shared_watchlist_invite",
        resource_id=invite_token,
    )
    await session.commit()
    return InviteActionResponse(success=True, status="declined")


@router.delete("/watchlists/{watchlist_id}/members/{member_user_id}", response_model=InviteActionResponse)
async def revoke_watchlist_member(
    watchlist_id: int,
    member_user_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InviteActionResponse:
    try:
        success = await shared_watchlist_service.revoke_member(
            session, watchlist_id, current_user.id, member_user_id
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")
    await activity_service.log_event(
        session,
        event_type="collaboration.watchlist.member_revoked",
        user_id=current_user.id,
        resource_type="shared_watchlist",
        resource_id=str(watchlist_id),
        event_metadata={"member_user_id": member_user_id},
    )
    await session.commit()
    return InviteActionResponse(success=True, status="revoked")


@router.post("/watchlists/invites/{invite_id}/revoke", response_model=InviteActionResponse)
async def revoke_watchlist_invite(
    invite_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InviteActionResponse:
    try:
        await shared_watchlist_service.revoke_invite(session, invite_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    await activity_service.log_event(
        session,
        event_type="collaboration.watchlist.invite_revoked",
        user_id=current_user.id,
        resource_type="shared_watchlist_invite",
        resource_id=str(invite_id),
    )
    await session.commit()
    return InviteActionResponse(success=True, status="revoked")
