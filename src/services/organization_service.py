"""Organization and invite workflows."""

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.organization import Organization, OrganizationInvite, OrganizationMember
from src.models.user import User


class OrganizationService:
    """Creates organizations and manages invite-based membership."""

    async def create_organization(
        self,
        session: AsyncSession,
        owner_id: int,
        name: str,
    ) -> Organization:
        invite_code = await self._generate_unique_invite_code(session)
        organization = Organization(
            name=name.strip(),
            owner_id=owner_id,
            invite_code=invite_code,
        )
        session.add(organization)
        await session.flush()

        owner_member = OrganizationMember(
            organization_id=organization.id,
            user_id=owner_id,
            role="owner",
        )
        session.add(owner_member)
        await session.flush()
        await session.refresh(organization)
        return organization

    async def invite_user(
        self,
        session: AsyncSession,
        organization_id: int,
        invited_by_user_id: int,
        invited_email: str,
        note: str | None = None,
        expires_in_days: int = 7,
    ) -> OrganizationInvite:
        await self._verify_inviter_permissions(session, organization_id, invited_by_user_id)

        organization_result = await session.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        organization = organization_result.scalar_one_or_none()
        if organization is None:
            raise ValueError("Organization not found")

        invite = OrganizationInvite(
            organization_id=organization_id,
            invited_email=invited_email.strip().lower(),
            invited_by_user_id=invited_by_user_id,
            invite_token=secrets.token_urlsafe(32),
            invite_code=organization.invite_code,
            expires_at=datetime.now(UTC) + timedelta(days=expires_in_days),
            note=note,
        )
        session.add(invite)
        await session.flush()
        await session.refresh(invite)
        return invite

    async def accept_invite(
        self,
        session: AsyncSession,
        invite_token: str,
        user_id: int,
    ) -> OrganizationMember:
        invite_result = await session.execute(
            select(OrganizationInvite).where(
                and_(
                    OrganizationInvite.invite_token == invite_token,
                    OrganizationInvite.status == "pending",
                )
            )
        )
        invite = invite_result.scalar_one_or_none()
        if invite is None:
            raise ValueError("Invite not found")
        if invite.expires_at < datetime.now(UTC):
            raise ValueError("Invite has expired")

        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user is None:
            raise ValueError("User not found")
        if user.email.lower() != invite.invited_email.lower():
            raise ValueError("Invite email does not match authenticated user")

        membership_result = await session.execute(
            select(OrganizationMember).where(
                and_(
                    OrganizationMember.organization_id == invite.organization_id,
                    OrganizationMember.user_id == user_id,
                )
            )
        )
        membership = membership_result.scalar_one_or_none()
        if membership is None:
            membership = OrganizationMember(
                organization_id=invite.organization_id,
                user_id=user_id,
                role="member",
            )
            session.add(membership)
            await session.flush()

        invite.status = "accepted"
        invite.accepted_at = datetime.now(UTC)
        await session.flush()
        await session.refresh(membership)
        return membership

    async def _verify_inviter_permissions(
        self,
        session: AsyncSession,
        organization_id: int,
        invited_by_user_id: int,
    ) -> None:
        result = await session.execute(
            select(OrganizationMember).where(
                and_(
                    OrganizationMember.organization_id == organization_id,
                    OrganizationMember.user_id == invited_by_user_id,
                )
            )
        )
        membership = result.scalar_one_or_none()
        if membership is None or membership.role not in {"owner", "admin"}:
            raise PermissionError("Only owner or admin can invite collaborators")

    async def _generate_unique_invite_code(self, session: AsyncSession) -> str:
        for _ in range(10):
            candidate = secrets.token_urlsafe(12)
            existing = await session.execute(
                select(Organization.id).where(Organization.invite_code == candidate)
            )
            if existing.scalar_one_or_none() is None:
                return candidate
        raise RuntimeError("Could not generate unique invite code")


organization_service = OrganizationService()
