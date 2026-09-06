from typing import Any

import pytest
from httpx import AsyncClient

from tests.test_tenders import auth_headers


async def create_tender(
    client: AsyncClient, headers: dict[str, str], reference_number: str = "BID-TENDER"
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/tenders",
        json={"title": "Bid Test Tender", "reference_number": reference_number},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


async def create_bidder(
    client: AsyncClient,
    headers: dict[str, str],
    legal_name: str = "Bid Test Bidder",
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/bidders",
        json={"legal_name": legal_name},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


async def create_bid(
    client: AsyncClient,
    headers: dict[str, str],
    tender_id: str,
    bidder_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = await client.post(
        f"/api/v1/tenders/{tender_id}/bids",
        json={"bidder_id": bidder_id, **(payload or {})},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_unauthenticated_bid_access_rejected(client: AsyncClient):
    response = await client.get(
        "/api/v1/tenders/00000000-0000-0000-0000-000000000000/bids"
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_create_bid_and_decimal_serialization(client: AsyncClient):
    headers = await auth_headers(client)
    tender = await create_tender(client, headers)
    bidder = await create_bidder(client, headers)

    bid = await create_bid(
        client,
        headers,
        tender["id"],
        bidder["id"],
        {"bid_amount": "125000.50"},
    )

    assert bid["tender_id"] == tender["id"]
    assert bid["bidder_id"] == bidder["id"]
    assert bid["bid_amount"] == "125000.50"
    assert bid["status"] == "SUBMITTED"


@pytest.mark.asyncio
async def test_create_bid_under_nonexistent_tender_returns_404(client: AsyncClient):
    headers = await auth_headers(client)
    bidder = await create_bidder(client, headers)

    response = await client.post(
        "/api/v1/tenders/00000000-0000-0000-0000-000000000000/bids",
        json={"bidder_id": bidder["id"]},
        headers=headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_bid_with_nonexistent_bidder_returns_404(client: AsyncClient):
    headers = await auth_headers(client)
    tender = await create_tender(client, headers)

    response = await client.post(
        f"/api/v1/tenders/{tender['id']}/bids",
        json={
            "bidder_id": "00000000-0000-0000-0000-000000000000",
            "bid_amount": "100.00",
        },
        headers=headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_bids_and_pagination(client: AsyncClient):
    headers = await auth_headers(client)
    tender = await create_tender(client, headers)
    first_bidder = await create_bidder(client, headers, "First Bidder")
    second_bidder = await create_bidder(client, headers, "Second Bidder")
    await create_bid(client, headers, tender["id"], first_bidder["id"])
    second_bid = await create_bid(client, headers, tender["id"], second_bidder["id"])

    response = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids?skip=1&limit=1",
        headers=headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] != second_bid["id"]
    assert response.json()[0]["bidder_id"] == first_bidder["id"]


@pytest.mark.asyncio
async def test_authenticated_get_bid(client: AsyncClient):
    headers = await auth_headers(client)
    tender = await create_tender(client, headers)
    bidder = await create_bidder(client, headers)
    bid = await create_bid(client, headers, tender["id"], bidder["id"])

    response = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}", headers=headers
    )

    assert response.status_code == 200
    assert response.json()["id"] == bid["id"]


@pytest.mark.asyncio
async def test_nonexistent_bid_returns_404(client: AsyncClient):
    headers = await auth_headers(client)
    tender = await create_tender(client, headers)

    response = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_wrong_tender_id_does_not_expose_bid(client: AsyncClient):
    headers = await auth_headers(client)
    tender_a = await create_tender(client, headers, "BID-TENDER-A")
    tender_b = await create_tender(client, headers, "BID-TENDER-B")
    bidder = await create_bidder(client, headers)
    bid = await create_bid(client, headers, tender_a["id"], bidder["id"])

    response = await client.get(
        f"/api/v1/tenders/{tender_b['id']}/bids/{bid['id']}", headers=headers
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_authenticated_patch_bid_is_partial(client: AsyncClient):
    headers = await auth_headers(client)
    tender = await create_tender(client, headers)
    bidder = await create_bidder(client, headers)
    bid = await create_bid(
        client,
        headers,
        tender["id"],
        bidder["id"],
        {"bid_amount": "2000.00"},
    )

    response = await client.patch(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}",
        json={"status": "UNDER_REVIEW"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "UNDER_REVIEW"
    assert response.json()["bid_amount"] == "2000.00"
    assert response.json()["bidder_id"] == bidder["id"]


@pytest.mark.asyncio
async def test_duplicate_bidder_tender_bid_returns_409(client: AsyncClient):
    headers = await auth_headers(client)
    tender = await create_tender(client, headers)
    bidder = await create_bidder(client, headers)
    await create_bid(client, headers, tender["id"], bidder["id"])

    response = await client.post(
        f"/api/v1/tenders/{tender['id']}/bids",
        json={"bidder_id": bidder["id"]},
        headers=headers,
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_nullable_bid_amount_preserved(client: AsyncClient):
    headers = await auth_headers(client)
    tender = await create_tender(client, headers)
    bidder = await create_bidder(client, headers)

    bid = await create_bid(client, headers, tender["id"], bidder["id"])

    assert bid["bid_amount"] is None


@pytest.mark.asyncio
async def test_bid_validation_rejects_extra_fields_and_invalid_amount(
    client: AsyncClient,
):
    headers = await auth_headers(client)
    tender = await create_tender(client, headers)
    bidder = await create_bidder(client, headers)
    path = f"/api/v1/tenders/{tender['id']}/bids"

    extra_response = await client.post(
        path,
        json={"bidder_id": bidder["id"], "unknown": True},
        headers=headers,
    )
    invalid_amount_response = await client.post(
        path,
        json={"bidder_id": bidder["id"], "bid_amount": "1.001"},
        headers=headers,
    )

    assert extra_response.status_code == 422
    assert invalid_amount_response.status_code == 422
