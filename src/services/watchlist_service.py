"""Watchlist service for managing watched patents and alerts."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.patent import Citation, MaintenanceFee, Patent
from src.models.watchlist import Alert, WatchlistItem
from src.utils.logger import logger

NEW_CITATION_LOOKBACK_DAYS = 30
NEW_PATENT_LOOKBACK_DAYS = 30


class WatchlistService:
    """Service for managing watchlists and generating alerts."""

    async def get_watchlist(
        self,
        session: AsyncSession,
        user_id: str = "default",
        item_type: str | None = None,
        include_inactive: bool = False,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[dict], int]:
        """Get watchlist items for a user."""
        offset = (page - 1) * per_page

        conditions = [WatchlistItem.user_id == user_id]
        if not include_inactive:
            conditions.append(WatchlistItem.is_active == True)
        if item_type:
            conditions.append(WatchlistItem.item_type == item_type)

        # Count query
        count_query = select(func.count(WatchlistItem.id)).where(and_(*conditions))
        total = (await session.execute(count_query)).scalar() or 0

        # Fetch query with alerts count
        fetch_query = (
            select(WatchlistItem)
            .where(and_(*conditions))
            .options(selectinload(WatchlistItem.alerts))
            .order_by(WatchlistItem.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )

        result = await session.execute(fetch_query)
        items = result.scalars().all()

        return [self._to_watchlist_dict(item) for item in items], total

    async def add_to_watchlist(
        self,
        session: AsyncSession,
        item_type: str,
        item_value: str,
        user_id: str = "default",
        name: str | None = None,
        notes: str | None = None,
        notify_expiration: bool = True,
        notify_maintenance: bool = True,
        notify_citations: bool = False,
        notify_new_patents: bool = False,
        expiration_lead_days: int = 90,
        maintenance_lead_days: int = 30,
    ) -> dict:
        """Add an item to the watchlist."""
        # Check if already exists
        existing = await session.execute(
            select(WatchlistItem).where(
                and_(
                    WatchlistItem.user_id == user_id,
                    WatchlistItem.item_value == item_value,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Item '{item_value}' is already in watchlist")

        # If watching a patent, look it up
        patent_id = None
        if item_type == "patent":
            patent_result = await session.execute(
                select(Patent.id).where(Patent.patent_number == item_value)
            )
            patent_id = patent_result.scalar_one_or_none()

        item = WatchlistItem(
            user_id=user_id,
            item_type=item_type,
            item_value=item_value,
            patent_id=patent_id,
            name=name or item_value,
            notes=notes,
            notify_expiration=notify_expiration,
            notify_maintenance=notify_maintenance,
            notify_citations=notify_citations,
            notify_new_patents=notify_new_patents,
            expiration_lead_days=expiration_lead_days,
            maintenance_lead_days=maintenance_lead_days,
        )

        session.add(item)
        await session.flush()
        await session.refresh(item)

        logger.info(
            "watchlist.added",
            user_id=user_id,
            item_type=item_type,
            item_value=item_value,
        )

        return self._to_watchlist_dict(item)

    async def remove_from_watchlist(
        self,
        session: AsyncSession,
        item_id: int,
        user_id: str = "default",
    ) -> bool:
        """Remove an item from watchlist."""
        result = await session.execute(
            delete(WatchlistItem).where(
                and_(
                    WatchlistItem.id == item_id,
                    WatchlistItem.user_id == user_id,
                )
            )
        )
        deleted = result.rowcount > 0

        if deleted:
            logger.info("watchlist.removed", user_id=user_id, item_id=item_id)

        return deleted

    async def update_watchlist_item(
        self,
        session: AsyncSession,
        item_id: int,
        user_id: str = "default",
        **updates,
    ) -> dict | None:
        """Update a watchlist item."""
        allowed_fields = {
            "name",
            "notes",
            "notify_expiration",
            "notify_maintenance",
            "notify_citations",
            "notify_new_patents",
            "expiration_lead_days",
            "maintenance_lead_days",
            "is_active",
        }

        update_data = {k: v for k, v in updates.items() if k in allowed_fields}
        if not update_data:
            return None

        await session.execute(
            update(WatchlistItem)
            .where(
                and_(
                    WatchlistItem.id == item_id,
                    WatchlistItem.user_id == user_id,
                )
            )
            .values(**update_data)
        )

        result = await session.execute(
            select(WatchlistItem)
            .where(WatchlistItem.id == item_id)
            .options(selectinload(WatchlistItem.alerts))
        )
        item = result.scalar_one_or_none()

        return self._to_watchlist_dict(item) if item else None

    async def get_alerts(
        self,
        session: AsyncSession,
        user_id: str = "default",
        unread_only: bool = False,
        alert_type: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[dict], int]:
        """Get alerts for a user's watchlist items."""
        offset = (page - 1) * per_page

        # Get user's watchlist item IDs
        watchlist_ids_query = select(WatchlistItem.id).where(WatchlistItem.user_id == user_id)

        conditions = [
            Alert.watchlist_item_id.in_(watchlist_ids_query),
            Alert.is_dismissed == False,
        ]

        if unread_only:
            conditions.append(Alert.is_read == False)
        if alert_type:
            conditions.append(Alert.alert_type == alert_type)

        count_query = select(func.count(Alert.id)).where(and_(*conditions))
        total = (await session.execute(count_query)).scalar() or 0

        fetch_query = (
            select(Alert)
            .where(and_(*conditions))
            .order_by(Alert.trigger_date.desc())
            .offset(offset)
            .limit(per_page)
        )

        result = await session.execute(fetch_query)
        alerts = result.scalars().all()

        return [self._to_alert_dict(alert) for alert in alerts], total

    async def mark_alert_read(
        self,
        session: AsyncSession,
        alert_id: int,
        user_id: str = "default",
    ) -> bool:
        """Mark an alert as read."""
        # Verify alert belongs to user
        alert_check = await session.execute(
            select(Alert)
            .join(WatchlistItem)
            .where(
                and_(
                    Alert.id == alert_id,
                    WatchlistItem.user_id == user_id,
                )
            )
        )
        if not alert_check.scalar_one_or_none():
            return False

        await session.execute(
            update(Alert)
            .where(Alert.id == alert_id)
            .values(is_read=True, read_at=datetime.now(UTC))
        )
        return True

    async def dismiss_alert(
        self,
        session: AsyncSession,
        alert_id: int,
        user_id: str = "default",
    ) -> bool:
        """Dismiss an alert."""
        alert_check = await session.execute(
            select(Alert)
            .join(WatchlistItem)
            .where(
                and_(
                    Alert.id == alert_id,
                    WatchlistItem.user_id == user_id,
                )
            )
        )
        if not alert_check.scalar_one_or_none():
            return False

        await session.execute(
            update(Alert)
            .where(Alert.id == alert_id)
            .values(is_dismissed=True, dismissed_at=datetime.now(UTC))
        )
        return True

    async def generate_alerts(
        self,
        session: AsyncSession,
        user_id: str = "default",
    ) -> int:
        """
        Generate alerts for watchlist items.

        Checks expiration dates and maintenance fees for watched patents
        and creates alerts based on configured lead times.
        """
        now = datetime.now(UTC)
        alerts_created = 0

        # Get active watchlist items for user
        items_result = await session.execute(
            select(WatchlistItem).where(
                and_(
                    WatchlistItem.user_id == user_id,
                    WatchlistItem.is_active == True,
                )
            )
        )
        items = items_result.scalars().all()

        for item in items:
            if item.item_type == "patent" and item.patent_id:
                # Check for expiration alerts
                if item.notify_expiration:
                    alerts_created += await self._check_expiration_alert(session, item, now)

                # Check for maintenance fee alerts
                if item.notify_maintenance:
                    alerts_created += await self._check_maintenance_alert(session, item, now)

                # Check for new citation alerts
                if item.notify_citations:
                    alerts_created += await self._check_citation_alerts(session, item, now)

            if item.notify_new_patents and item.item_type in ("cpc_code", "assignee", "inventor"):
                alerts_created += await self._check_new_patent_alerts(session, item, now)

        logger.info(
            "watchlist.alerts_generated",
            user_id=user_id,
            count=alerts_created,
        )

        return alerts_created

    async def generate_alerts_for_all_users(self, session: AsyncSession) -> int:
        """Generate alerts for every active watchlist user."""
        user_result = await session.execute(
            select(WatchlistItem.user_id)
            .where(WatchlistItem.is_active == True)
            .distinct()
        )
        user_ids = [row[0] for row in user_result.all()]

        total_created = 0
        for user_id in user_ids:
            total_created += await self.generate_alerts(session, user_id=user_id)

        return total_created

    async def _check_expiration_alert(
        self,
        session: AsyncSession,
        item: WatchlistItem,
        now: datetime,
    ) -> int:
        """Check if expiration alert should be created."""
        patent_result = await session.execute(select(Patent).where(Patent.id == item.patent_id))
        patent = patent_result.scalar_one_or_none()

        if not patent or not patent.expiration_date:
            return 0

        # Check if within lead time
        alert_threshold = now.date() + timedelta(days=item.expiration_lead_days)
        if patent.expiration_date > alert_threshold:
            return 0

        # Check if alert already exists
        existing = await session.execute(
            select(Alert).where(
                and_(
                    Alert.watchlist_item_id == item.id,
                    Alert.alert_type == "expiration",
                    Alert.related_patent_number == patent.patent_number,
                    Alert.is_dismissed == False,
                )
            )
        )
        if existing.scalar_one_or_none():
            return 0

        # Create alert
        days_until = (patent.expiration_date - now.date()).days
        priority = "critical" if days_until <= 30 else "high" if days_until <= 60 else "medium"

        alert = Alert(
            watchlist_item_id=item.id,
            alert_type="expiration",
            priority=priority,
            title=f"Patent Expiring: {patent.patent_number}",
            message=f"{patent.title} expires in {days_until} days on {patent.expiration_date}",
            related_patent_number=patent.patent_number,
            trigger_date=now,
            due_date=datetime.combine(patent.expiration_date, datetime.min.time()).replace(
                tzinfo=UTC
            ),
        )
        session.add(alert)
        return 1

    async def _check_maintenance_alert(
        self,
        session: AsyncSession,
        item: WatchlistItem,
        now: datetime,
    ) -> int:
        """Check if maintenance fee alert should be created."""
        fees_result = await session.execute(
            select(MaintenanceFee)
            .where(
                and_(
                    MaintenanceFee.patent_id == item.patent_id,
                    MaintenanceFee.status == "pending",
                    MaintenanceFee.due_date >= now.date(),
                )
            )
            .order_by(MaintenanceFee.due_date)
            .limit(1)
        )
        fee = fees_result.scalar_one_or_none()

        if not fee:
            return 0

        alert_threshold = now.date() + timedelta(days=item.maintenance_lead_days)
        if fee.due_date > alert_threshold:
            return 0

        # Check if alert already exists
        existing = await session.execute(
            select(Alert).where(
                and_(
                    Alert.watchlist_item_id == item.id,
                    Alert.alert_type == "maintenance_fee",
                    Alert.related_data.op("->>")("fee_id") == str(fee.id),
                    Alert.is_dismissed == False,
                )
            )
        )
        if existing.scalar_one_or_none():
            return 0

        # Get patent for title
        patent_result = await session.execute(select(Patent).where(Patent.id == item.patent_id))
        patent = patent_result.scalar_one_or_none()
        patent_number = patent.patent_number if patent else item.item_value

        days_until = (fee.due_date - now.date()).days
        priority = "high" if days_until <= 14 else "medium"

        alert = Alert(
            watchlist_item_id=item.id,
            alert_type="maintenance_fee",
            priority=priority,
            title=f"Maintenance Fee Due: {patent_number}",
            message=f"Year {fee.fee_year} maintenance fee due in {days_until} days (${fee.amount_usd or 'TBD'})",
            related_patent_number=patent_number,
            related_data={"fee_id": fee.id, "fee_year": fee.fee_year},
            trigger_date=now,
            due_date=datetime.combine(fee.due_date, datetime.min.time()).replace(tzinfo=UTC),
        )
        session.add(alert)
        return 1

    async def _check_citation_alerts(
        self,
        session: AsyncSession,
        item: WatchlistItem,
        now: datetime,
    ) -> int:
        """Check if new citation alerts should be created."""
        if not item.patent_id:
            return 0

        patent_result = await session.execute(select(Patent).where(Patent.id == item.patent_id))
        patent = patent_result.scalar_one_or_none()
        if not patent:
            return 0

        since_dt = now - timedelta(days=NEW_CITATION_LOOKBACK_DAYS)

        citations_result = await session.execute(
            select(Citation, Patent)
            .join(Patent, Patent.id == Citation.citing_patent_id, isouter=True)
            .where(
                and_(
                    Citation.cited_patent_number == patent.patent_number,
                    Citation.created_at >= since_dt,
                )
            )
            .order_by(Citation.created_at.desc())
            .limit(20)
        )

        alerts_created = 0
        for citation, citing_patent in citations_result.all():
            existing = await session.execute(
                select(Alert).where(
                    and_(
                        Alert.watchlist_item_id == item.id,
                        Alert.alert_type == "new_citation",
                        Alert.related_data.op("->>")("citation_id") == str(citation.id),
                        Alert.is_dismissed == False,
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue

            citing_number = citing_patent.patent_number if citing_patent else "Unknown"
            citing_title = citing_patent.title if citing_patent else ""
            message = (
                f"{citing_number} cited {patent.patent_number}"
                if not citing_title
                else f"{citing_number} cited {patent.patent_number}: {citing_title}"
            )

            alert = Alert(
                watchlist_item_id=item.id,
                alert_type="new_citation",
                priority="medium",
                title=f"New citation for {patent.patent_number}",
                message=message,
                related_patent_number=patent.patent_number,
                related_data={
                    "citation_id": citation.id,
                    "citing_patent_number": citing_number,
                    "citing_patent_title": citing_title,
                },
                trigger_date=now,
            )
            session.add(alert)
            alerts_created += 1

        return alerts_created

    async def _check_new_patent_alerts(
        self,
        session: AsyncSession,
        item: WatchlistItem,
        now: datetime,
    ) -> int:
        """Check if new patent alerts should be created for a watchlist item."""
        since_date = now.date() - timedelta(days=NEW_PATENT_LOOKBACK_DAYS)

        query = select(Patent).where(
            or_(
                Patent.filing_date >= since_date,
                Patent.publication_date >= since_date,
            )
        )

        if item.item_type == "cpc_code":
            query = query.where(
                func.array_to_string(Patent.cpc_codes, ",").ilike(f"%{item.item_value}%")
            )
        elif item.item_type == "assignee":
            query = query.where(Patent.assignee_organization.ilike(f"%{item.item_value}%"))
        elif item.item_type == "inventor":
            query = query.where(
                func.array_to_string(Patent.inventors, ",").ilike(f"%{item.item_value}%")
            )
        else:
            return 0

        query = query.order_by(Patent.filing_date.desc().nullslast()).limit(25)
        result = await session.execute(query)
        patents = result.scalars().all()

        alerts_created = 0
        for patent in patents:
            existing = await session.execute(
                select(Alert).where(
                    and_(
                        Alert.watchlist_item_id == item.id,
                        Alert.alert_type == "new_patent",
                        Alert.related_patent_number == patent.patent_number,
                        Alert.is_dismissed == False,
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue

            alert = Alert(
                watchlist_item_id=item.id,
                alert_type="new_patent",
                priority="medium",
                title=f"New patent for {item.item_value}",
                message=f"{patent.patent_number}: {patent.title}",
                related_patent_number=patent.patent_number,
                related_data={
                    "patent_id": patent.id,
                    "filing_date": patent.filing_date.isoformat() if patent.filing_date else None,
                    "assignee": patent.assignee_organization,
                    "cpc_codes": patent.cpc_codes,
                },
                trigger_date=now,
            )
            session.add(alert)
            alerts_created += 1

        return alerts_created

    async def get_alert_summary(
        self,
        session: AsyncSession,
        user_id: str = "default",
    ) -> dict:
        """Get summary of alerts for dashboard."""
        watchlist_ids_query = select(WatchlistItem.id).where(WatchlistItem.user_id == user_id)

        # Count unread by type
        summary_query = (
            select(
                Alert.alert_type,
                func.count(Alert.id).label("count"),
            )
            .where(
                and_(
                    Alert.watchlist_item_id.in_(watchlist_ids_query),
                    Alert.is_read == False,
                    Alert.is_dismissed == False,
                )
            )
            .group_by(Alert.alert_type)
        )

        result = await session.execute(summary_query)
        by_type = {row[0]: row[1] for row in result.all()}

        total_unread = sum(by_type.values())

        # Count by priority
        priority_query = (
            select(
                Alert.priority,
                func.count(Alert.id).label("count"),
            )
            .where(
                and_(
                    Alert.watchlist_item_id.in_(watchlist_ids_query),
                    Alert.is_read == False,
                    Alert.is_dismissed == False,
                )
            )
            .group_by(Alert.priority)
        )

        priority_result = await session.execute(priority_query)
        by_priority = {row[0]: row[1] for row in priority_result.all()}

        return {
            "total_unread": total_unread,
            "by_type": by_type,
            "by_priority": by_priority,
            "critical_count": by_priority.get("critical", 0),
            "high_count": by_priority.get("high", 0),
        }

    def _to_watchlist_dict(self, item: WatchlistItem) -> dict:
        """Convert watchlist item to dict."""
        unread_alerts = (
            len([a for a in item.alerts if not a.is_read and not a.is_dismissed])
            if item.alerts
            else 0
        )

        return {
            "id": item.id,
            "item_type": item.item_type,
            "item_value": item.item_value,
            "patent_id": item.patent_id,
            "name": item.name,
            "notes": item.notes,
            "notify_expiration": item.notify_expiration,
            "notify_maintenance": item.notify_maintenance,
            "notify_citations": item.notify_citations,
            "notify_new_patents": item.notify_new_patents,
            "expiration_lead_days": item.expiration_lead_days,
            "maintenance_lead_days": item.maintenance_lead_days,
            "is_active": item.is_active,
            "unread_alerts": unread_alerts,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }

    def _to_alert_dict(self, alert: Alert) -> dict:
        """Convert alert to dict."""
        return {
            "id": alert.id,
            "watchlist_item_id": alert.watchlist_item_id,
            "alert_type": alert.alert_type,
            "priority": alert.priority,
            "title": alert.title,
            "message": alert.message,
            "related_patent_number": alert.related_patent_number,
            "related_data": alert.related_data,
            "trigger_date": alert.trigger_date.isoformat() if alert.trigger_date else None,
            "due_date": alert.due_date.isoformat() if alert.due_date else None,
            "is_read": alert.is_read,
            "is_dismissed": alert.is_dismissed,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
        }


watchlist_service = WatchlistService()
