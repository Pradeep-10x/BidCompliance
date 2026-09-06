from typing import Any

import pytest
from httpx import AsyncClient

from tests.test_tenders import auth_headers


async def create_tender(
    client: AsyncClient, headers: dict[str, str], reference_number: str = "REQ-TENDER"
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/tenders",
        json={
            "title": "Requirement Test Tender",
            "reference_number": reference_number,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


async def create_requirement(
    client: AsyncClient,
    headers: dict[str, str],
    tender_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = await client.post(
        f"/api/v1/tenders/{tender_id}/requirements",
        json=payload or {"title": "Valid requirement"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_unauthenticated_requirement_access_rejected(client: AsyncClient):
    response = await client.get(
        "/api/v1/tenders/00000000-0000-0000-0000-000000000000/requirements"
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_create_requirement(client: AsyncClient):
    headers = await auth_headers(client)
    tender = await create_tender(client, headers)

    requirement = await create_requirement(
        client,
        headers,
        tender["id"],
        {
            "title": "GST registration",
            "description": "Valid GST certificate required",
            "is_mandatory": True,
            "weight": "2.50",
            "rule_config": {"required_code": "GST-001", "regions": ["MH", "DL"]},
        },
    )

    assert requirement["tender_id"] == tender["id"]
    assert requirement["title"] == "GST registration"
    assert requirement["is_mandatory"] is True
    assert requirement["weight"] == "2.50"
    assert requirement["rule_config"] == {
        "required_code": "GST-001",
        "regions": ["MH", "DL"],
    }


@pytest.mark.asyncio
async def test_create_requirement_under_nonexistent_tender_returns_404(
    client: AsyncClient,
):
    headers = await auth_headers(client)
    response = await client.post(
        "/api/v1/tenders/00000000-0000-0000-0000-000000000000/requirements",
        json={"title": "Orphan requirement"},
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_requirements_and_pagination(client: AsyncClient):
    headers = await auth_headers(client)
    tender = await create_tender(client, headers)
    tender_id = tender["id"]
    await create_requirement(client, headers, tender_id, {"title": "Requirement A"})
    await create_requirement(client, headers, tender_id, {"title": "Requirement B"})

    response = await client.get(
        f"/api/v1/tenders/{tender_id}/requirements?skip=1&limit=1",
        headers=headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Requirement A"


@pytest.mark.asyncio
async def test_authenticated_get_requirement(client: AsyncClient):
    headers = await auth_headers(client)
    tender = await create_tender(client, headers)
    requirement = await create_requirement(client, headers, tender["id"])

    response = await client.get(
        f"/api/v1/tenders/{tender['id']}/requirements/{requirement['id']}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == requirement["id"]


@pytest.mark.asyncio
async def test_get_nonexistent_requirement_returns_404(client: AsyncClient):
    headers = await auth_headers(client)
    tender = await create_tender(client, headers)
    response = await client.get(
        f"/api/v1/tenders/{tender['id']}/requirements/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_wrong_tender_id_does_not_expose_requirement(client: AsyncClient):
    headers = await auth_headers(client)
    tender_a = await create_tender(client, headers, "REQ-TENDER-A")
    tender_b = await create_tender(client, headers, "REQ-TENDER-B")
    requirement = await create_requirement(client, headers, tender_a["id"])

    response = await client.get(
        f"/api/v1/tenders/{tender_b['id']}/requirements/{requirement['id']}",
        headers=headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_authenticated_patch_is_partial_and_preserves_omitted_fields(
    client: AsyncClient,
):
    headers = await auth_headers(client)
    tender = await create_tender(client, headers)
    requirement = await create_requirement(
        client,
        headers,
        tender["id"],
        {
            "title": "Original title",
            "description": "Original description",
            "is_mandatory": True,
            "weight": "3.25",
            "rule_config": {"kind": "exact"},
        },
    )

    response = await client.patch(
        f"/api/v1/tenders/{tender['id']}/requirements/{requirement['id']}",
        json={"title": "Updated title", "is_mandatory": False},
        headers=headers,
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == "Updated title"
    assert updated["is_mandatory"] is False
    assert updated["description"] == "Original description"
    assert updated["weight"] == "3.25"
    assert updated["rule_config"] == {"kind": "exact"}


@pytest.mark.asyncio
async def test_rule_config_default_and_round_trip(client: AsyncClient):
    headers = await auth_headers(client)
    tender = await create_tender(client, headers)
    default_requirement = await create_requirement(client, headers, tender["id"])
    assert default_requirement["rule_config"] == {}

    config = {"required_documents": ["PAN", "GST"], "threshold": {"amount": 100}}
    response = await client.patch(
        f"/api/v1/tenders/{tender['id']}/requirements/{default_requirement['id']}",
        json={"rule_config": config},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["rule_config"] == config


@pytest.mark.asyncio
async def test_optional_requirement_and_weight_round_trip(client: AsyncClient):
    headers = await auth_headers(client)
    tender = await create_tender(client, headers)
    requirement = await create_requirement(
        client,
        headers,
        tender["id"],
        {"title": "Optional requirement", "is_mandatory": False, "weight": "0.75"},
    )
    assert requirement["is_mandatory"] is False
    assert requirement["weight"] == "0.75"


@pytest.mark.asyncio
async def test_requirement_validation_rejects_extra_fields_and_invalid_weight(
    client: AsyncClient,
):
    headers = await auth_headers(client)
    tender = await create_tender(client, headers)
    path = f"/api/v1/tenders/{tender['id']}/requirements"

    extra_response = await client.post(
        path, json={"title": "Unexpected", "unknown": True}, headers=headers
    )
    invalid_weight_response = await client.post(
        path, json={"title": "Too precise", "weight": "1.001"}, headers=headers
    )

    assert extra_response.status_code == 422
    assert invalid_weight_response.status_code == 422


@pytest.mark.asyncio
async def test_authenticated_delete_requirement(client: AsyncClient):
    headers = await auth_headers(client)
    tender = await create_tender(client, headers)
    requirement = await create_requirement(client, headers, tender["id"])
    path = f"/api/v1/tenders/{tender['id']}/requirements/{requirement['id']}"

    response = await client.delete(path, headers=headers)

    assert response.status_code == 204
    assert (await client.get(path, headers=headers)).status_code == 404
