import pytest
from httpx import AsyncClient


async def auth_headers(client: AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "tender-user@example.com",
            "password": "Password123!",
            "full_name": "Tender User",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "tender-user@example.com", "password": "Password123!"},
    )
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}


def tender_payload(reference_number: str = "TND-001") -> dict[str, object]:
    return {
        "title": "Office Equipment Procurement",
        "description": "Laptops and monitors",
        "reference_number": reference_number,
        "budget": "500000.00",
        "opening_date": "2026-09-10T09:00:00Z",
        "closing_date": "2026-09-20T17:00:00Z",
    }


@pytest.mark.asyncio
async def test_unauthenticated_tender_access_rejected(client: AsyncClient):
    response = await client.get("/api/v1/tenders")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_create_tender(client: AsyncClient):
    headers = await auth_headers(client)
    response = await client.post(
        "/api/v1/tenders", json=tender_payload(), headers=headers
    )
    assert response.status_code == 201
    assert response.json()["reference_number"] == "TND-001"
    assert response.json()["status"] == "DRAFT"


@pytest.mark.asyncio
async def test_list_and_get_tenders(client: AsyncClient):
    headers = await auth_headers(client)
    await client.post(
        "/api/v1/tenders", json=tender_payload(), headers=headers
    )
    create_response = await client.post(
        "/api/v1/tenders",
        json=tender_payload("TND-002"),
        headers=headers,
    )

    list_response = await client.get(
        "/api/v1/tenders?skip=1&limit=1", headers=headers
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["reference_number"] == "TND-001"

    tender_id = create_response.json()["id"]
    get_response = await client.get(f"/api/v1/tenders/{tender_id}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["reference_number"] == "TND-002"


@pytest.mark.asyncio
async def test_authenticated_get_tender(client: AsyncClient):
    headers = await auth_headers(client)
    create_response = await client.post(
        "/api/v1/tenders", json=tender_payload(), headers=headers
    )
    tender_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/tenders/{tender_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == tender_id


@pytest.mark.asyncio
async def test_get_nonexistent_tender(client: AsyncClient):
    headers = await auth_headers(client)
    response = await client.get(
        "/api/v1/tenders/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_tender_and_partial_update(client: AsyncClient):
    headers = await auth_headers(client)
    create_response = await client.post(
        "/api/v1/tenders", json=tender_payload(), headers=headers
    )
    tender_id = create_response.json()["id"]

    update_response = await client.patch(
        f"/api/v1/tenders/{tender_id}",
        json={"title": "Updated Procurement", "status": "PUBLISHED"},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated Procurement"
    assert update_response.json()["status"] == "PUBLISHED"
    assert update_response.json()["description"] == "Laptops and monitors"


@pytest.mark.asyncio
async def test_authenticated_patch_tender(client: AsyncClient):
    headers = await auth_headers(client)
    create_response = await client.post(
        "/api/v1/tenders", json=tender_payload(), headers=headers
    )
    tender_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/tenders/{tender_id}",
        json={"title": "Authenticated Update"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Authenticated Update"


@pytest.mark.asyncio
async def test_duplicate_reference_number_rejected(client: AsyncClient):
    headers = await auth_headers(client)
    payload = tender_payload()
    assert (await client.post("/api/v1/tenders", json=payload, headers=headers)).status_code == 201
    response = await client.post("/api/v1/tenders", json=payload, headers=headers)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_duplicate_reference_number_on_patch_rejected(client: AsyncClient):
    headers = await auth_headers(client)
    tender_a = await client.post(
        "/api/v1/tenders", json=tender_payload("T-001"), headers=headers
    )
    tender_b = await client.post(
        "/api/v1/tenders", json=tender_payload("T-002"), headers=headers
    )
    tender_b_id = tender_b.json()["id"]

    response = await client.patch(
        f"/api/v1/tenders/{tender_b_id}",
        json={"reference_number": tender_a.json()["reference_number"]},
        headers=headers,
    )

    assert response.status_code == 409
    unchanged_response = await client.get(
        f"/api/v1/tenders/{tender_b_id}", headers=headers
    )
    assert unchanged_response.status_code == 200
    assert unchanged_response.json()["reference_number"] == "T-002"


@pytest.mark.asyncio
async def test_invalid_date_range_on_create_rejected(client: AsyncClient):
    headers = await auth_headers(client)
    payload = tender_payload()
    payload["opening_date"] = "2026-09-20T09:00:00Z"
    payload["closing_date"] = "2026-09-10T17:00:00Z"

    response = await client.post("/api/v1/tenders", json=payload, headers=headers)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_date_range_on_partial_update_rejected(client: AsyncClient):
    headers = await auth_headers(client)
    create_response = await client.post(
        "/api/v1/tenders", json=tender_payload(), headers=headers
    )
    tender_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/tenders/{tender_id}",
        json={"opening_date": "2026-09-21T09:00:00Z"},
        headers=headers,
    )

    assert response.status_code == 422
    unchanged_response = await client.get(
        f"/api/v1/tenders/{tender_id}", headers=headers
    )
    assert unchanged_response.json()["opening_date"] == "2026-09-10T09:00:00Z"
    assert unchanged_response.json()["closing_date"] == "2026-09-20T17:00:00Z"


@pytest.mark.asyncio
async def test_nullable_tender_fields_preserved(client: AsyncClient):
    headers = await auth_headers(client)
    payload = {
        "title": "Nullable Tender",
        "reference_number": "T-NULL",
        "description": None,
        "budget": None,
        "opening_date": None,
        "closing_date": None,
    }

    response = await client.post(
        "/api/v1/tenders", json=payload, headers=headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["description"] is None
    assert data["budget"] is None
    assert data["opening_date"] is None
    assert data["closing_date"] is None


@pytest.mark.asyncio
async def test_delete_tender(client: AsyncClient):
    headers = await auth_headers(client)
    create_response = await client.post(
        "/api/v1/tenders", json=tender_payload(), headers=headers
    )
    tender_id = create_response.json()["id"]

    delete_response = await client.delete(
        f"/api/v1/tenders/{tender_id}", headers=headers
    )
    assert delete_response.status_code == 204
    assert (
        await client.get(f"/api/v1/tenders/{tender_id}", headers=headers)
    ).status_code == 404


@pytest.mark.asyncio
async def test_authenticated_delete_tender(client: AsyncClient):
    headers = await auth_headers(client)
    create_response = await client.post(
        "/api/v1/tenders", json=tender_payload(), headers=headers
    )
    tender_id = create_response.json()["id"]

    response = await client.delete(
        f"/api/v1/tenders/{tender_id}", headers=headers
    )

    assert response.status_code == 204