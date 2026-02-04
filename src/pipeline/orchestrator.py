from datetime import UTC, datetime

from celery import Celery
from celery.schedules import crontab

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
    beat_schedule={
        "watchlist-alerts-schedule": {
            "task": "pipeline.generate_watchlist_alerts",
            "schedule": crontab(minute=0, hour="*/6"),
        },
    },
)


def _run_async(coro):
    """Run an async coroutine in a way compatible with Celery workers."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


@celery_app.task(name="pipeline.ingest_patents", bind=True)
def ingest_patents_task(
    self,
    source: str,
    batch_size: int = 100,
    max_patents: int | None = None,
    since_date: str | None = None,
    job_id: int | None = None,
):
    """Background task for patent ingestion with database storage."""
    from src.utils.logger import logger

    logger.info("task.ingest_patents.started", source=source, task_id=self.request.id)

    async def _run():
        from sqlalchemy import select

        from src.database.connection import get_db_session
        from src.models.ingestion import IngestionCheckpoint, IngestionJob
        from src.pipeline.patent_store import store_patent_batch

        since: datetime | None = None
        if since_date:
            try:
                since = datetime.strptime(since_date, "%Y-%m-%d")
            except ValueError:
                logger.warning("task.ingest_patents.invalid_since_date", since_date=since_date)

        if source == "uspto":
            from src.ingesters.uspto_ingester import USPTOIngester

            ingester = USPTOIngester()
        elif source == "epo":
            from src.ingesters.epo_ingester import EPOIngester

            ingester = EPOIngester()
        else:
            raise ValueError(f"Unknown source: {source}")

        total_fetched = 0
        total_inserted = 0
        total_updated = 0
        total_errors = 0

        async def _mark_failed(error_message: str) -> None:
            if job_id is None:
                return
            completed_at = datetime.now(UTC)
            async with get_db_session() as session:
                job = await session.get(IngestionJob, job_id)
                if not job:
                    return
                job.status = "failed"
                job.error_message = error_message
                job.completed_at = completed_at
                if job.started_at:
                    job.duration_seconds = (completed_at - job.started_at).total_seconds()
                job.total_fetched = total_fetched
                job.total_inserted = total_inserted
                job.total_updated = total_updated
                job.total_errors = total_errors

        try:
            async for batch in ingester.fetch_patents(offset=0, limit=batch_size, since=since):
                async with get_db_session() as session:
                    ins, upd, errs = await store_patent_batch(session, batch, source=source)
                    total_inserted += ins
                    total_updated += upd
                    total_errors += errs
                    total_fetched += len(batch)

                    if job_id is not None:
                        job = await session.get(IngestionJob, job_id)
                        if job:
                            job.total_fetched = total_fetched
                            job.total_inserted = total_inserted
                            job.total_updated = total_updated
                            job.total_errors = total_errors
                            job.status = "running"
                            if job.started_at is None:
                                job.started_at = datetime.now(UTC)

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
            await _mark_failed(str(e))
            raise
        finally:
            await ingester.close()

        if job_id is not None:
            completed_at = datetime.now(UTC)
            async with get_db_session() as session:
                job = await session.get(IngestionJob, job_id)
                if job:
                    job.status = "completed"
                    job.completed_at = completed_at
                    if job.started_at:
                        job.duration_seconds = (completed_at - job.started_at).total_seconds()
                    job.total_fetched = total_fetched
                    job.total_inserted = total_inserted
                    job.total_updated = total_updated
                    job.total_errors = total_errors

                checkpoint_result = await session.execute(
                    select(IngestionCheckpoint).where(IngestionCheckpoint.source == source)
                )
                checkpoint = checkpoint_result.scalar_one_or_none()
                if checkpoint is None:
                    checkpoint = IngestionCheckpoint(source=source)
                    session.add(checkpoint)
                checkpoint.last_sync_date = completed_at
                checkpoint.total_patents_ingested = (
                    (checkpoint.total_patents_ingested or 0) + total_inserted
                )

        return {
            "source": source,
            "total_fetched": total_fetched,
            "total_inserted": total_inserted,
            "total_updated": total_updated,
            "total_errors": total_errors,
        }

    result = _run_async(_run())

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
    from src.utils.logger import logger

    logger.info("task.generate_embeddings.started", task_id=self.request.id)

    async def _run():
        from src.ai.embeddings import embedding_service
        from src.database.connection import get_db_session

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

    processed = _run_async(_run())
    return {"status": "completed", "processed": processed}


@celery_app.task(name="pipeline.generate_watchlist_alerts", bind=True)
def generate_watchlist_alerts_task(self):
    """Background task for generating watchlist alerts."""
    from src.utils.logger import logger

    logger.info("task.watchlist_alerts.started", task_id=self.request.id)

    async def _run():
        from src.database.connection import get_db_session
        from src.services.watchlist_service import watchlist_service

        async with get_db_session() as session:
            return await watchlist_service.generate_alerts_for_all_users(session)

    total_created = _run_async(_run())
    logger.info("task.watchlist_alerts.completed", alerts_created=total_created)
    return {"status": "completed", "alerts_created": total_created}
