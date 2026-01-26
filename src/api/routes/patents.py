from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.patent import PatentDetailResponse, PatentListResponse, PatentResponse
from src.database.connection import get_session
from src.models.patent import Patent

router = APIRouter()


@router.get("", response_model=PatentListResponse)
async def list_patents(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    country: str | None = None,
    status: str | None = None,
    assignee: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> PatentListResponse:
    query = select(Patent)

    if country:
        query = query.where(Patent.country == country)
    if status:
        query = query.where(Patent.status == status)
    if assignee:
        query = query.where(Patent.assignee_organization.ilike(f"%{assignee}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * per_page).limit(per_page)
    query = query.order_by(Patent.filing_date.desc().nullslast())

    result = await session.execute(query)
    patents = result.scalars().all()

    return PatentListResponse(
        patents=[PatentResponse.model_validate(p, from_attributes=True) for p in patents],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page,
    )


@router.get("/{patent_number}", response_model=PatentDetailResponse)
async def get_patent(
    patent_number: str,
    session: AsyncSession = Depends(get_session),
) -> PatentDetailResponse:
    query = select(Patent).where(Patent.patent_number == patent_number)
    result = await session.execute(query)
    patent = result.scalar_one_or_none()

    if not patent:
        raise HTTPException(status_code=404, detail=f"Patent {patent_number} not found")

    return PatentDetailResponse.model_validate(patent, from_attributes=True)


@router.get("/stats/overview")
async def patent_stats(
    session: AsyncSession = Depends(get_session),
) -> dict:
    total = (await session.execute(select(func.count(Patent.id)))).scalar() or 0

    active = (
        await session.execute(
            select(func.count(Patent.id)).where(Patent.status == "active")
        )
    ).scalar() or 0

    expired = (
        await session.execute(
            select(func.count(Patent.id)).where(Patent.status == "expired")
        )
    ).scalar() or 0

    lapsed = (
        await session.execute(
            select(func.count(Patent.id)).where(Patent.status == "lapsed")
        )
    ).scalar() or 0

    countries = (
        await session.execute(
            select(func.count(func.distinct(Patent.country)))
        )
    ).scalar() or 0

    return {
        "total_patents": total,
        "active": active,
        "expired": expired,
        "lapsed": lapsed,
        "countries": countries,
    }
