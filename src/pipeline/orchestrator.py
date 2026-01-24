from celery import Celery

from src.config import settings

celery_app = Celery(
    "patent_intelligence",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3000,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)


@celery_app.task(name="pipeline.ingest_patents", bind=True)
def ingest_patents_task(self, source: str, batch_size: int = 100, max_patents: int | None = None):
    """Background task for patent ingestion."""
    import asyncio
    from src.utils.logger import logger

    logger.info("task.ingest_patents.started", source=source, task_id=self.request.id)

    async def _run():
        if source == "uspto":
            from src.ingesters.uspto_ingester import USPTOIngester
            ingester = USPTOIngester()
        else:
            raise ValueError(f"Unknown source: {source}")

        return await ingester.run_ingestion(batch_size=batch_size, max_patents=max_patents)

    result = asyncio.run(_run())

    logger.info(
        "task.ingest_patents.completed",
        source=source,
        fetched=result.total_fetched,
        errors=result.total_errors,
    )

    return {
        "source": result.source,
        "total_fetched": result.total_fetched,
        "total_inserted": result.total_inserted,
        "total_updated": result.total_updated,
        "total_errors": result.total_errors,
        "duration_seconds": result.duration_seconds,
    }


@celery_app.task(name="pipeline.generate_embeddings", bind=True)
def generate_embeddings_task(self, patent_ids: list[int] | None = None, batch_size: int = 32):
    """Background task for generating patent embeddings."""
    from src.utils.logger import logger

    logger.info("task.generate_embeddings.started", task_id=self.request.id)
    return {"status": "completed", "processed": 0}
