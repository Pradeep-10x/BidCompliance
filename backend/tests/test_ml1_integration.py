import json
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest
from sqlalchemy import select

from app.core.queue import get_job_publisher
from app.main import app
from app.models.ml_processing_result import MLProcessingResult
from app.models.processing_job import ProcessingJob, ProcessingJobStatus
from app.services.ml1_client import ML1Client
from app.services.ml1_worker_service import execute_classification_job
from app.services.storage_service import LocalFileStorage, get_storage_service
from tests.test_documents import create_document, document_context, document_path
from tests.test_tenders import auth_headers


class RecordingPublisher:
    async def publish(self, job_id, payload):
        return None


@pytest.fixture(autouse=True)
def ml1_test_dependencies(tmp_path):
    app.dependency_overrides[get_storage_service] = lambda: LocalFileStorage(tmp_path)
    app.dependency_overrides[get_job_publisher] = lambda: RecordingPublisher()
    yield
    app.dependency_overrides.pop(get_storage_service, None)
    app.dependency_overrides.pop(get_job_publisher, None)


def ml1_response(job: ProcessingJob, payload: dict[str, Any], **overrides) -> dict[str, Any]:
    response = {
        "job_id": str(job.id),
        "bid_id": payload["bid_id"],
        "document_id": payload["document_id"],
        "page_id": payload["page_id"],
        "page_number": payload["page_number"],
        "module": "ml1_document_intelligence",
        "model_name": "paddleocr",
        "model_version": "v1",
        "status": "success",
        "processing_time_ms": 842,
        "result": {"fields": {"invoice_number": "INV-001"}},
        "errors": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    response.update(overrides)
    return response


async def job_context(client: httpx.AsyncClient, db_session):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    document = await create_document(client, headers, tender["id"], bid["id"])
    job = (
        await db_session.execute(
            select(ProcessingJob).where(ProcessingJob.document_id == document["id"])
        )
    ).scalar_one()
    return headers, tender, bid, document, job


@pytest.mark.asyncio
async def test_successful_worker_execution_persists_result_and_completes_job(
    client, db_session
):
    _, _, _, document, job = await job_context(client, db_session)

    async def handler(request: httpx.Request):
        payload = json.loads(request.content)
        return httpx.Response(200, json=ml1_response(job, payload))

    ml1 = ML1Client(httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://ml1.test"
    ))
    completed = await execute_classification_job(db_session, job.id, ml1)

    result = (
        await db_session.execute(
            select(MLProcessingResult).where(MLProcessingResult.job_id == job.id)
        )
    ).scalar_one()
    assert completed.status == ProcessingJobStatus.COMPLETED
    assert str(result.document_id) == document["id"]
    assert result.status == "success"
    assert result.result["fields"]["invoice_number"] == "INV-001"


@pytest.mark.asyncio
async def test_worker_sends_exact_ml1_payload(client, db_session):
    _, _, _, _, job = await job_context(client, db_session)
    captured: dict[str, Any] = {}

    async def handler(request: httpx.Request):
        captured.update(json.loads(request.content))
        return httpx.Response(200, json=ml1_response(job, captured))

    ml1 = ML1Client(httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://ml1.test"
    ))
    await execute_classification_job(db_session, job.id, ml1)

    assert captured == job.payload


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["job_id", "document_id", "bid_id"])
async def test_mismatched_ml1_identity_fails_job(client, db_session, field):
    _, _, _, _, job = await job_context(client, db_session)

    async def handler(request: httpx.Request):
        payload = json.loads(request.content)
        response = ml1_response(job, payload)
        response[field] = "00000000-0000-0000-0000-000000000000"
        return httpx.Response(200, json=response)

    ml1 = ML1Client(httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ml1.test"))
    failed = await execute_classification_job(db_session, job.id, ml1)

    assert failed.status == ProcessingJobStatus.FAILED
    assert "does not match" in failed.error_message
    assert failed.completed_at is None


@pytest.mark.asyncio
async def test_ml_error_response_does_not_complete_job(client, db_session):
    _, _, _, _, job = await job_context(client, db_session)

    async def handler(request: httpx.Request):
        payload = json.loads(request.content)
        return httpx.Response(200, json=ml1_response(job, payload, status="failed", errors=[{"code": "OCR_ERROR"}]))

    ml1 = ML1Client(httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ml1.test"))
    failed = await execute_classification_job(db_session, job.id, ml1)

    assert failed.status == ProcessingJobStatus.FAILED
    assert failed.completed_at is None
    assert (
        await db_session.execute(
            select(MLProcessingResult).where(MLProcessingResult.job_id == job.id)
        )
    ).scalar_one_or_none() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exception", [httpx.ConnectError("connection failed"), httpx.ReadTimeout("timeout")]
)
async def test_ml_transport_failures_fail_job_without_completion(client, db_session, exception):
    _, _, _, _, job = await job_context(client, db_session)

    async def handler(request: httpx.Request):
        raise exception

    ml1 = ML1Client(httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ml1.test"))
    failed = await execute_classification_job(db_session, job.id, ml1)

    assert failed.status == ProcessingJobStatus.FAILED
    assert failed.completed_at is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body", [{"unexpected": True}, "not-json-object"]
)
async def test_invalid_ml1_response_schema_fails_job(client, db_session, body):
    _, _, _, _, job = await job_context(client, db_session)

    async def handler(request: httpx.Request):
        return httpx.Response(200, json=body)

    ml1 = ML1Client(httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ml1.test"))
    failed = await execute_classification_job(db_session, job.id, ml1)

    assert failed.status == ProcessingJobStatus.FAILED
    assert failed.completed_at is None


@pytest.mark.asyncio
async def test_invalid_json_response_fails_job(client, db_session):
    _, _, _, _, job = await job_context(client, db_session)

    async def handler(request: httpx.Request):
        return httpx.Response(200, content=b"not-json", headers={"content-type": "application/json"})

    ml1 = ML1Client(httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ml1.test"))
    failed = await execute_classification_job(db_session, job.id, ml1)

    assert failed.status == ProcessingJobStatus.FAILED


@pytest.mark.asyncio
async def test_successful_retry_does_not_duplicate_result(client, db_session):
    _, _, _, _, job = await job_context(client, db_session)
    calls = 0

    async def handler(request: httpx.Request):
        nonlocal calls
        calls += 1
        payload = json.loads(request.content)
        return httpx.Response(200, json=ml1_response(job, payload))

    ml1 = ML1Client(httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ml1.test"))
    await execute_classification_job(db_session, job.id, ml1)
    await execute_classification_job(db_session, job.id, ml1)
    results = await db_session.execute(
        select(MLProcessingResult).where(MLProcessingResult.job_id == job.id)
    )

    assert calls == 1
    assert len(results.scalars().all()) == 1
