from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.utils.logger import logger


@dataclass
class IngestionResult:
    source: str
    total_fetched: int = 0
    total_inserted: int = 0
    total_updated: int = 0
    total_errors: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float | None:
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class RawPatentData:
    patent_number: str
    title: str
    abstract: str | None = None
    description: str | None = None
    claims: list[dict] | None = None
    filing_date: str | None = None
    grant_date: str | None = None
    publication_date: str | None = None
    priority_date: str | None = None
    assignee: str | None = None
    assignee_organization: str | None = None
    inventors: list[str] | None = None
    inventor_countries: list[str] | None = None
    cpc_codes: list[str] | None = None
    ipc_codes: list[str] | None = None
    uspc_codes: list[str] | None = None
    citations: list[dict] | None = None
    patent_type: str | None = None
    country: str = "US"
    kind_code: str | None = None
    status: str = "active"
    raw_data: dict | None = None


class BaseIngester(ABC):
    """Base class for all patent data ingesters."""

    source_name: str = "unknown"

    @abstractmethod
    async def fetch_patents(
        self,
        offset: int = 0,
        limit: int = 100,
        since: datetime | None = None,
    ) -> AsyncGenerator[list[RawPatentData], None]:
        """Fetch patents from the source in batches."""
        yield []  # pragma: no cover

    @abstractmethod
    async def fetch_patent_detail(self, patent_number: str) -> RawPatentData | None:
        """Fetch detailed data for a single patent."""
        ...  # pragma: no cover

    async def validate_connection(self) -> bool:
        """Validate that the data source is accessible."""
        try:
            async for batch in self.fetch_patents(offset=0, limit=1):
                return len(batch) > 0
        except Exception as e:
            logger.error("ingester.connection_failed", source=self.source_name, error=str(e))
            return False

    async def run_ingestion(
        self,
        batch_size: int = 100,
        max_patents: int | None = None,
        since: datetime | None = None,
    ) -> IngestionResult:
        """Run a full ingestion cycle."""
        result = IngestionResult(source=self.source_name)
        total_fetched = 0

        logger.info(
            "ingestion.started",
            source=self.source_name,
            batch_size=batch_size,
            max_patents=max_patents,
        )

        try:
            async for batch in self.fetch_patents(offset=0, limit=batch_size, since=since):
                result.total_fetched += len(batch)
                total_fetched += len(batch)

                if max_patents and total_fetched >= max_patents:
                    break

        except Exception as e:
            result.total_errors += 1
            result.errors.append(str(e))
            logger.error("ingestion.error", source=self.source_name, error=str(e))

        result.completed_at = datetime.now(timezone.utc)
        logger.info(
            "ingestion.completed",
            source=self.source_name,
            fetched=result.total_fetched,
            errors=result.total_errors,
            duration_seconds=result.duration_seconds,
        )

        return result
