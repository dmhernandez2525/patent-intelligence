"""API routes for collaborative research projects."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_user
from src.api.schemas.collaboration_project import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectMemberRequest,
    ProjectMemberResponse,
    ProjectPatentRequest,
    ProjectPatentResponse,
    ProjectResponse,
    ProjectSearchPatentResponse,
    ProjectSearchRequest,
    ProjectSearchResponse,
    ProjectUpdateRequest,
)
from src.database.connection import get_session
from src.models.research_project import ResearchProject
from src.models.user import User
from src.services.activity_service import activity_service
from src.services.research_project_service import research_project_service

router = APIRouter()


def _to_project_response(project: ResearchProject) -> ProjectResponse:
    return ProjectResponse(
        id=project.id, name=project.name, description=project.description,
        status=project.status, owner_id=project.owner_id,
        members=[
            ProjectMemberResponse(user_id=m.user_id, permission=m.permission)
            for m in project.members
        ],
        patents=[
            ProjectPatentResponse(
                id=p.id, patent_number=p.patent_number,
                patent_id=p.patent_id, added_by_user_id=p.added_by_user_id,
            )
            for p in project.patents
        ],
    )


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProjectListResponse:
    projects = await research_project_service.list_for_user(session, current_user.id)
    return ProjectListResponse(projects=[_to_project_response(project) for project in projects])


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProjectResponse:
    project = await research_project_service.create_project(
        session,
        owner_id=current_user.id,
        name=payload.name,
        description=payload.description,
    )
    await activity_service.log_event(
        session,
        event_type="collaboration.project.created",
        user_id=current_user.id,
        resource_type="research_project",
        resource_id=str(project.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    project = await research_project_service.get_project(session, project.id, current_user.id)
    return _to_project_response(project)


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProjectResponse:
    try:
        project = await research_project_service.get_project(session, project_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    return _to_project_response(project)


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    payload: ProjectUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProjectResponse:
    try:
        project = await research_project_service.update_project(
            session,
            project_id=project_id,
            actor_user_id=current_user.id,
            name=payload.name,
            description=payload.description,
            status=payload.status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    await activity_service.log_event(
        session,
        event_type="collaboration.project.updated",
        user_id=current_user.id,
        resource_type="research_project",
        resource_id=str(project_id),
    )
    await session.commit()
    return _to_project_response(project)


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    try:
        await research_project_service.delete_project(session, project_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    await activity_service.log_event(
        session,
        event_type="collaboration.project.deleted",
        user_id=current_user.id,
        resource_type="research_project",
        resource_id=str(project_id),
    )
    await session.commit()
    return {"success": True}


@router.post("/projects/{project_id}/members", response_model=ProjectMemberResponse)
async def add_project_member(
    project_id: int,
    payload: ProjectMemberRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProjectMemberResponse:
    try:
        member = await research_project_service.add_member(
            session,
            project_id=project_id,
            actor_user_id=current_user.id,
            member_user_id=payload.user_id,
            permission=payload.permission,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    await activity_service.log_event(
        session,
        event_type="collaboration.project.member_added",
        user_id=current_user.id,
        resource_type="research_project",
        resource_id=str(project_id),
        event_metadata={"member_user_id": payload.user_id, "permission": payload.permission},
    )
    await session.commit()
    return ProjectMemberResponse(user_id=member.user_id, permission=member.permission)


@router.delete("/projects/{project_id}/members/{member_user_id}")
async def remove_project_member(
    project_id: int,
    member_user_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    try:
        success = await research_project_service.remove_member(
            session,
            project_id=project_id,
            actor_user_id=current_user.id,
            member_user_id=member_user_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")
    await activity_service.log_event(
        session,
        event_type="collaboration.project.member_removed",
        user_id=current_user.id,
        resource_type="research_project",
        resource_id=str(project_id),
        event_metadata={"member_user_id": member_user_id},
    )
    await session.commit()
    return {"success": True}


@router.post("/projects/{project_id}/patents", response_model=ProjectPatentResponse)
async def add_project_patent(
    project_id: int,
    payload: ProjectPatentRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProjectPatentResponse:
    try:
        item = await research_project_service.add_patent(
            session,
            project_id=project_id,
            actor_user_id=current_user.id,
            patent_number=payload.patent_number,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    await activity_service.log_event(
        session,
        event_type="collaboration.project.patent_added",
        user_id=current_user.id,
        resource_type="research_project",
        resource_id=str(project_id),
        event_metadata={"patent_number": item.patent_number},
    )
    await session.commit()
    return ProjectPatentResponse(
        id=item.id, patent_number=item.patent_number,
        patent_id=item.patent_id, added_by_user_id=item.added_by_user_id,
    )


@router.delete("/projects/{project_id}/patents/{patent_number}")
async def remove_project_patent(
    project_id: int,
    patent_number: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    try:
        success = await research_project_service.remove_patent(
            session, project_id, current_user.id, patent_number
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    if not success:
        raise HTTPException(status_code=404, detail="Patent not found in project")
    await activity_service.log_event(
        session,
        event_type="collaboration.project.patent_removed",
        user_id=current_user.id,
        resource_type="research_project",
        resource_id=str(project_id),
        event_metadata={"patent_number": patent_number},
    )
    await session.commit()
    return {"success": True}


@router.post("/projects/{project_id}/search", response_model=ProjectSearchResponse)
async def scoped_project_search(
    project_id: int,
    payload: ProjectSearchRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProjectSearchResponse:
    try:
        patents, total = await research_project_service.scoped_search(
            session,
            project_id=project_id,
            user_id=current_user.id,
            query=payload.query,
            page=payload.page,
            per_page=payload.per_page,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    return ProjectSearchResponse(
        patents=[ProjectSearchPatentResponse(**p) for p in patents],
        total=total, page=payload.page, per_page=payload.per_page,
    )
