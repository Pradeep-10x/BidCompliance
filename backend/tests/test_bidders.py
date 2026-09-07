from typing import Any

import pytest
from httpx import AsyncClient

from tests.test_tenders import auth_headers


def bidder_payload(legal_name: str = "Acme Supplies") -> dict[str, Any]:
    return {
        "legal_name": legal_name,
        "contact_email": "contact@acme.example",
        "contact_phone": "+919876543210",
        "identifiers": {"pan": "ABCDE1234F", "gstin": "27ABCDE1234F1Z5"},
    }


@pytest.mark.asyncio
async def test_unauthenticated_bidder_access_rejected(client: AsyncClient):
    response = await client.get("/api/v1/bidders")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_create_bidder_and_identifiers_round_trip(
    client: AsyncClient,
):
    headers = await auth_headers(client)
    response = await client.post(
        "/api/v1/bidders", json=bidder_payload(), headers=headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["legal_name"] == "Acme Supplies"
    assert data["identifiers"] == {
        "pan": "ABCDE1234F",
        "gstin": "27ABCDE1234F1Z5",
    }


@pytest.mark.asyncio
async def test_bidder_identifiers_server_default_and_nullable_contacts(
    client: AsyncClient,
):
    headers = await auth_headers(client)
    response = await client.post(
        "/api/v1/bidders",
        json={
            "legal_name": "No Contact Bidder",
            "contact_email": None,
            "contact_phone": None,
        },
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["contact_email"] is None
    assert data["contact_phone"] is None
    assert data["identifiers"] == {}


@pytest.mark.asyncio
async def test_list_bidder_pagination_and_get(client: AsyncClient):
    headers = await auth_headers(client)
    first = await client.post(
        "/api/v1/bidders", json=bidder_payload("First Bidder"), headers=headers
    )
    second = await client.post(
        "/api/v1/bidders", json=bidder_payload("Second Bidder"), headers=headers
    )

    list_response = await client.get(
        "/api/v1/bidders?skip=1&limit=1", headers=headers
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["legal_name"] == "First Bidder"

    bidder_id = second.json()["id"]
    get_response = await client.get(f"/api/v1/bidders/{bidder_id}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["id"] == bidder_id
    assert first.json()["id"] != bidder_id


@pytest.mark.asyncio
async def test_authenticated_patch_bidder_is_partial(client: AsyncClient):
    headers = await auth_headers(client)
    create_response = await client.post(
        "/api/v1/bidders", json=bidder_payload(), headers=headers
    )
    bidder_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/bidders/{bidder_id}",
        json={"legal_name": "Updated Acme"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["legal_name"] == "Updated Acme"
    assert data["contact_email"] == "contact@acme.example"
    assert data["identifiers"]["pan"] == "ABCDE1234F"


@pytest.mark.asyncio
async def test_bidder_validation_rejects_missing_and_extra_fields(client: AsyncClient):
    headers = await auth_headers(client)
    missing_name = await client.post(
        "/api/v1/bidders", json={"contact_email": "missing@example.com"}, headers=headers
    )
    extra_field = await client.post(
        "/api/v1/bidders",
        json={"legal_name": "Unexpected", "unknown": True},
        headers=headers,
    )

    assert missing_name.status_code == 422
    assert extra_field.status_code == 422


@pytest.mark.asyncio
async def test_nonexistent_bidder_get_and_patch_return_404(client: AsyncClient):
    headers = await auth_headers(client)
    bidder_id = "00000000-0000-0000-0000-000000000000"

    get_response = await client.get(f"/api/v1/bidders/{bidder_id}", headers=headers)
    patch_response = await client.patch(
        f"/api/v1/bidders/{bidder_id}",
        json={"legal_name": "Missing"},
        headers=headers,
    )

    assert get_response.status_code == 404
    assert patch_response.status_code == 404
