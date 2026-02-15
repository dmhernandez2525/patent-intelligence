"""Research project collaboration service."""

from __future__ import annotations

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.patent import Patent
from src.models.research_project import (
    ProjectPermission,
    ResearchProject,
    ResearchProjectMember,
    ResearchProjectPatent,
)


class ResearchProjectService:
    """CRUD and scoped search for collaborative projects."""

    async def list_for_user(self, session: AsyncSession, user_id: int) -> list[ResearchProject]:
        query = (
            select(ResearchProject)
            .join(ResearchProjectMember)
            .where(ResearchProjectMember.user_id == user_id)
            .options(
                selectinload(ResearchProject.members),
                selectinload(ResearchProject.patents),
            )
            .order_by(ResearchProject.created_at.desc())
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    async def create_project(
        self,
        session: AsyncSession,
        owner_id: int,
        name: str,
        description: str | None,
    ) -> ResearchProject:
        project = ResearchProject(name=name, description=description, owner_id=owner_id)
        session.add(project)
        await session.flush()
        owner_member = ResearchProjectMember(
            project_id=project.id,
            user_id=owner_id,
            permission=ProjectPermission.OWNER.value,
        )
        session.add(owner_member)
        await session.flush()
        await session.refresh(project)
        return project

    async def get_project(self, session: AsyncSession, project_id: int, user_id: int) -> ResearchProject:
        project = await self._get_project(session, project_id)
        await self._require_permission(session, project_id, user_id, {"owner", "editor", "viewer"})
        return project

    async def update_project(
        self,
        session: AsyncSession,
        project_id: int,
        actor_user_id: int,
        name: str | None,
        description: str | None,
        status: str | None,
    ) -> ResearchProject:
        await self._require_permission(session, project_id, actor_user_id, {"owner", "editor"})
        project = await self._get_project(session, project_id)
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if status is not None:
            project.status = status
        await session.flush()
        return project

    async def delete_project(self, session: AsyncSession, project_id: int, actor_user_id: int) -> bool:
        await self._require_permission(session, project_id, actor_user_id, {"owner"})
        project = await self._get_project(session, project_id)
        await session.delete(project)
        return True

    async def add_member(
        self,
        session: AsyncSession,
        project_id: int,
        actor_user_id: int,
        member_user_id: int,
        permission: str,
    ) -> ResearchProjectMember:
        actor_permission = await self._require_permission(
            session, project_id, actor_user_id, {"owner", "editor"}
        )
        if permission not in {"editor", "viewer"}:
            raise ValueError("Member permission must be editor or viewer")
        if actor_permission == ProjectPermission.EDITOR.value and permission == "editor":
            raise PermissionError("Editors cannot promote other editors")

        result = await session.execute(
            select(ResearchProjectMember).where(
                and_(
                    ResearchProjectMember.project_id == project_id,
                    ResearchProjectMember.user_id == member_user_id,
                )
            )
        )
        member = result.scalar_one_or_none()
        if member is None:
            member = ResearchProjectMember(
                project_id=project_id,
                user_id=member_user_id,
                permission=permission,
            )
            session.add(member)
        else:
            member.permission = permission
        await session.flush()
        await session.refresh(member)
        return member

    async def remove_member(
        self,
        session: AsyncSession,
        project_id: int,
        actor_user_id: int,
        member_user_id: int,
    ) -> bool:
        actor_permission = await self._require_permission(
            session, project_id, actor_user_id, {"owner", "editor"}
        )
        target_result = await session.execute(
            select(ResearchProjectMember).where(
                and_(
                    ResearchProjectMember.project_id == project_id,
                    ResearchProjectMember.user_id == member_user_id,
                )
            )
        )
        target = target_result.scalar_one_or_none()
        if target is None:
            return False
        if target.permission == ProjectPermission.OWNER.value:
            raise PermissionError("Owner membership cannot be removed")
        if actor_permission == ProjectPermission.EDITOR.value and target.permission != "viewer":
            raise PermissionError("Editors can only remove viewer members")
        await session.delete(target)
        return True

    async def add_patent(
        self,
        session: AsyncSession,
        project_id: int,
        actor_user_id: int,
        patent_number: str,
    ) -> ResearchProjectPatent:
        await self._require_permission(session, project_id, actor_user_id, {"owner", "editor"})
        normalized_number = patent_number.strip().upper()
        existing = await session.execute(
            select(ResearchProjectPatent).where(
                and_(
                    ResearchProjectPatent.project_id == project_id,
                    ResearchProjectPatent.patent_number == normalized_number,
                )
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ValueError("Patent already exists in project")

        patent_result = await session.execute(
            select(Patent.id).where(Patent.patent_number == normalized_number)
        )
        patent_id = patent_result.scalar_one_or_none()
        item = ResearchProjectPatent(
            project_id=project_id,
            patent_id=patent_id,
            patent_number=normalized_number,
            added_by_user_id=actor_user_id,
        )
        session.add(item)
        await session.flush()
        await session.refresh(item)
        return item

    async def remove_patent(
        self,
        session: AsyncSession,
        project_id: int,
        actor_user_id: int,
        patent_number: str,
    ) -> bool:
        await self._require_permission(session, project_id, actor_user_id, {"owner", "editor"})
        normalized_number = patent_number.strip().upper()
        result = await session.execute(
            select(ResearchProjectPatent).where(
                and_(
                    ResearchProjectPatent.project_id == project_id,
                    ResearchProjectPatent.patent_number == normalized_number,
                )
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            return False
        await session.delete(item)
        return True

    async def scoped_search(
        self,
        session: AsyncSession,
        project_id: int,
        user_id: int,
        query: str,
        page: int,
        per_page: int,
    ) -> tuple[list[dict], int]:
        await self._require_permission(session, project_id, user_id, {"owner", "editor", "viewer"})
        offset = (page - 1) * per_page
        base_query = (
            select(Patent)
            .join(ResearchProjectPatent, ResearchProjectPatent.patent_id == Patent.id)
            .where(ResearchProjectPatent.project_id == project_id)
        )
        if query.strip():
            like_query = f"%{query.strip()}%"
            base_query = base_query.where(
                or_(
                    Patent.title.ilike(like_query),
                    Patent.abstract.ilike(like_query),
                    Patent.patent_number.ilike(like_query),
                )
            )

        count_query = select(func.count()).select_from(base_query.subquery())
        total = (await session.execute(count_query)).scalar() or 0

        result = await session.execute(
            base_query.order_by(Patent.filing_date.desc().nullslast()).offset(offset).limit(per_page)
        )
        patents = result.scalars().all()
        return [
            {
                "id": p.id,
                "patent_number": p.patent_number,
                "title": p.title,
                "status": p.status,
                "country": p.country,
                "filing_date": p.filing_date.isoformat() if p.filing_date else None,
            }
            for p in patents
        ], total

    async def _get_project(self, session: AsyncSession, project_id: int) -> ResearchProject:
        result = await session.execute(
            select(ResearchProject)
            .where(ResearchProject.id == project_id)
            .options(
                selectinload(ResearchProject.members),
                selectinload(ResearchProject.patents),
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise ValueError("Project not found")
        return project

    async def _require_permission(
        self,
        session: AsyncSession,
        project_id: int,
        user_id: int,
        allowed: set[str],
    ) -> str:
        result = await session.execute(
            select(ResearchProjectMember).where(
                and_(
                    ResearchProjectMember.project_id == project_id,
                    ResearchProjectMember.user_id == user_id,
                )
            )
        )
        member = result.scalar_one_or_none()
        if member is None or member.permission not in allowed:
            raise PermissionError("Insufficient project permission")
        return member.permission


research_project_service = ResearchProjectService()
