import hashlib
from typing import Any

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.queue import get_job_publisher
from app.main import app
from app.services.storage_service import LocalFileStorage, StorageError, get_storage_service
from tests.test_bids import create_bid, create_bidder, create_tender
from tests.test_tenders import auth_headers


@pytest.fixture(autouse=True)
def document_storage(tmp_path):
    storage = LocalFileStorage(tmp_path)
    app.dependency_overrides[get_storage_service] = lambda: storage
    app.dependency_overrides[get_job_publisher] = lambda: RecordingPublisher()
    yield storage
    app.dependency_overrides.pop(get_storage_service, None)
    app.dependency_overrides.pop(get_job_publisher, None)


class RecordingPublisher:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.published: list[tuple[str, dict]] = []

    async def publish(self, job_id, payload):
        if self.error:
            from app.core.queue import QueueSubmissionError

            raise QueueSubmissionError(str(self.error))
        self.published.append((str(job_id), payload))


def upload_payload(
    filename: str = "certificate.pdf",
    content: bytes = b"%PDF-1.7\nvalid document bytes",
    content_type: str = "application/pdf",
    document_type: str = "GST_CERTIFICATE",
) -> tuple[dict[str, Any], dict[str, tuple[str, bytes, str]]]:
    return {"document_type": document_type}, {
        "file": (filename, content, content_type),
    }


async def create_document(
    client: AsyncClient,
    headers: dict[str, str],
    tender_id: str,
    bid_id: str,
    filename: str = "certificate.pdf",
    content: bytes = b"%PDF-1.7\nvalid document bytes",
) -> dict[str, Any]:
    data, files = upload_payload(filename, content)
    response = await client.post(
        document_path(tender_id, bid_id), data=data, files=files, headers=headers
    )
    assert response.status_code == 201
    return response.json()


async def document_context(
    client: AsyncClient,
    headers: dict[str, str],
    tender_reference: str = "DOC-TENDER",
    bidder_name: str = "Document Bidder",
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    tender = await create_tender(client, headers, tender_reference)
    bidder = await create_bidder(client, headers, bidder_name)
    bid = await create_bid(client, headers, tender["id"], bidder["id"])
    return tender, bidder, bid


def document_path(tender_id: str, bid_id: str, document_id: str | None = None) -> str:
    path = f"/api/v1/tenders/{tender_id}/bids/{bid_id}/documents"
    return f"{path}/{document_id}" if document_id else path


@pytest.mark.asyncio
async def test_unauthenticated_document_access_rejected(client: AsyncClient):
    response = await client.get(
        document_path(
            "00000000-0000-0000-0000-000000000000",
            "00000000-0000-0000-0000-000000000000",
        )
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_upload_hashes_and_stores_document(client: AsyncClient):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    content = b"%PDF-1.7\nactual uploaded bytes"
    data, files = upload_payload("invoice.pdf", content)

    response = await client.post(
        document_path(tender["id"], bid["id"]),
        data=data,
        files=files,
        headers=headers,
    )

    assert response.status_code == 201
    document = response.json()
    assert document["bid_id"] == bid["id"]
    assert document["original_filename"] == "invoice.pdf"
    assert document["content_hash"] == hashlib.sha256(content).hexdigest()
    assert len(document["content_hash"]) == 64
    assert document["file_size_bytes"] == len(content)
    assert document["mime_type"] == "application/pdf"
    assert document["processing_status"] == "PENDING"
    assert document["storage_path"].startswith("documents/")
    assert "invoice.pdf" not in document["storage_path"]


@pytest.mark.asyncio
async def test_nonexistent_tender_returns_404(client: AsyncClient):
    headers = await auth_headers(client)
    data, files = upload_payload()
    response = await client.post(
        document_path(
            "00000000-0000-0000-0000-000000000000",
            "00000000-0000-0000-0000-000000000000",
        ),
        data=data,
        files=files,
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_nonexistent_bid_returns_404(client: AsyncClient):
    headers = await auth_headers(client)
    tender = await create_tender(client, headers)
    data, files = upload_payload()
    response = await client.post(
        document_path(tender["id"], "00000000-0000-0000-0000-000000000000"),
        data=data,
        files=files,
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_bid_under_another_tender_returns_404(client: AsyncClient):
    headers = await auth_headers(client)
    tender_a, _, bid_a = await document_context(client, headers, "DOC-TENDER-A", "Bidder A")
    tender_b = await create_tender(client, headers, "DOC-TENDER-B")
    data, files = upload_payload()
    response = await client.post(
        document_path(tender_b["id"], bid_a["id"]),
        data=data,
        files=files,
        headers=headers,
    )
    assert response.status_code == 404
    assert tender_a["id"] != tender_b["id"]


@pytest.mark.asyncio
async def test_document_under_another_bid_returns_404(client: AsyncClient):
    headers = await auth_headers(client)
    tender, _, bid_a = await document_context(client, headers)
    bidder_b = await create_bidder(client, headers, "Bidder B")
    bid_b = await create_bid(client, headers, tender["id"], bidder_b["id"])
    document = await create_document(client, headers, tender["id"], bid_a["id"])
    response = await client.get(
        document_path(tender["id"], bid_b["id"], document["id"]), headers=headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unsupported_mime_and_invalid_signature_rejected(client: AsyncClient):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    data, files = upload_payload("script.exe", b"MZ executable", "application/octet-stream")
    unsupported = await client.post(document_path(tender["id"], bid["id"]), data=data, files=files, headers=headers)
    data, files = upload_payload("fake.pdf", b"not a pdf", "application/pdf")
    invalid_signature = await client.post(document_path(tender["id"], bid["id"]), data=data, files=files, headers=headers)
    assert unsupported.status_code == 415
    assert invalid_signature.status_code == 400


@pytest.mark.asyncio
async def test_empty_upload_rejected(client: AsyncClient):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    data, files = upload_payload("empty.pdf", b"", "application/pdf")
    response = await client.post(document_path(tender["id"], bid["id"]), data=data, files=files, headers=headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_maximum_size_enforced(client: AsyncClient, monkeypatch):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 8)
    data, files = upload_payload(content=b"%PDF-1.7\nbytes too large")
    response = await client.post(document_path(tender["id"], bid["id"]), data=data, files=files, headers=headers)
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_upload_does_not_accept_client_hash_or_storage_path(client: AsyncClient):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    content = b"%PDF-1.7\nserver metadata wins"
    data, files = upload_payload("../unsafe.pdf", content)
    data.update({"content_hash": "f" * 64, "storage_path": "../../escape"})
    response = await client.post(document_path(tender["id"], bid["id"]), data=data, files=files, headers=headers)
    document = response.json()
    assert response.status_code == 201
    assert document["content_hash"] == hashlib.sha256(content).hexdigest()
    assert document["storage_path"].startswith("documents/")
    assert ".." not in document["storage_path"]
    assert document["original_filename"] == "unsafe.pdf"


@pytest.mark.asyncio
async def test_list_documents_and_pagination(client: AsyncClient):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    await create_document(client, headers, tender["id"], bid["id"], "first.pdf", b"%PDF-1\nfirst")
    second = await create_document(client, headers, tender["id"], bid["id"], "second.pdf", b"%PDF-1\nsecond")
    response = await client.get(f"{document_path(tender['id'], bid['id'])}?skip=1&limit=1", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["original_filename"] == "first.pdf"
    assert response.json()[0]["id"] != second["id"]


@pytest.mark.asyncio
async def test_authenticated_get_and_nonexistent_document(client: AsyncClient):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    document = await create_document(client, headers, tender["id"], bid["id"])
    get_response = await client.get(document_path(tender["id"], bid["id"], document["id"]), headers=headers)
    missing_response = await client.get(document_path(tender["id"], bid["id"], "00000000-0000-0000-0000-000000000000"), headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["id"] == document["id"]
    assert missing_response.status_code == 404


@pytest.mark.asyncio
async def test_authenticated_patch_is_partial_and_stays_pending(client: AsyncClient):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    document = await create_document(client, headers, tender["id"], bid["id"])
    response = await client.patch(
        document_path(tender["id"], bid["id"], document["id"]),
        json={"original_filename": "renamed.pdf", "mime_type": "application/octet-stream"},
        headers=headers,
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["original_filename"] == "renamed.pdf"
    assert updated["content_hash"] == document["content_hash"]
    assert updated["storage_path"] == document["storage_path"]
    assert updated["processing_status"] == "PENDING"
    assert updated["file_size_bytes"] == document["file_size_bytes"]


@pytest.mark.asyncio
async def test_document_update_rejects_immutable_fields(client: AsyncClient):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    document = await create_document(client, headers, tender["id"], bid["id"])
    path = document_path(tender["id"], bid["id"], document["id"])
    for field, value in {
        "content_hash": "b" * 64,
        "storage_path": "uploads/moved.pdf",
        "processing_status": "COMPLETED",
        "bid_id": "00000000-0000-0000-0000-000000000000",
    }.items():
        response = await client.patch(path, json={field: value}, headers=headers)
        assert response.status_code == 422
    unchanged = await client.get(path, headers=headers)
    assert unchanged.json()["content_hash"] == document["content_hash"]
    assert unchanged.json()["storage_path"] == document["storage_path"]
    assert unchanged.json()["processing_status"] == "PENDING"
    assert unchanged.json()["bid_id"] == bid["id"]


@pytest.mark.asyncio
async def test_storage_failure_does_not_create_document_record(client: AsyncClient, document_storage, monkeypatch):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)

    async def fail_store(*args, **kwargs):
        raise StorageError("storage unavailable")

    monkeypatch.setattr(document_storage, "store", fail_store)
    data, files = upload_payload()
    response = await client.post(document_path(tender["id"], bid["id"]), data=data, files=files, headers=headers)
    assert response.status_code == 500
    listed = await client.get(document_path(tender["id"], bid["id"]), headers=headers)
    assert listed.status_code == 200
    assert listed.json() == []


@pytest.mark.asyncio
async def test_generated_storage_path_exists_in_temporary_storage(
    client: AsyncClient, document_storage
):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    document = await create_document(client, headers, tender["id"], bid["id"])

    stored_path = document_storage.root / document["storage_path"]

    assert stored_path.is_file()


@pytest.mark.asyncio
async def test_upload_skips_job_creation_when_queue_is_disabled(
    client: AsyncClient, monkeypatch
):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    monkeypatch.setattr(settings, "PROCESSING_QUEUE_ENABLED", False)

    document = await create_document(client, headers, tender["id"], bid["id"])
    jobs = await client.get(
        document_path(tender["id"], bid["id"], document["id"]) + "/jobs",
        headers=headers,
    )

    assert jobs.status_code == 200
    assert jobs.json() == []


@pytest.mark.asyncio
async def test_processing_status_failed_is_rejected_and_remains_pending(
    client: AsyncClient,
):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    document = await create_document(client, headers, tender["id"], bid["id"])
    path = document_path(tender["id"], bid["id"], document["id"])

    response = await client.patch(
        path, json={"processing_status": "FAILED"}, headers=headers
    )
    unchanged = await client.get(path, headers=headers)

    assert response.status_code == 422
    assert unchanged.status_code == 200
    assert unchanged.json()["processing_status"] == "PENDING"
