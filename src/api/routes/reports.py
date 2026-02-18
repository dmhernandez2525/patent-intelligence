"""API routes for research report management."""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_user
from src.api.schemas.report import (
    ReportCreateRequest,
    ReportListResponse,
    ReportResponse,
    ScheduleCreateRequest,
    ScheduleListResponse,
    ScheduleResponse,
    TemplateListResponse,
    TemplateResponse,
)
from src.database.connection import get_session
from src.models.user import User
from src.services.activity_service import activity_service
from src.services.report_service import report_service

router = APIRouter()


def _report_response(r) -> ReportResponse:
    return ReportResponse(
        id=r.id, user_id=r.user_id, project_id=r.project_id,
        title=r.title, report_type=r.report_type,
        output_format=r.output_format, status=r.status,
        config=r.config, file_size=r.file_size,
        page_count=r.page_count, error_message=r.error_message,
        generated_at=r.generated_at.isoformat() if r.generated_at else None,
        created_at=r.created_at.isoformat() if r.created_at else None,
    )


def _schedule_response(s) -> ScheduleResponse:
    return ScheduleResponse(
        id=s.id, report_type=s.report_type,
        output_format=s.output_format, project_id=s.project_id,
        config=s.config, frequency=s.frequency,
        next_run_at=s.next_run_at.isoformat() if s.next_run_at else None,
        is_active=s.is_active,
    )


def _template_response(t) -> TemplateResponse:
    return TemplateResponse(
        id=t.id, name=t.name, report_type=t.report_type,
        description=t.description, template_config=t.template_config,
        is_default=t.is_default, is_system=t.is_system,
    )


# ---- Reports ----

@router.get("", response_model=ReportListResponse)
async def list_reports(
    project_id: int | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ReportListResponse:
    """List research reports for the current user."""
    reports = await report_service.list_reports(
        session, user_id=current_user.id,
        project_id=project_id, status=status_filter,
    )
    return ReportListResponse(
        reports=[_report_response(r) for r in reports],
        total=len(reports),
    )


@router.post(
    "", response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_report(
    payload: ReportCreateRequest, request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ReportResponse:
    """Create a new research report."""
    report = await report_service.create_report(
        session, user_id=current_user.id, title=payload.title,
        report_type=payload.report_type,
        output_format=payload.output_format,
        project_id=payload.project_id, config=payload.config,
    )
    await activity_service.log_event(
        session, event_type="report.created",
        user_id=current_user.id, resource_type="report",
        resource_id=str(report.id),
        event_metadata={
            "title": payload.title, "report_type": payload.report_type,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    return _report_response(report)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ReportResponse:
    """Get a single research report by ID."""
    try:
        report = await report_service.get_report(
            session, report_id=report_id, user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _report_response(report)


@router.post("/{report_id}/generate", response_model=ReportResponse)
async def generate_report(
    report_id: int, request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ReportResponse:
    """Trigger generation for a research report."""
    try:
        report = await report_service.generate_report(
            session, report_id=report_id, user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await activity_service.log_event(
        session, event_type="report.generated",
        user_id=current_user.id, resource_type="report",
        resource_id=str(report_id),
        event_metadata={"report_type": report.report_type},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    return _report_response(report)


@router.delete("/{report_id}")
async def delete_report(
    report_id: int, request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    """Delete a research report."""
    try:
        await report_service.delete_report(
            session, report_id=report_id, user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await activity_service.log_event(
        session, event_type="report.deleted",
        user_id=current_user.id, resource_type="report",
        resource_id=str(report_id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    return {"success": True}


# ---- Templates ----

@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    report_type: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TemplateListResponse:
    """List available report templates."""
    templates = await report_service.list_templates(
        session, report_type=report_type,
    )
    return TemplateListResponse(
        templates=[_template_response(t) for t in templates],
    )


# ---- Schedules ----

@router.post(
    "/schedules", response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule(
    payload: ScheduleCreateRequest, request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ScheduleResponse:
    """Create a new report generation schedule."""
    schedule = await report_service.create_schedule(
        session, user_id=current_user.id,
        report_type=payload.report_type,
        output_format=payload.output_format,
        project_id=payload.project_id,
        config=payload.config, frequency=payload.frequency,
    )
    await activity_service.log_event(
        session, event_type="report.schedule.created",
        user_id=current_user.id, resource_type="report_schedule",
        resource_id=str(schedule.id),
        event_metadata={
            "report_type": payload.report_type,
            "frequency": payload.frequency,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    return _schedule_response(schedule)


@router.get("/schedules", response_model=ScheduleListResponse)
async def list_schedules(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ScheduleListResponse:
    """List report generation schedules for the current user."""
    schedules = await report_service.list_schedules(
        session, user_id=current_user.id,
    )
    return ScheduleListResponse(
        schedules=[_schedule_response(s) for s in schedules],
    )


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: int, request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    """Delete a report generation schedule."""
    try:
        await report_service.delete_schedule(
            session, schedule_id=schedule_id, user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await activity_service.log_event(
        session, event_type="report.schedule.deleted",
        user_id=current_user.id, resource_type="report_schedule",
        resource_id=str(schedule_id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    return {"success": True}
