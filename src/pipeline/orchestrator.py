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
    """Background task for patent ingestion with database storage."""
    import asyncio
    from datetime import datetime
    from src.utils.logger import logger

    logger.info("task.ingest_patents.started", source=source, task_id=self.request.id)

    async def _run():
        from src.database.connection import get_db_session
        from src.pipeline.patent_store import store_patent_batch
        from src.models.ingestion import IngestionJob

        if source == "uspto":
            from src.ingesters.uspto_ingester import USPTOIngester
            ingester = USPTOIngester()
        else:
            raise ValueError(f"Unknown source: {source}")

        total_fetched = 0
        total_inserted = 0
        total_updated = 0
        total_errors = 0

        try:
            async for batch in ingester.fetch_patents(
                offset=0, limit=batch_size, since=None
            ):
                async with get_db_session() as session:
                    ins, upd, errs = await store_patent_batch(
                        session, batch, source=source
                    )
                    total_inserted += ins
                    total_updated += upd
                    total_errors += errs
                    total_fetched += len(batch)

                if max_patents and total_fetched >= max_patents:
                    break

                # Update task progress
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "fetched": total_fetched,
                        "inserted": total_inserted,
                        "updated": total_updated,
                    },
                )
        except Exception as e:
            total_errors += 1
            logger.error("task.ingest_patents.error", error=str(e))
            raise
        finally:
            await ingester.close()

        return {
            "source": source,
            "total_fetched": total_fetched,
            "total_inserted": total_inserted,
            "total_updated": total_updated,
            "total_errors": total_errors,
        }

    result = asyncio.run(_run())

    logger.info(
        "task.ingest_patents.completed",
        source=source,
        fetched=result["total_fetched"],
        inserted=result["total_inserted"],
        errors=result["total_errors"],
    )

    return result


@celery_app.task(name="pipeline.generate_embeddings", bind=True)
def generate_embeddings_task(self, patent_ids: list[int] | None = None, batch_size: int = 32):
    """Background task for generating patent embeddings."""
    import asyncio
    from src.utils.logger import logger

    logger.info("task.generate_embeddings.started", task_id=self.request.id)

    async def _run():
        from src.database.connection import get_db_session
        from src.ai.embeddings import embedding_service

        total_processed = 0
        async with get_db_session() as session:
            while True:
                count = await embedding_service.embed_patents(
                    session, patent_ids=patent_ids, batch_size=batch_size
                )
                if count == 0:
                    break
                total_processed += count
                self.update_state(
                    state="PROGRESS",
                    meta={"processed": total_processed},
                )

        return total_processed

    processed = asyncio.run(_run())
    return {"status": "completed", "processed": processed}
