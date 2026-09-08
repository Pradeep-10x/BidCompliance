import pytest
from httpx import AsyncClient


async def auth_headers(client: AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "tender-officer@example.com", "password": "Password123!"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "tender-officer@example.com", "password": "Password123!"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


class FakePage:
    def __init__(self, text: str):
        self.text = text

    def extract_text(self):
        return self.text


class FakePdfReader:
    def __init__(self, _stream):
        self.pages = [
            FakePage(
                "The bidder shall hold a valid Udyam registration as a Micro or Small enterprise.\n"
                "The bidder must provide an active GST registration certificate."
            )
        ]


@pytest.mark.asyncio
async def test_tender_upload_analysis_and_officer_confirmation(
    client, monkeypatch, tmp_path
):
    from app.core.config import settings
    from app.services import tender_analysis_service

    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    monkeypatch.setattr(tender_analysis_service, "PdfReader", FakePdfReader)
    headers = await auth_headers(client)
    tender_response = await client.post(
        "/api/v1/tenders",
        headers=headers,
        json={"title": "Tender Intelligence Demo", "reference_number": "TI-001"},
    )
    tender_id = tender_response.json()["id"]

    upload = await client.post(
        f"/api/v1/tenders/{tender_id}/documents",
        headers=headers,
        files={"file": ("tender.pdf", b"%PDF-1.7 synthetic", "application/pdf")},
    )
    assert upload.status_code == 201, upload.text
    assert upload.json()["version"] == 1

    analysis = await client.post(
        f"/api/v1/tenders/{tender_id}/analyze", headers=headers
    )
    assert analysis.status_code == 200, analysis.text
    assert analysis.json()["processing_status"] == "RULE_REVIEW"
    candidates = analysis.json()["candidates"]
    assert {candidate["category"] for candidate in candidates} == {
        "MSME_REGISTRATION",
        "GST_REGISTRATION",
    }
    assert {candidate["status"] for candidate in candidates} == {"CANDIDATE"}
    assert all(candidate["source_page"] == 1 for candidate in candidates)

    confirm = await client.post(
        f"/api/v1/tenders/{tender_id}/requirements/confirm",
        headers=headers,
        json={"requirement_ids": [candidate["id"] for candidate in candidates]},
    )
    assert confirm.status_code == 200, confirm.text
    assert {requirement["status"] for requirement in confirm.json()} == {"CONFIRMED"}

    audit = await client.get(f"/api/v1/tenders/{tender_id}/audit", headers=headers)
    assert audit.status_code == 200
    assert [event["event_type"] for event in audit.json()] == [
        "TENDER_DOCUMENT_UPLOADED",
        "TENDER_REQUIREMENTS_ANALYZED",
        "TENDER_REQUIREMENTS_CONFIRMED",
    ]
