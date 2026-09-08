import pytest
from app.models.compliance import VerificationResult
from app.services.assessment_service import evaluate_rule
from httpx import AsyncClient


async def auth_headers(client: AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "demo-officer@example.com",
            "password": "Password123!",
            "full_name": "Demo Officer",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "demo-officer@example.com", "password": "Password123!"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


class FakeMLResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "document_classification": {
                "document_type": "udyam_registration_certificate",
                "confidence": 0.99,
            },
            "fields": [
                {
                    "field": "udyam_registration_number",
                    "value": "UDYAM-TN-01-1234567",
                    "value_normalized": "UDYAM-TN-01-1234567",
                    "confidence": 0.98,
                    "page": 1,
                    "bounding_box": {"x": 10, "y": 20, "width": 100, "height": 20},
                    "extraction_method": "regex",
                    "evidence_id": "ev-udyam-number",
                },
                {
                    "field": "enterprise_type",
                    "value": "Micro",
                    "value_normalized": "Micro",
                    "confidence": 0.92,
                    "page": 1,
                    "bounding_box": None,
                    "extraction_method": "regex",
                    "evidence_id": "ev-enterprise-type",
                },
            ],
        }


class FakeMLClient:
    last_headers: dict[str, str] = {}

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        self.__class__.last_headers = kwargs.get("headers", {})
        return FakeMLResponse()


@pytest.mark.asyncio
async def test_upload_process_verify_assess_decide_and_audit(
    client: AsyncClient, monkeypatch, tmp_path
):
    from app.core.config import settings
    from app.services import processing_service

    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    monkeypatch.setattr(settings, "ML_SHARED_SECRET", "test-ml-shared-secret")
    monkeypatch.setattr(processing_service.httpx, "AsyncClient", FakeMLClient)
    headers = await auth_headers(client)

    tender = (
        await client.post(
            "/api/v1/tenders",
            headers=headers,
            json={"title": "Demo Tender", "reference_number": "DEMO-001"},
        )
    ).json()
    bidder = (
        await client.post(
            "/api/v1/bidders",
            headers=headers,
            json={"legal_name": "ABC Industrial Systems Pvt Ltd"},
        )
    ).json()
    bid = (
        await client.post(
            f"/api/v1/tenders/{tender['id']}/bids",
            headers=headers,
            json={"bidder_id": bidder["id"]},
        )
    ).json()

    for payload in (
        {
            "title": "Verified Udyam registration",
            "is_mandatory": True,
            "weight": "2.00",
            "rule_config": {
                "kind": "verification_status",
                "source": "UDYAM",
                "allowed_statuses": ["VERIFIED"],
                "on_unavailable": "REVIEW",
            },
        },
        {
            "title": "Micro or Small enterprise",
            "is_mandatory": True,
            "weight": "1.00",
            "rule_config": {
                "kind": "field_equals",
                "field": "enterprise_type",
                "allowed_values": ["Micro", "Small"],
            },
        },
    ):
        response = await client.post(
            f"/api/v1/tenders/{tender['id']}/requirements",
            headers=headers,
            json=payload,
        )
        assert response.status_code == 201, response.text

    upload = await client.post(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/documents/upload",
        headers=headers,
        files={"file": ("udyam.png", b"\x89PNG\r\n\x1a\nsynthetic-demo", "image/png")},
    )
    assert upload.status_code == 201, upload.text
    document = upload.json()
    assert document["processing_status"] == "UPLOADED"

    processed = await client.post(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/documents/{document['id']}/process",
        headers=headers,
    )
    assert processed.status_code == 200, processed.text
    assert processed.json()["processing_status"] == "READY"
    assert len(processed.json()["facts"]) == 2
    assert FakeMLClient.last_headers == {
        "X-ML-Service-Key": "test-ml-shared-secret"
    }

    downloaded = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/documents/{document['id']}/download",
        headers=headers,
    )
    assert downloaded.status_code == 200
    assert downloaded.content == b"\x89PNG\r\n\x1a\nsynthetic-demo"

    verification = await client.post(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/verifications/run",
        headers=headers,
        json={"source": "UDYAM", "scenario": "MATCH"},
    )
    assert verification.status_code == 201, verification.text
    assert verification.json()["mode"] == "MOCK"
    assert verification.json()["status"] == "VERIFIED"

    assessment = await client.post(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/assessments/run",
        headers=headers,
    )
    assert assessment.status_code == 201, assessment.text
    assessment_data = assessment.json()
    assert assessment_data["mandatory_gate_status"] == "PASS"
    assert assessment_data["compliance_score"] == "100.00"
    assert assessment_data["risk_level"] == "LOW"
    assert {item["status"] for item in assessment_data["requirement_results"]} == {
        "PASS"
    }

    without_reason = await client.post(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/assessments/{assessment_data['id']}/decisions",
        headers=headers,
        json={"action": "OVERRIDE"},
    )
    assert without_reason.status_code == 422

    decision = await client.post(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/assessments/{assessment_data['id']}/decisions",
        headers=headers,
        json={"action": "OVERRIDE", "reason": "Officer-reviewed supporting evidence"},
    )
    assert decision.status_code == 201, decision.text

    audit = await client.get(
        f"/api/v1/tenders/{tender['id']}/audit",
        headers=headers,
        params={"bid_id": bid["id"]},
    )
    assert audit.status_code == 200, audit.text
    events = audit.json()
    assert [event["event_type"] for event in events] == [
        "DOCUMENT_UPLOADED",
        "DOCUMENT_PROCESSED",
        "SOURCE_VERIFICATION_COMPLETED",
        "ASSESSMENT_COMPLETED",
        "OFFICER_DECISION_RECORDED",
    ]
    assert events[0]["previous_event_hash"] is None
    assert events[1]["previous_event_hash"] == events[0]["payload_hash"]


def test_unavailable_source_degrades_to_review():
    verification = VerificationResult(
        bid_id="00000000-0000-0000-0000-000000000001",
        source="GST",
        mode="MOCK",
        request_id="request-1",
        status="UNAVAILABLE",
        fields={},
        matched_fields=[],
        mismatches=[],
        warnings=[],
        evidence_refs=[],
        adapter_version="mock-v1",
        confidence=0,
    )
    result = evaluate_rule(
        {"kind": "verification_status", "source": "GST", "on_unavailable": "REVIEW"},
        facts={},
        document_types=set(),
        verifications={"GST": verification},
    )
    assert result.status == "REVIEW"
    assert "unavailable" in result.reason.lower()
