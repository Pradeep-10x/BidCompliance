from typing import Any

import pytest
from httpx import AsyncClient

from tests.test_bids import create_bid, create_bidder, create_tender
from tests.test_tenders import auth_headers


def document_payload(
    filename: str = "certificate.pdf", content_hash: str = "a" * 64
) -> dict[str, Any]:
    return {
        "original_filename": filename,
        "document_type": "GST_CERTIFICATE",
        "content_hash": content_hash,
        "storage_path": f"uploads/{filename}",
        "file_size_bytes": 4096,
        "mime_type": "application/pdf",
    }


async def create_document(
    client: AsyncClient,
    headers: dict[str, str],
    tender_id: str,
    bid_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = await client.post(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/documents",
        json=payload or document_payload(),
        headers=headers,
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


@pytest.mark.asyncio
async def test_unauthenticated_document_access_rejected(client: AsyncClient):
    response = await client.get(
        "/api/v1/tenders/00000000-0000-0000-0000-000000000000/"
        "bids/00000000-0000-0000-0000-000000000000/documents"
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_create_document_and_metadata(client: AsyncClient):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)

    document = await create_document(client, headers, tender["id"], bid["id"])

    assert document["bid_id"] == bid["id"]
    assert document["original_filename"] == "certificate.pdf"
    assert document["document_type"] == "GST_CERTIFICATE"
    assert document["content_hash"] == "a" * 64
    assert document["storage_path"] == "uploads/certificate.pdf"
    assert document["file_size_bytes"] == 4096
    assert document["mime_type"] == "application/pdf"
    assert document["processing_status"] == "PENDING"


@pytest.mark.asyncio
async def test_nonexistent_tender_returns_404(client: AsyncClient):
    headers = await auth_headers(client)
    bidder = await create_bidder(client, headers)

    response = await client.post(
        "/api/v1/tenders/00000000-0000-0000-0000-000000000000/"
        "bids/00000000-0000-0000-0000-000000000000/documents",
        json=document_payload(),
        headers=headers,
    )

    assert response.status_code == 404
    assert bidder["id"]


@pytest.mark.asyncio
async def test_nonexistent_bid_returns_404(client: AsyncClient):
    headers = await auth_headers(client)
    tender = await create_tender(client, headers)

    response = await client.post(
        f"/api/v1/tenders/{tender['id']}/bids/00000000-0000-0000-0000-000000000000/documents",
        json=document_payload(),
        headers=headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_documents_and_pagination(client: AsyncClient):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    await create_document(client, headers, tender["id"], bid["id"], document_payload("first.pdf", "1" * 64))
    second = await create_document(
        client, headers, tender["id"], bid["id"], document_payload("second.pdf", "2" * 64)
    )

    response = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/documents?skip=1&limit=1",
        headers=headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["original_filename"] == "first.pdf"
    assert response.json()[0]["id"] != second["id"]


@pytest.mark.asyncio
async def test_authenticated_get_document(client: AsyncClient):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    document = await create_document(client, headers, tender["id"], bid["id"])

    response = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/documents/{document['id']}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == document["id"]


@pytest.mark.asyncio
async def test_nonexistent_document_returns_404(client: AsyncClient):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)

    response = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/documents/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_bid_under_another_tender_returns_404(client: AsyncClient):
    headers = await auth_headers(client)
    tender_a, _, bid_a = await document_context(
        client, headers, "DOC-TENDER-A", "Document Bidder A"
    )
    tender_b = await create_tender(client, headers, "DOC-TENDER-B")
    document = await create_document(client, headers, tender_a["id"], bid_a["id"])

    response = await client.get(
        f"/api/v1/tenders/{tender_b['id']}/bids/{bid_a['id']}/documents/{document['id']}",
        headers=headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_document_under_another_bid_returns_404(client: AsyncClient):
    headers = await auth_headers(client)
    tender, _, bid_a = await document_context(client, headers)
    bidder_b = await create_bidder(client, headers, "Document Bidder B")
    bid_b = await create_bid(client, headers, tender["id"], bidder_b["id"])
    document = await create_document(client, headers, tender["id"], bid_a["id"])

    response = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids/{bid_b['id']}/documents/{document['id']}",
        headers=headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_authenticated_patch_document_is_partial(client: AsyncClient):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    document = await create_document(client, headers, tender["id"], bid["id"])

    response = await client.patch(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/documents/{document['id']}",
        json={"original_filename": "renamed.pdf", "mime_type": "application/octet-stream"},
        headers=headers,
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["original_filename"] == "renamed.pdf"
    assert updated["mime_type"] == "application/octet-stream"
    assert updated["document_type"] == "GST_CERTIFICATE"
    assert updated["content_hash"] == "a" * 64
    assert updated["storage_path"] == "uploads/certificate.pdf"
    assert updated["processing_status"] == "PENDING"
    assert updated["file_size_bytes"] == 4096


@pytest.mark.asyncio
async def test_document_update_rejects_immutable_fields(client: AsyncClient):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    document = await create_document(client, headers, tender["id"], bid["id"])

    for field, value in {
        "content_hash": "b" * 64,
        "storage_path": "uploads/moved.pdf",
        "processing_status": "COMPLETED",
    }.items():
        response = await client.patch(
            f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/documents/{document['id']}",
            json={field: value},
            headers=headers,
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_document_validation_rejects_invalid_hash_and_extra_fields(
    client: AsyncClient,
):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    path = f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/documents"

    invalid_hash = await client.post(
        path, json=document_payload(content_hash="not-a-sha256"), headers=headers
    )
    extra_field = await client.post(
        path, json={**document_payload(), "unknown": True}, headers=headers
    )

    assert invalid_hash.status_code == 422
    assert extra_field.status_code == 422


@pytest.mark.asyncio
async def test_nullable_file_metadata_preserved(client: AsyncClient):
    headers = await auth_headers(client)
    tender, _, bid = await document_context(client, headers)
    payload = document_payload()
    payload["file_size_bytes"] = None
    payload["mime_type"] = None

    document = await create_document(client, headers, tender["id"], bid["id"], payload)

    assert document["file_size_bytes"] is None
    assert document["mime_type"] is None
