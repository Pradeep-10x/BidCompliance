from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.queue import QueueSubmissionError, get_job_publisher
from app.main import app
from app.models.processing_job import ProcessingJobStatus
from app.models.processing_job import ProcessingJob
from app.services.job_service import create_initial_job, retry_job
from app.services.storage_service import LocalFileStorage, get_storage_service
from tests.test_documents import create_document, document_context, document_path
from tests.test_tenders import auth_headers


class RecordingPublisher:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.published: list[tuple[str, dict[str, Any]]] = []

    async def publish(self, job_id, payload):
        if self.error:
            raise QueueSubmissionError(str(self.error))
        self.published.append((str(job_id), payload))


@pytest.fixture(autouse=True)
def job_storage(tmp_path):
    storage = LocalFileStorage(tmp_path)
    app.dependency_overrides[get_storage_service] = lambda: storage
    yield storage
    app.dependency_overrides.pop(get_storage_service, None)


@pytest.fixture(autouse=True)
def job_publisher():
    publisher = RecordingPublisher()
    app.dependency_overrides[get_job_publisher] = lambda: publisher
    yield publisher
    app.dependency_overrides.pop(get_job_publisher, None)


@pytest.mark.asyncio
async def test_unauthenticated_job_access_rejected(client: AsyncClient):
    response = await client.get(
        document_path(
            "00000000-0000-0000-0000-000000000000",
            "00000000-0000-0000-0000-000000000000",
            "00000000-0000-0000-0000-000000000000",
        )
        + "/jobs"
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_creates_queued_job_with_ml_shape_payload(
    client: AsyncClient, job_publisher: RecordingPublisher
):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    document = await create_document(client, headers, tender["id"], bid["id"])

    response = await client.get(
        document_path(tender["id"], bid["id"], document["id"]) + "/jobs",
        headers=headers,
    )

    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) == 1
    job = jobs[0]
    assert job["status"] == "QUEUED"
    assert job["attempt_count"] == 0
    assert job["pipeline_stage"] == "CLASSIFICATION"
    payload = job["payload"]
    assert payload["document_id"] == document["id"]
    assert payload["bid_id"] == bid["id"]
    assert payload["file_type"] == "application/pdf"
    assert payload["image_path"] == document["storage_path"]
    assert payload["document_hash"] == document["content_hash"]
    assert payload["pipeline_stage"] == "classification"
    assert len(job_publisher.published) == 1


@pytest.mark.asyncio
async def test_initial_classification_payload_contains_complete_contract(
    client: AsyncClient,
):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    document = await create_document(client, headers, tender["id"], bid["id"])
    response = await client.get(
        document_path(tender["id"], bid["id"], document["id"]) + "/jobs",
        headers=headers,
    )

    payload = response.json()[0]["payload"]

    assert set(payload) == {
        "job_id",
        "bid_id",
        "document_id",
        "page_id",
        "page_number",
        "file_type",
        "image_path",
        "document_hash",
        "callback_url",
        "pipeline_stage",
    }
    assert payload["job_id"] == response.json()[0]["id"]
    assert payload["bid_id"] == bid["id"]
    assert payload["document_id"] == document["id"]
    assert payload["page_id"] is None
    assert payload["page_number"] == 1
    assert payload["file_type"] == document["mime_type"]
    assert payload["image_path"] == document["storage_path"]
    assert payload["document_hash"] == document["content_hash"]
    assert payload["callback_url"] is None
    assert payload["pipeline_stage"] == "classification"


@pytest.mark.asyncio
async def test_direct_initial_job_creation_is_idempotent(
    client: AsyncClient, db_session, job_publisher: RecordingPublisher
):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    document = await create_document(client, headers, tender["id"], bid["id"])
    publisher_calls_before = len(job_publisher.published)

    first = await create_initial_job(db_session, document["id"], job_publisher)
    second = await create_initial_job(db_session, document["id"], job_publisher)
    rows = await db_session.execute(
        select(ProcessingJob).where(ProcessingJob.document_id == document["id"])
    )

    assert first.id == second.id
    assert len(rows.scalars().all()) == 1
    assert len(job_publisher.published) == publisher_calls_before


@pytest.mark.asyncio
async def test_non_terminal_retry_publishes_and_failed_retry_stays_failed(
    client: AsyncClient, db_session, job_publisher: RecordingPublisher
):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    document = await create_document(client, headers, tender["id"], bid["id"])
    job = await db_session.get(
        ProcessingJob,
        (
            await db_session.execute(
                select(ProcessingJob.id).where(
                    ProcessingJob.document_id == document["id"]
                )
            )
        ).scalar_one(),
    )
    job.status = ProcessingJobStatus.FAILED
    job.attempt_count = 1
    await db_session.commit()
    published_before_retry = len(job_publisher.published)

    retried = await retry_job(db_session, job, job_publisher)

    assert retried.attempt_count == 2
    assert retried.status == ProcessingJobStatus.QUEUED
    assert len(job_publisher.published) == published_before_retry + 1

    failing_publisher = RecordingPublisher(error=RuntimeError("retry unavailable"))
    retried.status = ProcessingJobStatus.FAILED
    await db_session.commit()
    failed_retry = await retry_job(db_session, retried, failing_publisher)

    assert failed_retry.status == ProcessingJobStatus.FAILED
    assert failed_retry.attempt_count == 3
    assert failed_retry.error_message == "retry unavailable"


@pytest.mark.asyncio
async def test_public_job_patch_cannot_mutate_processing_status(client: AsyncClient):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    document = await create_document(client, headers, tender["id"], bid["id"])
    jobs = await client.get(
        document_path(tender["id"], bid["id"], document["id"]) + "/jobs",
        headers=headers,
    )
    job_id = jobs.json()[0]["id"]
    path = document_path(tender["id"], bid["id"], document["id"]) + f"/jobs/{job_id}"

    responses = [
        await client.patch(path, json={"status": "COMPLETED"}, headers=headers),
        await client.patch(path, json={"status": "FAILED"}, headers=headers),
    ]
    unchanged = await client.get(path, headers=headers)

    assert all(response.status_code in {404, 405, 422} for response in responses)
    assert all(response.status_code < 500 for response in responses)
    assert unchanged.status_code == 200
    assert unchanged.json()["status"] == "QUEUED"


@pytest.mark.asyncio
async def test_job_creation_is_idempotent(client: AsyncClient):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    document = await create_document(client, headers, tender["id"], bid["id"])

    first = await client.get(
        document_path(tender["id"], bid["id"], document["id"]) + "/jobs",
        headers=headers,
    )
    second = await client.get(
        document_path(tender["id"], bid["id"], document["id"]) + "/jobs",
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(first.json()) == len(second.json()) == 1
    assert first.json()[0]["id"] == second.json()[0]["id"]


@pytest.mark.asyncio
async def test_job_detail_and_missing_job_return_404(client: AsyncClient):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    document = await create_document(client, headers, tender["id"], bid["id"])
    jobs = await client.get(
        document_path(tender["id"], bid["id"], document["id"]) + "/jobs",
        headers=headers,
    )
    job_id = jobs.json()[0]["id"]

    detail = await client.get(
        document_path(tender["id"], bid["id"], document["id"]) + f"/jobs/{job_id}",
        headers=headers,
    )
    missing = await client.get(
        document_path(tender["id"], bid["id"], document["id"])
        + "/jobs/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert detail.status_code == 200
    assert detail.json()["id"] == job_id
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_job_cross_tender_and_cross_bid_isolation(client: AsyncClient):
    headers = await auth_headers(client)
    tender_a, _, bid_a = await document_context(client, headers, "JOB-TENDER-A", "Job Bidder A")
    tender_b, _, bid_b = await document_context(client, headers, "JOB-TENDER-B", "Job Bidder B")
    document = await create_document(client, headers, tender_a["id"], bid_a["id"])
    jobs = await client.get(
        document_path(tender_a["id"], bid_a["id"], document["id"]) + "/jobs",
        headers=headers,
    )
    job_id = jobs.json()[0]["id"]

    wrong_tender = await client.get(
        document_path(tender_b["id"], bid_a["id"], document["id"]) + f"/jobs/{job_id}",
        headers=headers,
    )
    wrong_bid = await client.get(
        document_path(tender_a["id"], bid_b["id"], document["id"]) + f"/jobs/{job_id}",
        headers=headers,
    )

    assert wrong_tender.status_code == 404
    assert wrong_bid.status_code == 404


@pytest.mark.asyncio
async def test_queue_failure_marks_job_failed_and_document_stays_pending(
    client: AsyncClient,
):
    publisher = RecordingPublisher(error=RuntimeError("redis unavailable"))
    app.dependency_overrides[get_job_publisher] = lambda: publisher
    try:
        headers = await auth_headers(client)
        tender, _, bid = await document_context(client, headers)
        document = await create_document(client, headers, tender["id"], bid["id"])
        jobs = await client.get(
            document_path(tender["id"], bid["id"], document["id"]) + "/jobs",
            headers=headers,
        )
        document_response = await client.get(
            document_path(tender["id"], bid["id"], document["id"]),
            headers=headers,
        )
    finally:
        app.dependency_overrides.pop(get_job_publisher, None)

    assert jobs.status_code == 200
    assert jobs.json()[0]["status"] == "FAILED"
    assert jobs.json()[0]["attempt_count"] == 1
    assert document_response.json()["processing_status"] == "PENDING"


@pytest.mark.asyncio
async def test_retry_is_bounded_and_terminal_failure_is_preserved(
    client: AsyncClient, db_session
):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    document = await create_document(client, headers, tender["id"], bid["id"])
    jobs = await client.get(
        document_path(tender["id"], bid["id"], document["id"]) + "/jobs",
        headers=headers,
    )
    job_id = jobs.json()[0]["id"]
    from app.models.processing_job import ProcessingJob

    job = await db_session.get(ProcessingJob, job_id)
    job.status = ProcessingJobStatus.FAILED
    job.attempt_count = job.max_attempts
    await db_session.commit()
    retried = await retry_job(db_session, job, RecordingPublisher())

    assert retried.status == ProcessingJobStatus.FAILED
    assert retried.attempt_count == retried.max_attempts
