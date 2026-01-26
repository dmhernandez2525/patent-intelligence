from datetime import date

from src.ingesters.base import RawPatentData
from src.utils.logger import logger


def parse_date(date_str: str | None) -> date | None:
    """Parse various date formats to a date object."""
    if not date_str:
        return None

    formats = ["%Y-%m-%d", "%Y%m%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]

    for fmt in formats:
        try:
            return (
                date.fromisoformat(date_str)
                if fmt == "%Y-%m-%d"
                else __import__("datetime").datetime.strptime(date_str, fmt).date()
            )
        except (ValueError, TypeError):
            continue

    logger.warning("normalizer.date_parse_failed", date_str=date_str)
    return None


def normalize_patent_number(number: str, country: str = "US") -> str:
    """Normalize patent number format."""
    cleaned = number.strip().upper().replace(" ", "").replace(",", "")

    if country == "US" and not cleaned.startswith("US"):
        cleaned = f"US{cleaned}"

    return cleaned


def normalize_cpc_code(code: str) -> str:
    """Normalize CPC classification code."""
    return code.strip().upper().replace(" ", "")


def normalize_raw_patent(raw: RawPatentData) -> dict:
    """Normalize raw patent data into database-ready format."""
    return {
        "patent_number": normalize_patent_number(raw.patent_number, raw.country),
        "title": raw.title.strip() if raw.title else "",
        "abstract": raw.abstract.strip() if raw.abstract else None,
        "description": raw.description,
        "filing_date": parse_date(raw.filing_date),
        "grant_date": parse_date(raw.grant_date),
        "publication_date": parse_date(raw.publication_date),
        "priority_date": parse_date(raw.priority_date),
        "assignee": raw.assignee,
        "assignee_organization": raw.assignee_organization,
        "inventors": raw.inventors or [],
        "inventor_countries": raw.inventor_countries or [],
        "cpc_codes": [normalize_cpc_code(c) for c in (raw.cpc_codes or [])],
        "ipc_codes": raw.ipc_codes or [],
        "uspc_codes": raw.uspc_codes or [],
        "patent_type": raw.patent_type,
        "country": raw.country,
        "kind_code": raw.kind_code,
        "status": raw.status,
        "source": "unknown",
        "raw_data": raw.raw_data,
    }
