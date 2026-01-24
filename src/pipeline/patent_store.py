from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from src.ingesters.base import RawPatentData
from src.models.patent import Patent, Citation, PatentClaim
from src.pipeline.normalizer import normalize_raw_patent, parse_date
from src.pipeline.expiration_calc import calculate_expiration_date
from src.utils.logger import logger


async def store_patent_batch(
    session: AsyncSession,
    raw_patents: list[RawPatentData],
    source: str = "uspto",
) -> tuple[int, int, int]:
    """
    Store a batch of patents in the database.

    Returns (inserted, updated, errors) counts.
    """
    inserted = 0
    updated = 0
    errors = 0

    for raw in raw_patents:
        try:
            normalized = normalize_raw_patent(raw)
            normalized["source"] = source

            # Calculate expiration date
            filing_date = normalized.get("filing_date")
            grant_date = normalized.get("grant_date")
            patent_type = normalized.get("patent_type")

            if filing_date or grant_date:
                expiration = calculate_expiration_date(
                    filing_date=filing_date,
                    grant_date=grant_date,
                    patent_type=patent_type,
                )
                normalized["expiration_date"] = expiration

            # Check if patent exists
            existing = await session.execute(
                select(Patent).where(Patent.patent_number == normalized["patent_number"])
            )
            existing_patent = existing.scalar_one_or_none()

            if existing_patent:
                # Update existing patent
                for key, value in normalized.items():
                    if key not in ("raw_data",) and value is not None:
                        setattr(existing_patent, key, value)
                updated += 1
            else:
                # Insert new patent
                patent = Patent(**{
                    k: v for k, v in normalized.items()
                    if k in Patent.__table__.columns.keys()
                })
                session.add(patent)
                inserted += 1

                # Store citations if available
                if raw.citations:
                    await session.flush()  # Get patent ID
                    for cite_data in raw.citations[:50]:  # Limit citations per patent
                        citation = Citation(
                            citing_patent_id=patent.id,
                            cited_patent_number=cite_data.get("patent_number", ""),
                            citation_type="patent",
                            category=cite_data.get("category"),
                        )
                        session.add(citation)

        except Exception as e:
            errors += 1
            logger.error(
                "store.patent_error",
                patent_number=raw.patent_number,
                error=str(e),
            )

    try:
        await session.flush()
    except Exception as e:
        logger.error("store.flush_error", error=str(e))
        await session.rollback()

    logger.info(
        "store.batch_complete",
        inserted=inserted,
        updated=updated,
        errors=errors,
    )

    return inserted, updated, errors
