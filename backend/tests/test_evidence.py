import json
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest
from sqlalchemy import select

from app.core.queue import get_job_publisher
from app.main import app
from app.models.evidence import Evidence
from app.models.ml_processing_result import MLProcessingResult
from app.models.processing_job import ProcessingJob, ProcessingJobStatus
from app.services.ml1_client import ML1Client
from app.services.ml1_worker_service import execute_classification_job
from app.services.storage_service import LocalFileStorage, get_storage_service
from tests.test_documents import create_document, document_context
from tests.test_ml1_integration import RecordingPublisher, job_context, ml1_response
from tests.test_tenders import auth_headers


@pytest.fixture(autouse=True)
def evidence_test_dependencies(tmp_path):
    app.dependency_overrides[get_storage_service] = lambda: LocalFileStorage(tmp_path)
    app.dependency_overrides[get_job_publisher] = lambda: RecordingPublisher()
    yield
    app.dependency_overrides.pop(get_storage_service, None)
    app.dependency_overrides.pop(get_job_publisher, None)


@pytest.mark.asyncio
async def test_successful_ml_result_creates_evidence(client, db_session):
    headers, tender, bid, document, job = await job_context(client, db_session)

    fields = [
        {
            "field": "enterprise_name",
            "value": "ABC ENGINEERING PVT LTD",
            "value_normalized": "ABC ENGINEERING PRIVATE LIMITED",
            "confidence": 0.99,
            "page": 1,
            "bounding_box": [120, 340, 650, 380],
            "extraction_method": "ocr_anchor",
            "source_text": "Name of Enterprise: ABC ENGINEERING PVT LTD",
            "evidence_id": "ev_udyam_name_001",
        }
    ]

    async def handler(request: httpx.Request):
        payload = json.loads(request.content)
        return httpx.Response(200, json=ml1_response(job, payload, result={"fields": fields}))

    ml1 = ML1Client(
        httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ml1.test")
    )
    completed_job = await execute_classification_job(db_session, job.id, ml1)
    assert completed_job.status == ProcessingJobStatus.COMPLETED

    evidence_rows = (
        await db_session.execute(
            select(Evidence).where(Evidence.document_id == document["id"])
        )
    ).scalars().all()

    assert len(evidence_rows) == 1
    ev = evidence_rows[0]
    assert ev.field_name == "enterprise_name"
    assert ev.value == "ABC ENGINEERING PVT LTD"
    assert ev.value_normalized == "ABC ENGINEERING PRIVATE LIMITED"
    assert ev.confidence == 0.99
    assert ev.page_number == 1
    assert ev.bounding_box == [120, 340, 650, 380]
    assert ev.source_text == "Name of Enterprise: ABC ENGINEERING PVT LTD"
    assert ev.extraction_method == "ocr_anchor"
    assert ev.source_evidence_id == "ev_udyam_name_001"
    assert ev.evidence_id.startswith("ev_")
    assert str(ev.document_id) == document["id"]
    assert ev.evidence_type == "ML_EXTRACTION"


@pytest.mark.asyncio
async def test_multiple_extracted_fields_preserve_all_attributes(client, db_session):
    headers, tender, bid, document, job = await job_context(client, db_session)

    fields = [
        {
            "field": "enterprise_name",
            "value": "ABC ENGINEERING PVT LTD",
            "value_normalized": "ABC ENGINEERING PRIVATE LIMITED",
            "confidence": 0.99,
            "page": 1,
            "bounding_box": [120, 340, 650, 380],
            "extraction_method": "ocr_anchor",
            "source_text": "Name of Enterprise: ABC ENGINEERING PVT LTD",
            "evidence_id": "ev_udyam_name_001",
        },
        {
            "field": "gstin",
            "value": "09ABCDE1234F1Z5",
            "value_normalized": "09ABCDE1234F1Z5",
            "confidence": 0.96,
            "page": 1,
            "bounding_box": [120, 200, 520, 235],
            "extraction_method": "ocr_anchor",
            "source_text": "GSTIN: 09ABCDE1234F1Z5",
            "evidence_id": "ev_gst_001",
        },
        {
            "field": "pan",
            "value": "ABCDE1234F",
            "value_normalized": "ABCDE1234F",
            "confidence": 0.92,
            "page": 2,
            "bounding_box": None,
            "extraction_method": "regex",
            "source_text": "PAN: ABCDE1234F",
            "evidence_id": "ev_pan_001",
        },
    ]

    async def handler(request: httpx.Request):
        payload = json.loads(request.content)
        return httpx.Response(200, json=ml1_response(job, payload, result={"fields": fields}))

    ml1 = ML1Client(
        httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ml1.test")
    )
    await execute_classification_job(db_session, job.id, ml1)

    # Fetch through API
    response = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/documents/{document['id']}/evidence",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

    fields_by_name = {item["field_name"]: item for item in data}
    assert set(fields_by_name.keys()) == {"enterprise_name", "gstin", "pan"}

    # 1. enterprise_name
    ent = fields_by_name["enterprise_name"]
    assert ent["value"] == "ABC ENGINEERING PVT LTD"
    assert ent["value_normalized"] == "ABC ENGINEERING PRIVATE LIMITED"
    assert ent["confidence"] == 0.99
    assert ent["page_number"] == 1
    assert ent["bounding_box"] == [120, 340, 650, 380]
    assert ent["source_text"] == "Name of Enterprise: ABC ENGINEERING PVT LTD"
    assert ent["extraction_method"] == "ocr_anchor"
    assert ent["source_evidence_id"] == "ev_udyam_name_001"

    # 2. gstin
    gst = fields_by_name["gstin"]
    assert gst["value"] == "09ABCDE1234F1Z5"
    assert gst["confidence"] == 0.96
    assert gst["page_number"] == 1
    assert gst["bounding_box"] == [120, 200, 520, 235]
    assert gst["source_text"] == "GSTIN: 09ABCDE1234F1Z5"
    assert gst["source_evidence_id"] == "ev_gst_001"

    # 3. pan
    pan = fields_by_name["pan"]
    assert pan["value"] == "ABCDE1234F"
    assert pan["confidence"] == 0.92
    assert pan["page_number"] == 2
    assert pan["bounding_box"] is None
    assert pan["extraction_method"] == "regex"
    assert pan["source_evidence_id"] == "ev_pan_001"


@pytest.mark.asyncio
async def test_evidence_id_traceability_via_api(client, db_session):
    headers, tender, bid, document, job = await job_context(client, db_session)

    fields = [
        {
            "field": "enterprise_name",
            "value": "ABC ENGINEERING PVT LTD",
            "confidence": 0.99,
            "page": 1,
            "evidence_id": "ev_udyam_name_001",
        }
    ]

    async def handler(request: httpx.Request):
        payload = json.loads(request.content)
        return httpx.Response(200, json=ml1_response(job, payload, result={"fields": fields}))

    ml1 = ML1Client(
        httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ml1.test")
    )
    await execute_classification_job(db_session, job.id, ml1)

    list_resp = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/documents/{document['id']}/evidence",
        headers=headers,
    )
    assert list_resp.status_code == 200
    evidence_item = list_resp.json()[0]
    db_uuid = evidence_item["id"]
    auth_ev_id = evidence_item["evidence_id"]
    source_ev_id = evidence_item["source_evidence_id"]

    # Resolve by UUID
    res_uuid = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/documents/{document['id']}/evidence/{db_uuid}",
        headers=headers,
    )
    assert res_uuid.status_code == 200
    assert res_uuid.json()["id"] == db_uuid

    # Resolve by Authoritative Evidence ID
    res_auth = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/documents/{document['id']}/evidence/{auth_ev_id}",
        headers=headers,
    )
    assert res_auth.status_code == 200
    assert res_auth.json()["id"] == db_uuid

    # Resolve by Source ML Evidence ID
    res_src = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/documents/{document['id']}/evidence/{source_ev_id}",
        headers=headers,
    )
    assert res_src.status_code == 200
    assert res_src.json()["id"] == db_uuid


@pytest.mark.asyncio
async def test_duplicate_successful_worker_retry_does_not_duplicate_evidence(
    client, db_session
):
    headers, tender, bid, document, job = await job_context(client, db_session)

    fields = [
        {"field": "enterprise_name", "value": "ABC ENGINEERING PVT LTD"},
        {"field": "gstin", "value": "09ABCDE1234F1Z5"},
    ]

    async def handler(request: httpx.Request):
        payload = json.loads(request.content)
        return httpx.Response(200, json=ml1_response(job, payload, result={"fields": fields}))

    ml1 = ML1Client(
        httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ml1.test")
    )
    await execute_classification_job(db_session, job.id, ml1)
    await execute_classification_job(db_session, job.id, ml1)

    evidence_rows = (
        await db_session.execute(
            select(Evidence).where(Evidence.document_id == document["id"])
        )
    ).scalars().all()

    assert len(evidence_rows) == 2


@pytest.mark.asyncio
async def test_malformed_field_data_handled_safely_partial_ingestion(client, db_session):
    headers, tender, bid, document, job = await job_context(client, db_session)

    fields = [
        {"field": "valid_field", "value": "Valid Value", "confidence": 0.95},
        {"field": "", "value": "Empty field name"},
        {"field": "invalid_conf", "value": "Val", "confidence": 99.0},
        {"field": "invalid_page", "value": "Val", "page": -5},
        {"field": "invalid_bbox", "value": "Val", "bounding_box": "not-a-list"},
        "not-a-dict",
    ]

    async def handler(request: httpx.Request):
        payload = json.loads(request.content)
        return httpx.Response(200, json=ml1_response(job, payload, result={"fields": fields}))

    ml1 = ML1Client(
        httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ml1.test")
    )
    completed = await execute_classification_job(db_session, job.id, ml1)

    assert completed.status == ProcessingJobStatus.COMPLETED

    # Check evidence rows: Only the valid field should be persisted
    evidence_rows = (
        await db_session.execute(
            select(Evidence).where(Evidence.document_id == document["id"])
        )
    ).scalars().all()
    assert len(evidence_rows) == 1
    assert evidence_rows[0].field_name == "valid_field"

    # Check ML processing result errors: Malformed field errors are clearly preserved
    ml_result = (
        await db_session.execute(
            select(MLProcessingResult).where(MLProcessingResult.job_id == job.id)
        )
    ).scalar_one()
    assert ml_result.status == "success"  # Unmodified ML status
    assert len(ml_result.errors) == 5  # 5 malformed items
    error_codes = [err["code"] for err in ml_result.errors]
    assert all(code == "MALFORMED_FIELD" for code in error_codes)


@pytest.mark.asyncio
async def test_ownership_protection_returns_404(client, db_session):
    headers, tender, bid, document, job = await job_context(client, db_session)

    fields = [{"field": "enterprise_name", "value": "ABC ENGINEERING PVT LTD"}]

    async def handler(request: httpx.Request):
        payload = json.loads(request.content)
        return httpx.Response(200, json=ml1_response(job, payload, result={"fields": fields}))

    ml1 = ML1Client(
        httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ml1.test")
    )
    await execute_classification_job(db_session, job.id, ml1)

    random_id = str(uuid.uuid4())

    # 1. Wrong tender
    res = await client.get(
        f"/api/v1/tenders/{random_id}/bids/{bid['id']}/documents/{document['id']}/evidence",
        headers=headers,
    )
    assert res.status_code == 404

    # 2. Wrong bid
    res = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids/{random_id}/documents/{document['id']}/evidence",
        headers=headers,
    )
    assert res.status_code == 404

    # 3. Wrong document
    res = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/documents/{random_id}/evidence",
        headers=headers,
    )
    assert res.status_code == 404

    # 4. Wrong evidence
    res = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/documents/{document['id']}/evidence/{random_id}",
        headers=headers,
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_evidence_access_rejected(client, db_session):
    _, tender, bid, document, job = await job_context(client, db_session)

    res_list = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/documents/{document['id']}/evidence"
    )
    assert res_list.status_code == 401

    res_single = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/documents/{document['id']}/evidence/{uuid.uuid4()}"
    )
    assert res_single.status_code == 401


@pytest.mark.asyncio
async def test_post_and_patch_evidence_not_supported(client, db_session):
    headers, tender, bid, document, _ = await job_context(client, db_session)

    # POST evidence -> 405 Method Not Allowed
    post_res = await client.post(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/documents/{document['id']}/evidence",
        json={"field": "test", "value": "val"},
        headers=headers,
    )
    assert post_res.status_code == 405

    # PATCH evidence -> 405 Method Not Allowed
    patch_res = await client.patch(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/documents/{document['id']}/evidence/{uuid.uuid4()}",
        json={"value": "new_val"},
        headers=headers,
    )
    assert patch_res.status_code == 405


@pytest.mark.asyncio
async def test_legacy_dict_fields_format_supported(client, db_session):
    headers, tender, bid, document, job = await job_context(client, db_session)

    # Legacy test format: {"fields": {"invoice_number": "INV-001"}}
    async def handler(request: httpx.Request):
        payload = json.loads(request.content)
        return httpx.Response(200, json=ml1_response(job, payload, result={"fields": {"invoice_number": "INV-001"}}))

    ml1 = ML1Client(
        httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ml1.test")
    )
    await execute_classification_job(db_session, job.id, ml1)

    evidence_rows = (
        await db_session.execute(
            select(Evidence).where(Evidence.document_id == document["id"])
        )
    ).scalars().all()

    assert len(evidence_rows) == 1
    assert evidence_rows[0].field_name == "invoice_number"
    assert evidence_rows[0].value == "INV-001"
