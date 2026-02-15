"""Shared watchlist collaboration service."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.collaboration_watchlist import (
    SharedPermission,
    SharedWatchlist,
    SharedWatchlistInvite,
    SharedWatchlistItem,
    SharedWatchlistMember,
)
from src.models.patent import Patent
from src.models.user import User


class SharedWatchlistService:
    """Manage shared watchlists and collaborator lifecycle."""

    async def list_for_user(self, session: AsyncSession, user_id: int) -> list[dict]:
        query = (
            select(SharedWatchlist)
            .join(SharedWatchlistMember)
            .where(SharedWatchlistMember.user_id == user_id)
            .options(selectinload(SharedWatchlist.items), selectinload(SharedWatchlist.members))
            .order_by(SharedWatchlist.created_at.desc())
        )
        result = await session.execute(query)
        watchlists = result.scalars().all()
        return [self._to_watchlist_dict(w) for w in watchlists]

    async def create_watchlist(
        self,
        session: AsyncSession,
        owner_id: int,
        name: str,
        description: str | None = None,
    ) -> SharedWatchlist:
        watchlist = SharedWatchlist(name=name, description=description, owner_id=owner_id)
        session.add(watchlist)
        await session.flush()

        owner_member = SharedWatchlistMember(
            watchlist_id=watchlist.id,
            user_id=owner_id,
            permission=SharedPermission.OWNER.value,
        )
        session.add(owner_member)
        await session.flush()
        await session.refresh(watchlist)
        return watchlist

    async def get_watchlist(
        self, session: AsyncSession, watchlist_id: int, user_id: int
    ) -> SharedWatchlist:
        watchlist = await self._get_watchlist(session, watchlist_id)
        await self._require_permission(session, watchlist_id, user_id, {"owner", "editor", "viewer"})
        return watchlist

    async def add_item(
        self,
        session: AsyncSession,
        watchlist_id: int,
        actor_user_id: int,
        item_type: str,
        item_value: str,
    ) -> SharedWatchlistItem:
        await self._require_permission(session, watchlist_id, actor_user_id, {"owner", "editor"})
        normalized_value = item_value.strip()
        existing = await session.execute(
            select(SharedWatchlistItem).where(
                and_(
                    SharedWatchlistItem.watchlist_id == watchlist_id,
                    SharedWatchlistItem.item_type == item_type,
                    SharedWatchlistItem.item_value == normalized_value,
                )
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ValueError("Item already exists in shared watchlist")

        patent_id: int | None = None
        if item_type == "patent":
            patent_result = await session.execute(
                select(Patent.id).where(Patent.patent_number == normalized_value)
            )
            patent_id = patent_result.scalar_one_or_none()

        item = SharedWatchlistItem(
            watchlist_id=watchlist_id,
            item_type=item_type,
            item_value=normalized_value,
            patent_id=patent_id,
            added_by_user_id=actor_user_id,
        )
        session.add(item)
        await session.flush()
        await session.refresh(item)
        return item

    async def invite_collaborator(
        self,
        session: AsyncSession,
        watchlist_id: int,
        actor_user_id: int,
        invited_email: str,
        permission: str,
    ) -> SharedWatchlistInvite:
        await self._require_permission(session, watchlist_id, actor_user_id, {"owner", "editor"})
        if permission not in {"editor", "viewer"}:
            raise ValueError("Invite permission must be editor or viewer")

        token = secrets.token_urlsafe(24)
        invite = SharedWatchlistInvite(
            watchlist_id=watchlist_id,
            invited_email=invited_email.strip().lower(),
            invited_by_user_id=actor_user_id,
            permission=permission,
            invite_token=token,
            status="pending",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        session.add(invite)
        await session.flush()
        await session.refresh(invite)
        return invite

    async def accept_invite(
        self, session: AsyncSession, invite_token: str, current_user_id: int
    ) -> SharedWatchlistMember:
        invite = await self._load_invite(session, invite_token)
        user = await self._load_user(session, current_user_id)
        if invite.invited_email != user.email.lower():
            raise PermissionError("Invite email does not match authenticated user")
        if invite.status != "pending":
            raise ValueError("Invite is no longer pending")
        if invite.expires_at < datetime.now(UTC):
            raise ValueError("Invite has expired")

        existing = await session.execute(
            select(SharedWatchlistMember).where(
                and_(
                    SharedWatchlistMember.watchlist_id == invite.watchlist_id,
                    SharedWatchlistMember.user_id == current_user_id,
                )
            )
        )
        member = existing.scalar_one_or_none()
        if member is None:
            member = SharedWatchlistMember(
                watchlist_id=invite.watchlist_id,
                user_id=current_user_id,
                permission=invite.permission,
            )
            session.add(member)
        else:
            member.permission = invite.permission

        invite.status = "accepted"
        invite.responded_at = datetime.now(UTC)
        await session.flush()
        await session.refresh(member)
        return member

    async def decline_invite(
        self, session: AsyncSession, invite_token: str, current_user_id: int
    ) -> SharedWatchlistInvite:
        invite = await self._load_invite(session, invite_token)
        user = await self._load_user(session, current_user_id)
        if invite.invited_email != user.email.lower():
            raise PermissionError("Invite email does not match authenticated user")
        if invite.status != "pending":
            raise ValueError("Invite is no longer pending")
        invite.status = "declined"
        invite.responded_at = datetime.now(UTC)
        await session.flush()
        return invite

    async def revoke_member(
        self,
        session: AsyncSession,
        watchlist_id: int,
        actor_user_id: int,
        target_user_id: int,
    ) -> bool:
        actor_permission = await self._require_permission(
            session, watchlist_id, actor_user_id, {"owner", "editor"}
        )
        target = await session.execute(
            select(SharedWatchlistMember).where(
                and_(
                    SharedWatchlistMember.watchlist_id == watchlist_id,
                    SharedWatchlistMember.user_id == target_user_id,
                )
            )
        )
        target_member = target.scalar_one_or_none()
        if target_member is None:
            return False
        if target_member.permission == SharedPermission.OWNER.value:
            raise PermissionError("Owner membership cannot be revoked")
        if actor_permission == SharedPermission.EDITOR.value and target_member.permission != "viewer":
            raise PermissionError("Editors can only revoke viewer memberships")

        await session.delete(target_member)
        return True

    async def revoke_invite(
        self, session: AsyncSession, invite_id: int, actor_user_id: int
    ) -> SharedWatchlistInvite:
        invite_result = await session.execute(
            select(SharedWatchlistInvite).where(SharedWatchlistInvite.id == invite_id)
        )
        invite = invite_result.scalar_one_or_none()
        if invite is None:
            raise ValueError("Invite not found")
        await self._require_permission(session, invite.watchlist_id, actor_user_id, {"owner", "editor"})
        invite.status = "revoked"
        invite.responded_at = datetime.now(UTC)
        await session.flush()
        return invite

    async def _get_watchlist(self, session: AsyncSession, watchlist_id: int) -> SharedWatchlist:
        result = await session.execute(
            select(SharedWatchlist)
            .where(SharedWatchlist.id == watchlist_id)
            .options(
                selectinload(SharedWatchlist.items),
                selectinload(SharedWatchlist.members),
                selectinload(SharedWatchlist.invites),
            )
        )
        watchlist = result.scalar_one_or_none()
        if watchlist is None:
            raise ValueError("Shared watchlist not found")
        return watchlist

    async def _load_invite(self, session: AsyncSession, invite_token: str) -> SharedWatchlistInvite:
        result = await session.execute(
            select(SharedWatchlistInvite).where(SharedWatchlistInvite.invite_token == invite_token)
        )
        invite = result.scalar_one_or_none()
        if invite is None:
            raise ValueError("Invite not found")
        return invite

    async def _load_user(self, session: AsyncSession, user_id: int) -> User:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError("User not found")
        return user

    async def _require_permission(
        self,
        session: AsyncSession,
        watchlist_id: int,
        user_id: int,
        allowed: set[str],
    ) -> str:
        member_result = await session.execute(
            select(SharedWatchlistMember).where(
                and_(
                    SharedWatchlistMember.watchlist_id == watchlist_id,
                    SharedWatchlistMember.user_id == user_id,
                )
            )
        )
        member = member_result.scalar_one_or_none()
        if member is None or member.permission not in allowed:
            raise PermissionError("Insufficient watchlist permission")
        return member.permission

    def _to_watchlist_dict(self, watchlist: SharedWatchlist) -> dict:
        return {
            "id": watchlist.id,
            "name": watchlist.name,
            "description": watchlist.description,
            "owner_id": watchlist.owner_id,
            "member_count": len(watchlist.members),
            "item_count": len(watchlist.items),
            "created_at": watchlist.created_at.isoformat() if watchlist.created_at else None,
        }


shared_watchlist_service = SharedWatchlistService()
