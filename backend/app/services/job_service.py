from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.queue import JobPublisher, QueueSubmissionError
from app.models.bid import Bid
from app.models.document import Document
from app.models.processing_job import (
    PipelineStage,
    ProcessingJob,
    ProcessingJobStatus,
)


class JobNotFoundError(Exception):
    pass


def build_initial_payload(
    job_id: UUID, document: Document, bid: Bid, callback_url: str | None = None
) -> dict:
    return {
        "job_id": str(job_id),
        "bid_id": str(bid.id),
        "document_id": str(document.id),
        "page_id": None,
        "page_number": 1,
        "file_type": document.mime_type or document.document_type,
        "image_path": document.storage_path,
        "document_hash": document.content_hash,
        "callback_url": callback_url,
        "pipeline_stage": PipelineStage.CLASSIFICATION.value.lower(),
    }


async def get_document_and_bid(
    db: AsyncSession, document_id: UUID
) -> tuple[Document, Bid] | None:
    result = await db.execute(
        select(Document, Bid)
        .join(Bid, Bid.id == Document.bid_id)
        .where(Document.id == document_id)
    )
    row = result.first()
    return row if row else None


async def create_initial_job(
    db: AsyncSession,
    document_id: UUID,
    publisher: JobPublisher,
    callback_url: str | None = None,
) -> ProcessingJob:
    existing_result = await db.execute(
        select(ProcessingJob).where(
            ProcessingJob.document_id == document_id,
            ProcessingJob.pipeline_stage == PipelineStage.CLASSIFICATION,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        return existing

    context = await get_document_and_bid(db, document_id)
    if context is None:
        raise JobNotFoundError
    document, bid = context
    job = ProcessingJob(
        document_id=document.id,
        job_type="document_processing",
        pipeline_stage=PipelineStage.CLASSIFICATION,
        status=ProcessingJobStatus.PENDING,
        max_attempts=settings.PROCESSING_JOB_MAX_ATTEMPTS,
        payload={},
    )
    db.add(job)
    await db.flush()
    job.payload = build_initial_payload(job.id, document, bid, callback_url)
    try:
        await publisher.publish(job.id, job.payload)
    except QueueSubmissionError as exc:
        job.status = ProcessingJobStatus.FAILED
        job.attempt_count = 1
        job.error_message = str(exc) or "Queue submission failed"
        await db.commit()
        return job

    job.status = ProcessingJobStatus.QUEUED
    job.queued_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job_for_document(
    db: AsyncSession, tender_id: UUID, bid_id: UUID, document_id: UUID, job_id: UUID
) -> ProcessingJob | None:
    result = await db.execute(
        select(ProcessingJob)
        .join(Document, Document.id == ProcessingJob.document_id)
        .join(Bid, Bid.id == Document.bid_id)
        .where(
            ProcessingJob.id == job_id,
            ProcessingJob.document_id == document_id,
            Bid.id == bid_id,
            Bid.tender_id == tender_id,
        )
    )
    return result.scalar_one_or_none()


async def list_document_jobs(
    db: AsyncSession, tender_id: UUID, bid_id: UUID, document_id: UUID
) -> list[ProcessingJob]:
    result = await db.execute(
        select(ProcessingJob)
        .join(Document, Document.id == ProcessingJob.document_id)
        .join(Bid, Bid.id == Document.bid_id)
        .where(
            ProcessingJob.document_id == document_id,
            Bid.id == bid_id,
            Bid.tender_id == tender_id,
        )
        .order_by(ProcessingJob.created_at.desc())
    )
    return list(result.scalars().all())


async def get_job(db: AsyncSession, job_id: UUID) -> ProcessingJob | None:
    return await db.get(ProcessingJob, job_id)


async def retry_job(
    db: AsyncSession, job: ProcessingJob, publisher: JobPublisher
) -> ProcessingJob:
    if job.status != ProcessingJobStatus.FAILED:
        return job
    if job.attempt_count >= job.max_attempts:
        return job
    job.attempt_count += 1
    job.error_message = None
    try:
        await publisher.publish(job.id, job.payload)
    except QueueSubmissionError as exc:
        job.status = ProcessingJobStatus.FAILED
        job.error_message = str(exc) or "Queue submission failed"
    else:
        job.status = ProcessingJobStatus.QUEUED
        job.queued_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)
    return job
