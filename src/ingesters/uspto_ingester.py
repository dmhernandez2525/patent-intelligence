from collections.abc import AsyncGenerator
from datetime import datetime

import httpx

from src.config import settings
from src.ingesters.base import BaseIngester, RawPatentData
from src.utils.logger import logger
from src.utils.rate_limiter import uspto_limiter


class USPTOIngester(BaseIngester):
    """Ingester for USPTO PatentsView API v1."""

    source_name = "uspto"
    BASE_URL = "https://search.patentsview.org/api/v1"

    PATENT_FIELDS = [
        "patent_id",
        "patent_title",
        "patent_abstract",
        "patent_date",
        "patent_type",
        "patent_kind",
        "patent_num_claims",
        "application.application_number",
        "application.filing_date",
        "assignees.assignee_organization",
        "assignees.assignee_individual_name_first",
        "assignees.assignee_individual_name_last",
        "assignees.assignee_country",
        "inventors.inventor_name_first",
        "inventors.inventor_name_last",
        "inventors.inventor_country",
        "cpcs.cpc_group_id",
        "cpcs.cpc_subclass_id",
        "cited_patents.cited_patent_id",
        "cited_patents.cited_patent_category",
    ]

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                headers={"Accept": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _build_query(self, since: datetime | None = None) -> dict:
        """Build PatentsView query filter."""
        if since:
            date_str = since.strftime("%Y-%m-%d")
            return {"_gte": {"patent_date": date_str}}
        return {"_gte": {"patent_date": "2020-01-01"}}

    def _parse_patent(self, raw: dict) -> RawPatentData:
        """Parse PatentsView API response into RawPatentData."""
        patent_id = raw.get("patent_id", "")
        title = raw.get("patent_title", "")
        abstract = raw.get("patent_abstract", "")

        # Parse assignees
        assignees = raw.get("assignees", []) or []
        assignee_org = None
        assignee_name = None
        if assignees:
            first_assignee = assignees[0]
            assignee_org = first_assignee.get("assignee_organization")
            if not assignee_org:
                first_name = first_assignee.get("assignee_individual_name_first", "")
                last_name = first_assignee.get("assignee_individual_name_last", "")
                assignee_name = f"{first_name} {last_name}".strip()

        # Parse inventors
        inventors_raw = raw.get("inventors", []) or []
        inventors = []
        inventor_countries = []
        for inv in inventors_raw:
            first = inv.get("inventor_name_first", "")
            last = inv.get("inventor_name_last", "")
            name = f"{first} {last}".strip()
            if name:
                inventors.append(name)
            country = inv.get("inventor_country", "")
            if country:
                inventor_countries.append(country)

        # Parse CPC codes
        cpcs_raw = raw.get("cpcs", []) or []
        cpc_codes = list({
            cpc.get("cpc_group_id", "")
            for cpc in cpcs_raw
            if cpc.get("cpc_group_id")
        })

        # Parse citations
        cited_raw = raw.get("cited_patents", []) or []
        citations = []
        for cite in cited_raw:
            cited_id = cite.get("cited_patent_id")
            if cited_id:
                citations.append({
                    "patent_number": cited_id,
                    "category": cite.get("cited_patent_category", ""),
                })

        # Parse application data
        application = raw.get("application", {}) or {}
        application_number = application.get("application_number")
        filing_date = application.get("filing_date")

        return RawPatentData(
            patent_number=patent_id,
            title=title or "Untitled",
            abstract=abstract or None,
            filing_date=filing_date,
            grant_date=raw.get("patent_date"),
            patent_type=raw.get("patent_type"),
            kind_code=raw.get("patent_kind"),
            assignee=assignee_name,
            assignee_organization=assignee_org,
            inventors=inventors if inventors else None,
            inventor_countries=inventor_countries if inventor_countries else None,
            cpc_codes=cpc_codes if cpc_codes else None,
            citations=citations if citations else None,
            country="US",
            status="active",
            raw_data=raw,
        )

    async def fetch_patents(
        self,
        offset: int = 0,
        limit: int = 100,
        since: datetime | None = None,
    ) -> AsyncGenerator[list[RawPatentData], None]:
        """Fetch patents from PatentsView API in batches."""
        client = await self._get_client()
        current_offset = offset
        batch_size = min(limit, 100)  # PatentsView max per_page is 1000

        while True:
            async with uspto_limiter:
                query = self._build_query(since)

                params = {
                    "q": query,
                    "f": self.PATENT_FIELDS,
                    "o": {
                        "page": (current_offset // batch_size) + 1,
                        "per_page": batch_size,
                    },
                    "s": [{"patent_date": "desc"}],
                }

                logger.info(
                    "uspto.fetching",
                    offset=current_offset,
                    batch_size=batch_size,
                )

                try:
                    response = await client.post(
                        f"{self.BASE_URL}/patents/",
                        json=params,
                    )
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    logger.error(
                        "uspto.api_error",
                        status_code=e.response.status_code,
                        detail=e.response.text[:200],
                    )
                    if e.response.status_code == 429:
                        # Rate limited - wait and retry
                        import asyncio
                        await asyncio.sleep(60)
                        continue
                    raise
                except httpx.RequestError as e:
                    logger.error("uspto.request_error", error=str(e))
                    raise

                data = response.json()
                patents = data.get("patents", [])

                if not patents:
                    logger.info("uspto.no_more_results", offset=current_offset)
                    break

                batch = [self._parse_patent(p) for p in patents]
                yield batch

                total_count = data.get("total_patent_count", 0)
                current_offset += len(patents)

                logger.info(
                    "uspto.batch_complete",
                    fetched=len(batch),
                    total_so_far=current_offset,
                    total_available=total_count,
                )

                if current_offset >= total_count:
                    break

    async def fetch_patent_detail(self, patent_number: str) -> RawPatentData | None:
        """Fetch detailed data for a single patent."""
        client = await self._get_client()

        async with uspto_limiter:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/patents/",
                    json={
                        "q": {"patent_id": patent_number},
                        "f": self.PATENT_FIELDS,
                        "o": {"page": 1, "per_page": 1},
                    },
                )
                response.raise_for_status()
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                logger.error(
                    "uspto.detail_error",
                    patent_number=patent_number,
                    error=str(e),
                )
                return None

            data = response.json()
            patents = data.get("patents", [])

            if not patents:
                return None

            return self._parse_patent(patents[0])

    async def fetch_maintenance_fees(self, patent_number: str) -> list[dict]:
        """Fetch maintenance fee events for a patent from USPTO."""
        client = await self._get_client()

        async with uspto_limiter:
            try:
                response = await client.get(
                    f"https://developer.uspto.gov/ptab-api/maintenance-fees/{patent_number}",
                )
                if response.status_code == 200:
                    return response.json().get("fees", [])
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                logger.warning(
                    "uspto.maintenance_fee_error",
                    patent_number=patent_number,
                    error=str(e),
                )
            return []
