import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.bid import Bid, BidStatus
from app.models.document import Document, DocumentProcessingStatus
from app.models.evidence import Evidence
from app.models.ml_processing_result import MLProcessingResult
from app.models.processing_job import PipelineStage, ProcessingJob, ProcessingJobStatus
from app.models.requirement import Requirement
from app.models.requirement_evaluation import RequirementEvaluation
from app.schemas.compliance import ComplianceSummaryStatus
from app.schemas.evaluation import EvaluationStatus
from app.services.evaluation_service import (
    evaluate_bid_requirements,
    get_bid_compliance_summary,
)
from tests.test_bids import create_bidder, create_tender
from tests.test_documents import document_context
from tests.test_requirements import create_requirement
from tests.test_tenders import auth_headers


async def setup_compliance_test_context(client: AsyncClient, db_session):
    headers = await auth_headers(client)
    tender, bidder, bid = await document_context(client, headers)

    doc = Document(
        id=uuid.uuid4(),
        bid_id=uuid.UUID(bid["id"]),
        original_filename="tender_doc.pdf",
        document_type="FINANCIAL_STATEMENT",
        content_hash=f"hash_{uuid.uuid4().hex[:8]}",
        storage_path="/tmp/test",
        processing_status=DocumentProcessingStatus.COMPLETED,
    )
    db_session.add(doc)
    await db_session.flush()

    job = ProcessingJob(
        id=uuid.uuid4(),
        document_id=doc.id,
        job_type="classification",
        pipeline_stage=PipelineStage.CLASSIFICATION,
        status=ProcessingJobStatus.COMPLETED,
        payload={},
    )
    db_session.add(job)
    await db_session.flush()

    ml_result = MLProcessingResult(
        id=uuid.uuid4(),
        job_id=job.id,
        document_id=doc.id,
        bid_id=uuid.UUID(bid["id"]),
        module="ml1",
        model_name="ocr",
        model_version="v1",
        status="success",
        result={},
        errors=[],
    )
    db_session.add(ml_result)
    await db_session.flush()

    def create_evidence(
        field_name: str,
        value: str | None,
        value_normalized: str | None = None,
        confidence: float | None = 0.95,
    ) -> Evidence:
        return Evidence(
            id=uuid.uuid4(),
            evidence_id=f"ev_{uuid.uuid4().hex[:12]}",
            document_id=doc.id,
            ml_result_id=ml_result.id,
            field_name=field_name,
            value=value,
            value_normalized=value_normalized,
            confidence=confidence,
            page_number=1,
            extraction_method="ocr",
            evidence_type="ML_EXTRACTION",
        )

    return headers, tender, bidder, bid, doc, create_evidence


# ==============================================================================
# UNIT & INTEGRATION TESTS FOR 4F COMPLIANCE AGGREGATION
# ==============================================================================


@pytest.mark.asyncio
async def test_compliance_summary_all_compliant(client: AsyncClient, db_session):
    headers, tender, bidder, bid, doc, create_evidence = await setup_compliance_test_context(client, db_session)
    tender_id = tender["id"]
    bid_id = bid["id"]

    # 2 requirements: both mandatory
    req1 = await create_requirement(
        client,
        headers,
        tender_id,
        {
            "title": "GST Registration",
            "is_mandatory": True,
            "weight": "2.00",
            "rule_config": {"target_field": "gstin", "operator": "EQUALS", "expected_value": "09ABCDE1234F1Z5"},
        },
    )
    req2 = await create_requirement(
        client,
        headers,
        tender_id,
        {
            "title": "Turnover Requirement",
            "is_mandatory": True,
            "weight": "3.00",
            "rule_config": {"target_field": "turnover", "operator": "GTE", "expected_value": 1000000},
        },
    )

    # Persist matching evidence
    ev1 = create_evidence("gstin", "09ABCDE1234F1Z5")
    ev2 = create_evidence("turnover", "2500000")
    db_session.add_all([ev1, ev2])
    await db_session.commit()

    # Trigger evaluation
    eval_resp = await client.post(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/evaluations",
        headers=headers,
    )
    assert eval_resp.status_code == 200

    # Request compliance summary
    resp = await client.get(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/compliance-summary",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["bid_id"] == bid_id
    assert data["tender_id"] == tender_id
    assert data["total_requirements"] == 2
    assert data["evaluated_requirements"] == 2
    assert data["unevaluated_requirements"] == 0
    assert data["compliant"] == 2
    assert data["non_compliant"] == 0
    assert data["missing_evidence"] == 0
    assert data["low_confidence"] == 0
    assert data["error"] == 0
    assert data["mandatory_total"] == 2
    assert data["mandatory_evaluated"] == 2
    assert data["mandatory_compliant"] == 2
    assert data["mandatory_non_compliant"] == 0
    assert data["summary_status"] == ComplianceSummaryStatus.READY_FOR_REVIEW
    assert data["compliance_ratio"] == 1.0
    assert data["weighted_compliance_ratio"] == 1.0
    assert len(data["requirements"]) == 2
    assert all(r["status"] == "COMPLIANT" for r in data["requirements"])


@pytest.mark.asyncio
async def test_compliance_summary_mixed_statuses(client: AsyncClient, db_session):
    headers, tender, bidder, bid, doc, create_evidence = await setup_compliance_test_context(client, db_session)
    tender_id = tender["id"]
    bid_id = bid["id"]

    # Req 1: mandatory compliant
    await create_requirement(
        client,
        headers,
        tender_id,
        {
            "title": "GST Req",
            "is_mandatory": True,
            "weight": "1.00",
            "rule_config": {"target_field": "gstin", "operator": "EQUALS", "expected_value": "09ABC"},
        },
    )
    # Req 2: optional non-compliant
    await create_requirement(
        client,
        headers,
        tender_id,
        {
            "title": "Turnover Req",
            "is_mandatory": False,
            "weight": "1.00",
            "rule_config": {"target_field": "turnover", "operator": "GTE", "expected_value": 5000000},
        },
    )

    ev1 = create_evidence("gstin", "09ABC")
    ev2 = create_evidence("turnover", "1000000")  # Less than 5,000,000
    db_session.add_all([ev1, ev2])
    await db_session.commit()

    # Evaluate
    await client.post(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/evaluations",
        headers=headers,
    )

    # Fetch summary
    resp = await client.get(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/compliance-summary",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_requirements"] == 2
    assert data["compliant"] == 1
    assert data["non_compliant"] == 1
    assert data["mandatory_total"] == 1
    assert data["mandatory_compliant"] == 1
    assert data["mandatory_non_compliant"] == 0
    assert data["summary_status"] == ComplianceSummaryStatus.REVIEW_REQUIRED
    assert data["compliance_ratio"] == 0.5
    assert data["weighted_compliance_ratio"] == 0.5


@pytest.mark.asyncio
async def test_compliance_summary_mandatory_failure(client: AsyncClient, db_session):
    headers, tender, bidder, bid, doc, create_evidence = await setup_compliance_test_context(client, db_session)
    tender_id = tender["id"]
    bid_id = bid["id"]

    # Mandatory requirement fails
    await create_requirement(
        client,
        headers,
        tender_id,
        {
            "title": "Mandatory GST",
            "is_mandatory": True,
            "weight": "1.00",
            "rule_config": {"target_field": "gstin", "operator": "EQUALS", "expected_value": "09ABC"},
        },
    )
    # Optional requirement passes
    await create_requirement(
        client,
        headers,
        tender_id,
        {
            "title": "Optional ISO",
            "is_mandatory": False,
            "weight": "1.00",
            "rule_config": {"target_field": "iso_code", "operator": "EQUALS", "expected_value": "ISO9001"},
        },
    )

    ev1 = create_evidence("gstin", "WRONG_GST")
    ev2 = create_evidence("iso_code", "ISO9001")
    db_session.add_all([ev1, ev2])
    await db_session.commit()

    await client.post(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/evaluations",
        headers=headers,
    )

    resp = await client.get(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/compliance-summary",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["mandatory_total"] == 1
    assert data["mandatory_evaluated"] == 1
    assert data["mandatory_compliant"] == 0
    assert data["mandatory_non_compliant"] == 1
    assert data["summary_status"] == ComplianceSummaryStatus.REVIEW_REQUIRED


@pytest.mark.asyncio
async def test_compliance_summary_missing_evidence(client: AsyncClient, db_session):
    headers, tender, bidder, bid, doc, create_evidence = await setup_compliance_test_context(client, db_session)
    tender_id = tender["id"]
    bid_id = bid["id"]

    await create_requirement(
        client,
        headers,
        tender_id,
        {
            "title": "PAN Card",
            "is_mandatory": True,
            "rule_config": {"target_field": "pan", "operator": "EXISTS"},
        },
    )
    # No evidence inserted

    await client.post(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/evaluations",
        headers=headers,
    )

    resp = await client.get(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/compliance-summary",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["missing_evidence"] == 1
    assert data["compliant"] == 0
    assert data["mandatory_non_compliant"] == 1
    assert data["summary_status"] == ComplianceSummaryStatus.REVIEW_REQUIRED


@pytest.mark.asyncio
async def test_compliance_summary_low_confidence(client: AsyncClient, db_session):
    headers, tender, bidder, bid, doc, create_evidence = await setup_compliance_test_context(client, db_session)
    tender_id = tender["id"]
    bid_id = bid["id"]

    await create_requirement(
        client,
        headers,
        tender_id,
        {
            "title": "High Confidence Field",
            "is_mandatory": True,
            "rule_config": {
                "target_field": "field_x",
                "operator": "EQUALS",
                "expected_value": "val",
                "min_confidence": 0.90,
            },
        },
    )

    ev = create_evidence("field_x", "val", confidence=0.75)
    db_session.add(ev)
    await db_session.commit()

    await client.post(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/evaluations",
        headers=headers,
    )

    resp = await client.get(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/compliance-summary",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["low_confidence"] == 1
    assert data["compliant"] == 0
    assert data["mandatory_non_compliant"] == 1
    assert data["summary_status"] == ComplianceSummaryStatus.REVIEW_REQUIRED


@pytest.mark.asyncio
async def test_compliance_summary_evaluation_error(client: AsyncClient, db_session):
    headers, tender, bidder, bid, doc, create_evidence = await setup_compliance_test_context(client, db_session)
    tender_id = tender["id"]
    bid_id = bid["id"]

    # Requirement with broken regex to trigger ERROR status
    await create_requirement(
        client,
        headers,
        tender_id,
        {
            "title": "Broken Rule",
            "is_mandatory": False,
            "rule_config": {
                "target_field": "test_field",
                "operator": "REGEX",
                "pattern": "[invalid-regex(",
            },
        },
    )

    ev = create_evidence("test_field", "sample")
    db_session.add(ev)
    await db_session.commit()

    await client.post(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/evaluations",
        headers=headers,
    )

    resp = await client.get(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/compliance-summary",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["error"] == 1
    assert data["summary_status"] == ComplianceSummaryStatus.ERROR


@pytest.mark.asyncio
async def test_compliance_summary_zero_requirements(client: AsyncClient, db_session):
    headers, tender, bidder, bid, doc, _ = await setup_compliance_test_context(client, db_session)
    tender_id = tender["id"]
    bid_id = bid["id"]

    # Tender has 0 requirements
    resp = await client.get(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/compliance-summary",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_requirements"] == 0
    assert data["evaluated_requirements"] == 0
    assert data["unevaluated_requirements"] == 0
    assert data["compliant"] == 0
    assert data["mandatory_total"] == 0
    assert data["compliance_ratio"] == 1.0
    assert data["weighted_compliance_ratio"] == 1.0
    assert data["summary_status"] == ComplianceSummaryStatus.READY_FOR_REVIEW
    assert data["requirements"] == []


@pytest.mark.asyncio
async def test_compliance_summary_incomplete_evaluations(client: AsyncClient, db_session):
    headers, tender, bidder, bid, doc, _ = await setup_compliance_test_context(client, db_session)
    tender_id = tender["id"]
    bid_id = bid["id"]

    # Create 2 requirements
    req1 = await create_requirement(
        client,
        headers,
        tender_id,
        {
            "title": "Evaluated Req",
            "is_mandatory": True,
            "rule_config": {"target_field": "f1", "operator": "EXISTS"},
        },
    )
    req2 = await create_requirement(
        client,
        headers,
        tender_id,
        {
            "title": "Unevaluated Req",
            "is_mandatory": True,
            "rule_config": {"target_field": "f2", "operator": "EXISTS"},
        },
    )

    # Insert an evaluation only for req1 directly to simulate partial evaluation
    eval_rec = RequirementEvaluation(
        id=uuid.uuid4(),
        tender_id=uuid.UUID(tender_id),
        bid_id=uuid.UUID(bid_id),
        requirement_id=uuid.UUID(req1["id"]),
        status=EvaluationStatus.COMPLIANT,
        is_mandatory=True,
        reason="Manual mock evaluation",
        details={},
    )
    db_session.add(eval_rec)
    await db_session.commit()

    # Query summary without running full evaluation
    resp = await client.get(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/compliance-summary",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_requirements"] == 2
    assert data["evaluated_requirements"] == 1
    assert data["unevaluated_requirements"] == 1
    assert data["summary_status"] == ComplianceSummaryStatus.INCOMPLETE

    # Verify req2 is marked as UNEVALUATED and NOT silently converted to NON_COMPLIANT
    req2_item = next(r for r in data["requirements"] if r["requirement_id"] == req2["id"])
    assert req2_item["status"] == "UNEVALUATED"
    assert req2_item["evaluation_id"] is None
    assert "not been evaluated yet" in req2_item["reason"]


@pytest.mark.asyncio
async def test_compliance_summary_repeated_call_determinism(client: AsyncClient, db_session):
    headers, tender, bidder, bid, doc, create_evidence = await setup_compliance_test_context(client, db_session)
    tender_id = tender["id"]
    bid_id = bid["id"]

    await create_requirement(
        client,
        headers,
        tender_id,
        {
            "title": "Req 1",
            "is_mandatory": True,
            "rule_config": {"target_field": "f1", "operator": "EQUALS", "expected_value": "val"},
        },
    )
    ev = create_evidence("f1", "val")
    db_session.add(ev)
    await db_session.commit()

    await client.post(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/evaluations",
        headers=headers,
    )

    resp1 = await client.get(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/compliance-summary",
        headers=headers,
    )
    resp2 = await client.get(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/compliance-summary",
        headers=headers,
    )

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json() == resp2.json()


@pytest.mark.asyncio
async def test_compliance_summary_immutability(client: AsyncClient, db_session):
    headers, tender, bidder, bid, doc, create_evidence = await setup_compliance_test_context(client, db_session)
    tender_id = tender["id"]
    bid_id = bid["id"]

    await create_requirement(
        client,
        headers,
        tender_id,
        {
            "title": "Immutable Req",
            "is_mandatory": True,
            "rule_config": {"target_field": "f1", "operator": "EQUALS", "expected_value": "val"},
        },
    )
    ev = create_evidence("f1", "val")
    db_session.add(ev)
    await db_session.commit()

    await client.post(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/evaluations",
        headers=headers,
    )

    # Get initial bid state
    bid_obj_before = (
        await db_session.execute(select(Bid).where(Bid.id == uuid.UUID(bid_id)))
    ).scalar_one()
    initial_bid_status = bid_obj_before.status
    assert initial_bid_status == BidStatus.SUBMITTED

    # Call summary
    resp = await client.get(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/compliance-summary",
        headers=headers,
    )
    assert resp.status_code == 200

    # Verify Bid.status is untouched
    bid_obj_after = (
        await db_session.execute(select(Bid).where(Bid.id == uuid.UUID(bid_id)))
    ).scalar_one()
    assert bid_obj_after.status == initial_bid_status
    assert bid_obj_after.status not in ["QUALIFIED", "DISQUALIFIED"]

    # Verify Requirement and Evidence remain intact
    req_obj = (
        await db_session.execute(select(Requirement).where(Requirement.tender_id == uuid.UUID(tender_id)))
    ).scalar_one()
    assert req_obj.rule_config == {"target_field": "f1", "operator": "EQUALS", "expected_value": "val"}

    ev_obj = (
        await db_session.execute(select(Evidence).where(Evidence.id == ev.id))
    ).scalar_one()
    assert ev_obj.value == "val"


@pytest.mark.asyncio
async def test_compliance_summary_provenance(client: AsyncClient, db_session):
    headers, tender, bidder, bid, doc, create_evidence = await setup_compliance_test_context(client, db_session)
    tender_id = tender["id"]
    bid_id = bid["id"]

    req = await create_requirement(
        client,
        headers,
        tender_id,
        {
            "title": "Provenance Req",
            "is_mandatory": True,
            "weight": "2.50",
            "rule_config": {"target_field": "f_prov", "operator": "EQUALS", "expected_value": "prov_val"},
        },
    )
    ev = create_evidence("f_prov", "prov_val")
    db_session.add(ev)
    await db_session.commit()

    eval_post = await client.post(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/evaluations",
        headers=headers,
    )
    evaluation_id = eval_post.json()[0]["id"]

    resp = await client.get(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/compliance-summary",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    req_summary = data["requirements"][0]
    assert req_summary["requirement_id"] == req["id"]
    assert req_summary["title"] == "Provenance Req"
    assert req_summary["is_mandatory"] is True
    assert req_summary["weight"] == 2.5
    assert req_summary["evaluation_id"] == evaluation_id
    assert req_summary["evidence_id"] == str(ev.id)
    assert req_summary["status"] == "COMPLIANT"
    assert req_summary["target_field"] == "f_prov"
    assert req_summary["extracted_value"] == "prov_val"
    assert req_summary["details"]["matched_evidence_id"] == str(ev.id)


@pytest.mark.asyncio
async def test_compliance_summary_weighted_calculation(client: AsyncClient, db_session):
    headers, tender, bidder, bid, doc, create_evidence = await setup_compliance_test_context(client, db_session)
    tender_id = tender["id"]
    bid_id = bid["id"]

    # Req 1: weight 3.0, passes
    await create_requirement(
        client,
        headers,
        tender_id,
        {
            "title": "Major Req",
            "is_mandatory": False,
            "weight": "3.00",
            "rule_config": {"target_field": "w1", "operator": "EQUALS", "expected_value": "yes"},
        },
    )
    # Req 2: weight 1.0, fails
    await create_requirement(
        client,
        headers,
        tender_id,
        {
            "title": "Minor Req",
            "is_mandatory": False,
            "weight": "1.00",
            "rule_config": {"target_field": "w2", "operator": "EQUALS", "expected_value": "yes"},
        },
    )

    ev1 = create_evidence("w1", "yes")
    ev2 = create_evidence("w2", "no")
    db_session.add_all([ev1, ev2])
    await db_session.commit()

    await client.post(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/evaluations",
        headers=headers,
    )

    resp = await client.get(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/compliance-summary",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    # Unweighted: 1 / 2 = 0.5
    assert data["compliance_ratio"] == 0.5
    # Weighted: 3.0 / (3.0 + 1.0) = 0.75
    assert data["weighted_compliance_ratio"] == 0.75


@pytest.mark.asyncio
async def test_compliance_summary_zero_and_negative_weights(client: AsyncClient, db_session):
    headers, tender, bidder, bid, doc, create_evidence = await setup_compliance_test_context(client, db_session)
    tender_id = tender["id"]
    bid_id = bid["id"]

    # Weight 0.0
    await create_requirement(
        client,
        headers,
        tender_id,
        {
            "title": "Zero Weight Req",
            "is_mandatory": False,
            "weight": "0.00",
            "rule_config": {"target_field": "z1", "operator": "EQUALS", "expected_value": "ok"},
        },
    )

    ev = create_evidence("z1", "ok")
    db_session.add(ev)
    await db_session.commit()

    await client.post(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/evaluations",
        headers=headers,
    )

    resp = await client.get(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/compliance-summary",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    # Total weight clamped to 0.0 -> falls back to unweighted compliance_ratio
    assert data["compliance_ratio"] == 1.0
    assert data["weighted_compliance_ratio"] == 1.0


@pytest.mark.asyncio
async def test_compliance_summary_scoping_and_not_found(client: AsyncClient, db_session):
    headers, tender, bidder, bid, doc, _ = await setup_compliance_test_context(client, db_session)
    tender_id = tender["id"]
    bid_id = bid["id"]
    random_uuid = str(uuid.uuid4())

    # Non-existent tender
    resp = await client.get(
        f"/api/v1/tenders/{random_uuid}/bids/{bid_id}/compliance-summary",
        headers=headers,
    )
    assert resp.status_code == 404

    # Non-existent bid
    resp = await client.get(
        f"/api/v1/tenders/{tender_id}/bids/{random_uuid}/compliance-summary",
        headers=headers,
    )
    assert resp.status_code == 404

    # Another tender and bid to test cross-scoping
    other_tender = await create_tender(client, headers, reference_number="OTHER-TENDER-123")
    resp = await client.get(
        f"/api/v1/tenders/{other_tender['id']}/bids/{bid_id}/compliance-summary",
        headers=headers,
    )
    assert resp.status_code == 404



@pytest.mark.asyncio
async def test_compliance_summary_unauthenticated(client: AsyncClient, db_session):
    headers, tender, bidder, bid, doc, _ = await setup_compliance_test_context(client, db_session)
    tender_id = tender["id"]
    bid_id = bid["id"]

    resp = await client.get(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/compliance-summary",
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_compliance_summary_no_autonomous_qualification(client: AsyncClient, db_session):
    """Verify that even when 100% compliant, the system NEVER qualifies the bid autonomously."""
    headers, tender, bidder, bid, doc, create_evidence = await setup_compliance_test_context(client, db_session)
    tender_id = tender["id"]
    bid_id = bid["id"]

    await create_requirement(
        client,
        headers,
        tender_id,
        {
            "title": "Req 100%",
            "is_mandatory": True,
            "rule_config": {"target_field": "field_q", "operator": "EQUALS", "expected_value": "pass"},
        },
    )
    ev = create_evidence("field_q", "pass")
    db_session.add(ev)
    await db_session.commit()

    await client.post(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/evaluations",
        headers=headers,
    )

    resp = await client.get(
        f"/api/v1/tenders/{tender_id}/bids/{bid_id}/compliance-summary",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["summary_status"] == ComplianceSummaryStatus.READY_FOR_REVIEW
    assert "QUALIFIED" not in data["summary_status"]
    assert "DISQUALIFIED" not in data["summary_status"]

    # Check database directly
    bid_record = (
        await db_session.execute(select(Bid).where(Bid.id == uuid.UUID(bid_id)))
    ).scalar_one()
    assert bid_record.status == BidStatus.SUBMITTED


@pytest.mark.asyncio
async def test_compliance_summary_direct_service_layer(client: AsyncClient, db_session):
    """Directly test the service function get_bid_compliance_summary."""
    headers, tender, bidder, bid, doc, create_evidence = await setup_compliance_test_context(client, db_session)
    tender_id = uuid.UUID(tender["id"])
    bid_id = uuid.UUID(bid["id"])

    # Directly call service function
    summary = await get_bid_compliance_summary(db_session, tender_id, bid_id)
    assert summary.bid_id == bid_id
    assert summary.tender_id == tender_id
    assert summary.total_requirements == 0
    assert summary.summary_status == ComplianceSummaryStatus.READY_FOR_REVIEW
