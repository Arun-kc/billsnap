"""
In-process OCR background worker.
Polls ocr_jobs for pending work, runs extraction, creates bills.
Stuck jobs (processing > OCR_STUCK_JOB_TIMEOUT seconds) are auto-reset on startup.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import AsyncSessionLocal
from ..models.ocr_job import OcrJob
from ..services import bill_service, ocr_service, storage_service

logger = logging.getLogger(__name__)


async def _reset_stuck_jobs(db: AsyncSession) -> None:
    """Reset any jobs that got stuck in 'processing' state (e.g., after a crash)."""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.ocr_stuck_job_timeout)
    await db.execute(
        update(OcrJob)
        .where(OcrJob.status == "processing", OcrJob.started_at < cutoff)
        .values(status="pending", started_at=None)
    )
    await db.commit()


async def _process_job(job: OcrJob, db: AsyncSession) -> None:
    """Run OCR extraction for a single job and create the bill record."""
    try:
        # Mark as processing
        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        await db.commit()

        # Download original image from storage
        image_bytes = storage_service.download(job.original_file_key)

        # Generate thumbnail
        try:
            thumbnail_key = storage_service.upload_thumbnail(job.user_id, job.id, image_bytes)
            job.thumbnail_key = thumbnail_key
        except Exception as e:
            logger.warning("Thumbnail generation failed for job %s: %s", job.id, e)

        # Run OCR
        result = await ocr_service.extract(image_bytes, job.file_content_type)

        # Persist raw response for reprocessing / debugging
        job.raw_ocr_response = result.extracted
        job.extraction_confidence = result.cost_inr  # store cost for monitoring
        job.extraction_notes = result.extracted.get("extraction_notes")
        job.model_tier = "sonnet" if result.model_used == ocr_service.SONNET_MODEL else "haiku"

        # Map text confidence to numeric
        conf_map = {"high": 0.90, "medium": 0.65, "low": 0.35}
        confidence_numeric = conf_map.get(result.confidence, 0.65)
        job.extraction_confidence = confidence_numeric

        # Create bill record
        await bill_service.create_from_ocr(db, job, result.extracted, confidence_numeric)

        job.status = "needs_review" if result.needs_review else "completed"
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()
        logger.info("Job %s completed (%s, confidence=%s)", job.id, result.model_used, result.confidence)

    except Exception as e:
        logger.error("Job %s failed: %s", job.id, e, exc_info=True)
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()


async def run_worker() -> None:
    """Main worker loop — runs forever, polling for pending jobs."""
    logger.info("OCR worker started (poll interval: %ds)", settings.ocr_worker_poll_interval)

    async with AsyncSessionLocal() as db:
        await _reset_stuck_jobs(db)

    while True:
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(OcrJob)
                    .where(OcrJob.status == "pending")
                    .order_by(OcrJob.created_at)
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                job = result.scalar_one_or_none()

                if job:
                    logger.info("Processing job %s (file: %s)", job.id, job.original_file_key)
                    await _process_job(job, db)

        except Exception as e:
            logger.error("Worker loop error: %s", e, exc_info=True)

        await asyncio.sleep(settings.ocr_worker_poll_interval)
