"""Research report generation and scheduling service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.report import ReportSchedule, ReportTemplate, ResearchReport

logger = structlog.get_logger(__name__)
_STUB_DIR = "/reports/generated"


class ReportService:
    """Manage research report lifecycle, templates, and schedules."""

    async def list_reports(
        self, session: AsyncSession, user_id: int,
        project_id: int | None = None,
        status: str | None = None,
    ) -> list[ResearchReport]:
        stmt = select(ResearchReport).where(
            ResearchReport.user_id == user_id)
        if project_id is not None:
            stmt = stmt.where(
                ResearchReport.project_id == project_id)
        if status is not None:
            stmt = stmt.where(ResearchReport.status == status)
        stmt = stmt.order_by(ResearchReport.created_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_report(
        self, session: AsyncSession,
        report_id: int, user_id: int,
    ) -> ResearchReport:
        return await self._get_user_report(
            session, report_id, user_id)

    async def create_report(
        self, session: AsyncSession, user_id: int,
        title: str, report_type: str,
        output_format: str = "pdf",
        project_id: int | None = None,
        config: dict | None = None,
    ) -> ResearchReport:
        report = ResearchReport(
            user_id=user_id, title=title,
            report_type=report_type,
            output_format=output_format,
            project_id=project_id,
            config=config or {}, status="pending")
        session.add(report)
        await session.flush()
        await session.refresh(report)
        return report

    async def generate_report(
        self, session: AsyncSession,
        report_id: int, user_id: int,
    ) -> ResearchReport:
        report = await self._get_user_report(
            session, report_id, user_id)
        report.status = "generating"
        await session.flush()
        generators = {
            "landscape": self._generate_landscape,
            "competitive": self._generate_competitive,
            "expiration": self._generate_expiration,
            "patent_analysis": self._generate_patent_analysis,
        }
        gen = generators.get(
            report.report_type, self._generate_custom)
        try:
            result = await gen(report.config, report.project_id)
            report.status = "completed"
            report.file_path = result["file_path"]
            report.file_size = result["file_size"]
            report.page_count = result["page_count"]
            report.generated_at = datetime.now(UTC)
        except Exception as exc:
            report.status = "failed"
            report.error_message = str(exc)
            logger.error("report_generation_failed",
                         report_id=report_id, error=str(exc))
        await session.flush()
        await session.refresh(report)
        return report

    async def delete_report(
        self, session: AsyncSession,
        report_id: int, user_id: int,
    ) -> bool:
        report = await self._get_user_report(
            session, report_id, user_id)
        await session.delete(report)
        return True

    async def list_templates(
        self, session: AsyncSession,
        report_type: str | None = None,
    ) -> list[ReportTemplate]:
        stmt = select(ReportTemplate)
        if report_type is not None:
            stmt = stmt.where(
                ReportTemplate.report_type == report_type)
        stmt = stmt.order_by(ReportTemplate.name)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_template(
        self, session: AsyncSession, template_id: int,
    ) -> ReportTemplate:
        result = await session.execute(
            select(ReportTemplate).where(
                ReportTemplate.id == template_id))
        tmpl = result.scalar_one_or_none()
        if tmpl is None:
            raise ValueError("Report template not found")
        return tmpl

    async def create_schedule(
        self, session: AsyncSession, user_id: int,
        report_type: str, output_format: str = "pdf",
        project_id: int | None = None,
        config: dict | None = None,
        frequency: str = "weekly",
        next_run_at: datetime | None = None,
    ) -> ReportSchedule:
        schedule = ReportSchedule(
            user_id=user_id, report_type=report_type,
            output_format=output_format,
            project_id=project_id,
            config=config or {},
            frequency=frequency, is_active=True,
            next_run_at=next_run_at or datetime.now(UTC))
        session.add(schedule)
        await session.flush()
        await session.refresh(schedule)
        return schedule

    async def list_schedules(
        self, session: AsyncSession, user_id: int,
    ) -> list[ReportSchedule]:
        result = await session.execute(
            select(ReportSchedule)
            .where(ReportSchedule.user_id == user_id)
            .order_by(ReportSchedule.id))
        return list(result.scalars().all())

    async def delete_schedule(
        self, session: AsyncSession,
        schedule_id: int, user_id: int,
    ) -> bool:
        s = await self._get_user_schedule(
            session, schedule_id, user_id)
        await session.delete(s)
        return True

    async def process_due_schedules(
        self, session: AsyncSession,
    ) -> int:
        now = datetime.now(UTC)
        result = await session.execute(
            select(ReportSchedule).where(and_(
                ReportSchedule.is_active.is_(True),
                ReportSchedule.next_run_at <= now)))
        schedules = list(result.scalars().all())
        processed = 0
        for schedule in schedules:
            report = ResearchReport(
                user_id=schedule.user_id,
                title=f"Scheduled {schedule.report_type} report",
                report_type=schedule.report_type,
                output_format=schedule.output_format,
                project_id=schedule.project_id,
                config=schedule.config or {},
                status="pending")
            session.add(report)
            self._advance_next_run(schedule)
            processed += 1
        await session.flush()
        logger.info("due_schedules_processed", count=processed)
        return processed

    # -- Generation stubs ------------------------------------------

    async def _generate_landscape(
        self, config: dict | None, project_id: int | None,
    ) -> dict:
        logger.info("generate_landscape",
                     project_id=project_id)
        return {"file_path": f"{_STUB_DIR}/landscape.pdf",
                "file_size": 0, "page_count": 0}

    async def _generate_competitive(
        self, config: dict | None, project_id: int | None,
    ) -> dict:
        logger.info("generate_competitive",
                     project_id=project_id)
        return {"file_path": f"{_STUB_DIR}/competitive.pdf",
                "file_size": 0, "page_count": 0}

    async def _generate_expiration(
        self, config: dict | None, project_id: int | None,
    ) -> dict:
        logger.info("generate_expiration",
                     project_id=project_id)
        return {"file_path": f"{_STUB_DIR}/expiration.pdf",
                "file_size": 0, "page_count": 0}

    async def _generate_patent_analysis(
        self, config: dict | None, project_id: int | None,
    ) -> dict:
        logger.info("generate_patent_analysis",
                     project_id=project_id)
        return {"file_path": f"{_STUB_DIR}/patent_analysis.pdf",
                "file_size": 0, "page_count": 0}

    async def _generate_custom(
        self, config: dict | None, project_id: int | None,
    ) -> dict:
        logger.info("generate_custom",
                     project_id=project_id)
        return {"file_path": f"{_STUB_DIR}/custom.pdf",
                "file_size": 0, "page_count": 0}

    # -- Internal helpers ------------------------------------------

    async def _get_user_report(
        self, session: AsyncSession,
        report_id: int, user_id: int,
    ) -> ResearchReport:
        r = await session.execute(
            select(ResearchReport).where(and_(
                ResearchReport.id == report_id,
                ResearchReport.user_id == user_id)))
        report = r.scalar_one_or_none()
        if report is None:
            raise ValueError("Report not found")
        return report

    async def _get_user_schedule(
        self, session: AsyncSession,
        schedule_id: int, user_id: int,
    ) -> ReportSchedule:
        r = await session.execute(
            select(ReportSchedule).where(and_(
                ReportSchedule.id == schedule_id,
                ReportSchedule.user_id == user_id)))
        sched = r.scalar_one_or_none()
        if sched is None:
            raise ValueError("Report schedule not found")
        return sched

    def _advance_next_run(self, schedule: ReportSchedule) -> None:
        increments = {
            "daily": timedelta(days=1),
            "weekly": timedelta(days=7),
            "monthly": timedelta(days=30),
        }
        delta = increments.get(
            schedule.frequency, timedelta(days=7))
        schedule.next_run_at = datetime.now(UTC) + delta


report_service = ReportService()
