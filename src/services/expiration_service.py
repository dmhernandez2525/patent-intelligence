from datetime import date, timedelta

from sqlalchemy import and_, extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.patent import MaintenanceFee, Patent


class ExpirationService:
    """Service for patent expiration tracking and analysis."""

    async def get_expiring_patents(
        self,
        session: AsyncSession,
        days: int = 30,
        country: str | None = None,
        cpc_code: str | None = None,
        assignee: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[dict], int]:
        """Get patents expiring within the specified number of days."""
        today = date.today()
        end_date = today + timedelta(days=days)
        offset = (page - 1) * per_page

        conditions = [
            Patent.expiration_date >= today,
            Patent.expiration_date <= end_date,
            Patent.status == "active",
        ]

        if country:
            conditions.append(Patent.country == country)
        if cpc_code:
            conditions.append(func.array_to_string(Patent.cpc_codes, ",").ilike(f"%{cpc_code}%"))
        if assignee:
            conditions.append(Patent.assignee_organization.ilike(f"%{assignee}%"))

        base_query = (
            select(Patent).where(and_(*conditions)).options(selectinload(Patent.maintenance_fees))
        )

        count_query = select(func.count()).select_from(
            select(Patent.id).where(and_(*conditions)).subquery()
        )
        total = (await session.execute(count_query)).scalar() or 0

        results_query = (
            base_query.order_by(Patent.expiration_date.asc()).offset(offset).limit(per_page)
        )

        result = await session.execute(results_query)
        patents = result.scalars().all()

        items = [self._to_expiration_item(p, today) for p in patents]
        return items, total

    async def get_lapsed_patents(
        self,
        session: AsyncSession,
        days_back: int = 365,
        country: str | None = None,
        cpc_code: str | None = None,
        assignee: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[dict], int]:
        """Get patents that recently lapsed (expired or missed maintenance fees)."""
        today = date.today()
        start_date = today - timedelta(days=days_back)
        offset = (page - 1) * per_page

        conditions = [
            Patent.status.in_(["lapsed", "expired"]),
            or_(
                and_(
                    Patent.expiration_date >= start_date,
                    Patent.expiration_date <= today,
                ),
                Patent.updated_at >= start_date,
            ),
        ]

        if country:
            conditions.append(Patent.country == country)
        if cpc_code:
            conditions.append(func.array_to_string(Patent.cpc_codes, ",").ilike(f"%{cpc_code}%"))
        if assignee:
            conditions.append(Patent.assignee_organization.ilike(f"%{assignee}%"))

        base_query = (
            select(Patent).where(and_(*conditions)).options(selectinload(Patent.maintenance_fees))
        )

        count_query = select(func.count()).select_from(
            select(Patent.id).where(and_(*conditions)).subquery()
        )
        total = (await session.execute(count_query)).scalar() or 0

        results_query = (
            base_query.order_by(Patent.expiration_date.desc()).offset(offset).limit(per_page)
        )

        result = await session.execute(results_query)
        patents = result.scalars().all()

        items = [self._to_expiration_item(p, today) for p in patents]
        return items, total

    async def get_upcoming_maintenance_fees(
        self,
        session: AsyncSession,
        days: int = 90,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[dict], int]:
        """Get maintenance fees due within the specified time window."""
        today = date.today()
        end_date = today + timedelta(days=days)
        offset = (page - 1) * per_page

        conditions = [
            MaintenanceFee.due_date >= today,
            MaintenanceFee.due_date <= end_date,
            MaintenanceFee.status == "pending",
        ]

        base_query = (
            select(MaintenanceFee, Patent)
            .join(Patent, MaintenanceFee.patent_id == Patent.id)
            .where(and_(*conditions))
        )

        count_query = select(func.count()).select_from(
            select(MaintenanceFee.id).where(and_(*conditions)).subquery()
        )
        total = (await session.execute(count_query)).scalar() or 0

        results_query = (
            base_query.order_by(MaintenanceFee.due_date.asc()).offset(offset).limit(per_page)
        )

        result = await session.execute(results_query)
        rows = result.all()

        items = []
        for fee, patent in rows:
            items.append(
                {
                    "patent_number": patent.patent_number,
                    "title": patent.title,
                    "assignee_organization": patent.assignee_organization,
                    "fee_year": fee.fee_year,
                    "due_date": fee.due_date.isoformat(),
                    "grace_period_end": fee.grace_period_end.isoformat()
                    if fee.grace_period_end
                    else None,
                    "amount_usd": fee.amount_usd,
                    "days_until_due": (fee.due_date - today).days,
                    "status": fee.status,
                }
            )

        return items, total

    async def get_expiration_stats(
        self,
        session: AsyncSession,
        country: str | None = None,
    ) -> dict:
        """Get summary statistics for patent expirations."""
        today = date.today()

        conditions_base = [Patent.status == "active", Patent.expiration_date.isnot(None)]
        if country:
            conditions_base.append(Patent.country == country)

        # Count by time window
        window_30 = await self._count_expiring(session, conditions_base, today, 30)
        window_90 = await self._count_expiring(session, conditions_base, today, 90)
        window_180 = await self._count_expiring(session, conditions_base, today, 180)
        window_365 = await self._count_expiring(session, conditions_base, today, 365)

        # Count lapsed in last year
        lapsed_conditions = [
            Patent.status.in_(["lapsed", "expired"]),
            Patent.expiration_date >= today - timedelta(days=365),
            Patent.expiration_date <= today,
        ]
        if country:
            lapsed_conditions.append(Patent.country == country)
        lapsed_count = (
            await session.execute(select(func.count(Patent.id)).where(and_(*lapsed_conditions)))
        ).scalar() or 0

        # Pending maintenance fees
        pending_fees = (
            await session.execute(
                select(func.count(MaintenanceFee.id)).where(
                    and_(
                        MaintenanceFee.status == "pending",
                        MaintenanceFee.due_date >= today,
                        MaintenanceFee.due_date <= today + timedelta(days=180),
                    )
                )
            )
        ).scalar() or 0

        # Top CPC codes expiring soon (90 days)
        top_cpc_query = (
            select(
                func.unnest(Patent.cpc_codes).label("cpc_code"),
                func.count(Patent.id).label("count"),
            )
            .where(
                and_(
                    *conditions_base,
                    Patent.expiration_date >= today,
                    Patent.expiration_date <= today + timedelta(days=90),
                )
            )
            .group_by("cpc_code")
            .order_by(func.count(Patent.id).desc())
            .limit(10)
        )
        top_cpc_result = await session.execute(top_cpc_query)
        top_cpc_sectors = [{"cpc_code": row[0], "count": row[1]} for row in top_cpc_result.all()]

        # Monthly expiration timeline (next 12 months) - single query
        first_month_start = date(today.year, today.month, 1)
        # Calculate end of 12th month
        end_month = today.month + 11
        end_year = today.year + (end_month - 1) // 12
        end_month_adj = ((end_month - 1) % 12) + 1
        last_month_end = date(
            end_year + (end_month_adj // 12), (end_month_adj % 12) + 1, 1
        ) - timedelta(days=1)

        timeline_result = await session.execute(
            select(
                extract("year", Patent.expiration_date).label("exp_year"),
                extract("month", Patent.expiration_date).label("exp_month"),
                func.count(Patent.id).label("count"),
            )
            .where(
                and_(
                    *conditions_base,
                    Patent.expiration_date >= first_month_start,
                    Patent.expiration_date <= last_month_end,
                )
            )
            .group_by("exp_year", "exp_month")
            .order_by("exp_year", "exp_month")
        )
        month_counts = {(int(row[0]), int(row[1])): row[2] for row in timeline_result.all()}

        timeline = []
        for i in range(12):
            m = today.month + i
            y = today.year + (m - 1) // 12
            m_adj = ((m - 1) % 12) + 1
            month_start = date(y, m_adj, 1)
            timeline.append(
                {
                    "month": month_start.isoformat(),
                    "count": month_counts.get((y, m_adj), 0),
                }
            )

        return {
            "expiring_30_days": window_30,
            "expiring_90_days": window_90,
            "expiring_180_days": window_180,
            "expiring_365_days": window_365,
            "recently_lapsed": lapsed_count,
            "pending_maintenance_fees": pending_fees,
            "top_sectors": top_cpc_sectors,
            "monthly_timeline": timeline,
        }

    async def _count_expiring(
        self,
        session: AsyncSession,
        base_conditions: list,
        today: date,
        days: int,
    ) -> int:
        end_date = today + timedelta(days=days)
        return (
            await session.execute(
                select(func.count(Patent.id)).where(
                    and_(
                        *base_conditions,
                        Patent.expiration_date >= today,
                        Patent.expiration_date <= end_date,
                    )
                )
            )
        ).scalar() or 0

    def _to_expiration_item(self, patent: Patent, today: date) -> dict:
        """Convert a patent to an expiration item dict."""
        days_until = (patent.expiration_date - today).days if patent.expiration_date else 0

        # Determine maintenance fee status from related fees
        fee_status = "unknown"
        if patent.maintenance_fees:
            pending_fees = [f for f in patent.maintenance_fees if f.status == "pending"]
            overdue_fees = [
                f for f in patent.maintenance_fees if f.status == "pending" and f.due_date < today
            ]
            if overdue_fees:
                fee_status = "overdue"
            elif pending_fees:
                next_fee = min(pending_fees, key=lambda f: f.due_date)
                if (next_fee.due_date - today).days <= 90:
                    fee_status = "due_soon"
                else:
                    fee_status = "current"
            else:
                paid_fees = [f for f in patent.maintenance_fees if f.status == "paid"]
                fee_status = "all_paid" if paid_fees else "no_fees"
        else:
            fee_status = "no_fees"

        # Next maintenance fee info
        next_fee_date = None
        next_fee_amount = None
        if patent.maintenance_fees:
            future_pending = [
                f for f in patent.maintenance_fees if f.status == "pending" and f.due_date >= today
            ]
            if future_pending:
                next_fee = min(future_pending, key=lambda f: f.due_date)
                next_fee_date = next_fee.due_date.isoformat()
                next_fee_amount = next_fee.amount_usd

        return {
            "patent_number": patent.patent_number,
            "title": patent.title,
            "abstract": patent.abstract,
            "expiration_date": patent.expiration_date.isoformat()
            if patent.expiration_date
            else None,
            "filing_date": patent.filing_date.isoformat() if patent.filing_date else None,
            "grant_date": patent.grant_date.isoformat() if patent.grant_date else None,
            "assignee_organization": patent.assignee_organization,
            "cpc_codes": patent.cpc_codes,
            "country": patent.country,
            "status": patent.status,
            "days_until_expiration": days_until,
            "maintenance_fee_status": fee_status,
            "next_fee_date": next_fee_date,
            "next_fee_amount": next_fee_amount,
            "citation_count": patent.citation_count,
            "patent_type": patent.patent_type,
        }


expiration_service = ExpirationService()
