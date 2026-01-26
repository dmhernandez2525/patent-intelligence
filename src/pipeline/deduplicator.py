from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.patent import Patent
from src.utils.logger import logger


async def find_duplicates(session: AsyncSession) -> list[tuple[int, int]]:
    """Find duplicate patents based on patent_number."""
    subquery = (
        select(Patent.patent_number)
        .group_by(Patent.patent_number)
        .having(func.count(Patent.id) > 1)
    )

    result = await session.execute(
        select(Patent.id, Patent.patent_number, Patent.source, Patent.updated_at)
        .where(Patent.patent_number.in_(subquery))
        .order_by(Patent.patent_number, Patent.updated_at.desc())
    )

    duplicates: list[tuple[int, int]] = []
    seen: dict[str, int] = {}

    for row in result:
        patent_number = row[1]
        if patent_number in seen:
            duplicates.append((row[0], seen[patent_number]))
        else:
            seen[patent_number] = row[0]

    logger.info("deduplicator.found_duplicates", count=len(duplicates))
    return duplicates


async def merge_duplicates(session: AsyncSession, keep_id: int, remove_id: int) -> None:
    """Merge duplicate patent records, keeping the most complete one."""
    keep = await session.get(Patent, keep_id)
    remove = await session.get(Patent, remove_id)

    if not keep or not remove:
        return

    for field in ["abstract", "description", "assignee_organization", "cpc_codes"]:
        keep_val = getattr(keep, field)
        remove_val = getattr(remove, field)
        if not keep_val and remove_val:
            setattr(keep, field, remove_val)

    await session.delete(remove)
    logger.info("deduplicator.merged", keep_id=keep_id, remove_id=remove_id)
