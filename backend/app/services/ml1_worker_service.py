from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bid import Bid
from app.models.document import Document
from app.models.ml_processing_result import MLProcessingResult
from app.models.processing_job import ProcessingJob, ProcessingJobStatus
from app.schemas.ml1 import ML1Request, ML1Response
from app.services.ml1_client import ML1IntegrationError


class ML1InvalidResponseError(ML1IntegrationError):
    pass


def build_ml1_request(job: ProcessingJob, document: Document, bid: Bid) -> ML1Request:
    return ML1Request.model_validate(job.payload)


def validate_response(
    response: ML1Response, job: ProcessingJob, document: Document, bid: Bid
) -> None:
    if (
        response.job_id != job.id
        or response.bid_id != bid.id
        or response.document_id != document.id
    ):
        raise ML1InvalidResponseError("ML-1 response identity does not match job")
    expected_page_id = job.payload.get("page_id")
    if response.page_id != expected_page_id:
        raise ML1InvalidResponseError("ML-1 response page_id does not match job")
    if response.page_number != job.payload.get("page_number"):
        raise ML1InvalidResponseError("ML-1 response page_number does not match job")
    if response.status not in {"success", "failed"}:
        raise ML1InvalidResponseError("ML-1 response status is not recognized")


async def persist_result(
    db: AsyncSession,
    job: ProcessingJob,
    document: Document,
    bid: Bid,
    response: ML1Response,
) -> MLProcessingResult:
    existing_result = await db.execute(
        select(MLProcessingResult).where(MLProcessingResult.job_id == job.id)
    )
    result = existing_result.scalar_one_or_none()
    if result is None:
        result = MLProcessingResult(
            job_id=job.id,
            document_id=document.id,
            bid_id=bid.id,
            module=response.module,
            model_name=response.model_name,
            model_version=response.model_version,
            status=response.status,
            processing_time_ms=response.processing_time_ms,
            result=response.result,
            errors=response.errors,
        )
        db.add(result)
    return result


async def execute_classification_job(
    db: AsyncSession, job_id: UUID, ml1_client
) -> ProcessingJob:
    result = await db.execute(
        select(ProcessingJob, Document, Bid)
        .join(Document, Document.id == ProcessingJob.document_id)
        .join(Bid, Bid.id == Document.bid_id)
        .where(ProcessingJob.id == job_id)
    )
    row = result.first()
    if row is None:
        raise ML1InvalidResponseError("Processing job not found")
    job, document, bid = row
    if job.status == ProcessingJobStatus.COMPLETED:
        return job

    job.status = ProcessingJobStatus.PROCESSING
    job.started_at = datetime.now(timezone.utc)
    job.attempt_count += 1
    await db.commit()

    try:
        request = build_ml1_request(job, document, bid)
        response = await ml1_client.document_intelligence(request)
        validate_response(response, job, document, bid)
        if response.status != "success":
            raise ML1InvalidResponseError("ML-1 returned a failed result")
        await persist_result(db, job, document, bid, response)
    except ML1IntegrationError as exc:
        job.status = ProcessingJobStatus.FAILED
        job.error_message = str(exc)
        await db.commit()
        return job

    job.status = ProcessingJobStatus.COMPLETED
    job.completed_at = datetime.now(timezone.utc)
    job.error_message = None
    await db.commit()
    await db.refresh(job)
    return job
