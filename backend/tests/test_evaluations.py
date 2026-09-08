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
from app.schemas.evaluation import EvaluationStatus
from app.services.evaluation_service import (
    evaluate_bid_requirements,
    evaluate_single_requirement,
)
from tests.test_bids import create_bidder, create_tender
from tests.test_documents import document_context
from tests.test_requirements import create_requirement
from tests.test_tenders import auth_headers


def make_test_evidence(
    document_id: uuid.UUID,
    field_name: str,
    value: str | None,
    value_normalized: str | None = None,
    confidence: float | None = 0.95,
    document: Document | None = None,
) -> Evidence:
    return Evidence(
        id=uuid.uuid4(),
        evidence_id=f"ev_{uuid.uuid4().hex[:12]}",
        document_id=document_id,
        ml_result_id=uuid.uuid4(),
        field_name=field_name,
        value=value,
        value_normalized=value_normalized,
        confidence=confidence,
        page_number=1,
        extraction_method="ocr",
        evidence_type="ML_EXTRACTION",
        document=document,
    )


def test_matching_evidence_returns_compliant():
    req = Requirement(
        id=uuid.uuid4(),
        tender_id=uuid.uuid4(),
        title="GST Registration",
        rule_config={"target_field": "gstin", "operator": "EQUALS", "expected_value": "09ABCDE1234F1Z5"},
    )
    ev = make_test_evidence(uuid.uuid4(), "gstin", "09ABCDE1234F1Z5")
    result = evaluate_single_requirement(req, [ev])

    assert result.status == EvaluationStatus.COMPLIANT
    assert result.evidence_id == ev.id
    assert result.extracted_value == "09ABCDE1234F1Z5"
    assert "satisfies requirement" in result.reason
    assert result.details["matched_evidence_id"] == str(ev.id)


def test_non_matching_evidence_returns_non_compliant():
    req = Requirement(
        id=uuid.uuid4(),
        tender_id=uuid.uuid4(),
        title="GST Registration",
        rule_config={"target_field": "gstin", "operator": "EQUALS", "expected_value": "09ABCDE1234F1Z5"},
    )
    ev = make_test_evidence(uuid.uuid4(), "gstin", "07XYZAB9876C1Z2")
    result = evaluate_single_requirement(req, [ev])

    assert result.status == EvaluationStatus.NON_COMPLIANT
    assert result.evidence_id is None
    assert "none satisfied operator" in result.reason
    assert str(ev.id) in result.details["candidate_evidence_ids"]


def test_missing_evidence_returns_missing_evidence():
    req = Requirement(
        id=uuid.uuid4(),
        tender_id=uuid.uuid4(),
        title="PAN Card Requirement",
        rule_config={"target_field": "pan", "operator": "EXISTS"},
    )
    ev = make_test_evidence(uuid.uuid4(), "gstin", "09ABCDE1234F1Z5")
    result = evaluate_single_requirement(req, [ev])

    assert result.status == EvaluationStatus.MISSING_EVIDENCE
    assert result.evidence_id is None
    assert "No evidence found" in result.reason


def test_low_confidence_semantics():
    req = Requirement(
        id=uuid.uuid4(),
        tender_id=uuid.uuid4(),
        title="High Confidence GST",
        rule_config={
            "target_field": "gstin",
            "operator": "EQUALS",
            "expected_value": "09ABCDE1234F1Z5",
            "min_confidence": 0.90,
        },
    )
    # Target-field evidence exists but all candidates fail min_confidence
    ev = make_test_evidence(uuid.uuid4(), "gstin", "09ABCDE1234F1Z5", confidence=0.75)
    result = evaluate_single_requirement(req, [ev])

    assert result.status == EvaluationStatus.LOW_CONFIDENCE
    assert result.evidence_id is None
    assert "below min_confidence" in result.reason


def test_multiple_candidates_with_one_matching():
    req = Requirement(
        id=uuid.uuid4(),
        tender_id=uuid.uuid4(),
        title="Enterprise Name Match",
        rule_config={
            "target_field": "enterprise_name",
            "operator": "EQUALS",
            "expected_value": "ABC ENGINEERING PVT LTD",
        },
    )
    doc_id = uuid.uuid4()
    ev1 = make_test_evidence(doc_id, "enterprise_name", "XYZ LABS", confidence=0.99)
    ev2 = make_test_evidence(doc_id, "enterprise_name", "ABC ENGINEERING PVT LTD", confidence=0.80)

    result = evaluate_single_requirement(req, [ev1, ev2])

    assert result.status == EvaluationStatus.COMPLIANT
    # Crucial: picks the candidate satisfying the rule, even if other candidate had higher confidence
    assert result.evidence_id == ev2.id
    assert result.extracted_value == "ABC ENGINEERING PVT LTD"
    assert len(result.details["candidate_evidence_ids"]) == 2


def test_multiple_candidates_conflicting_none_matching():
    req = Requirement(
        id=uuid.uuid4(),
        tender_id=uuid.uuid4(),
        title="Enterprise Name Match",
        rule_config={
            "target_field": "enterprise_name",
            "operator": "EQUALS",
            "expected_value": "EXPECTED CORP",
        },
    )
    doc_id = uuid.uuid4()
    ev1 = make_test_evidence(doc_id, "enterprise_name", "CANDIDATE ONE", confidence=0.90)
    ev2 = make_test_evidence(doc_id, "enterprise_name", "CANDIDATE TWO", confidence=0.80)

    result = evaluate_single_requirement(req, [ev1, ev2])

    assert result.status == EvaluationStatus.NON_COMPLIANT
    assert result.evidence_id is None
    assert result.details["evaluated_candidates_count"] == 2


@pytest.mark.parametrize(
    "operator,expected,actual,compliant",
    [
        ("EQUALS", "ABC", "ABC", True),
        ("EQ", "ABC", "abc", True),  # default case-insensitive
        ("NOT_EQUALS", "XYZ", "ABC", True),
        ("NEQ", "ABC", "ABC", False),
        ("IN", ["ABC", "DEF"], "ABC", True),
        ("IN", ["XYZ", "123"], "ABC", False),
        ("CONTAINS", "ENG", "ABC ENGINEERING", True),
        ("CONTAINS", "LABS", "ABC ENGINEERING", False),
        ("STARTS_WITH", "ABC", "ABC ENGINEERING", True),
        ("STARTS_WITH", "ENG", "ABC ENGINEERING", False),
        ("EXISTS", None, "ANY_VALUE", True),
    ],
)
def test_deterministic_operators(operator, expected, actual, compliant):
    req = Requirement(
        id=uuid.uuid4(),
        tender_id=uuid.uuid4(),
        title="Operator Test",
        rule_config={
            "target_field": "test_field",
            "operator": operator,
            "expected_value": expected,
        },
    )
    ev = make_test_evidence(uuid.uuid4(), "test_field", actual)
    res = evaluate_single_requirement(req, [ev])
    if compliant:
        assert res.status == EvaluationStatus.COMPLIANT
    else:
        assert res.status == EvaluationStatus.NON_COMPLIANT


@pytest.mark.parametrize(
    "operator,expected,actual,compliant",
    [
        ("GT", 1000000, "1500000", True),
        ("GT", 1000000, "500000", False),
        ("GTE", 1000000, "1000000.00", True),
        ("GTE", 1000000, "999999", False),
        ("LT", 500, "250", True),
        ("LT", 500, "500", False),
        ("LTE", 500, "500.0", True),
        ("LTE", 500, "501", False),
    ],
)
def test_numeric_operators(operator, expected, actual, compliant):
    req = Requirement(
        id=uuid.uuid4(),
        tender_id=uuid.uuid4(),
        title="Numeric Operator Test",
        rule_config={
            "target_field": "turnover",
            "operator": operator,
            "expected_value": expected,
        },
    )
    ev = make_test_evidence(uuid.uuid4(), "turnover", actual)
    res = evaluate_single_requirement(req, [ev])
    if compliant:
        assert res.status == EvaluationStatus.COMPLIANT
    else:
        assert res.status == EvaluationStatus.NON_COMPLIANT


def test_malformed_numeric_value_returns_error():
    req = Requirement(
        id=uuid.uuid4(),
        tender_id=uuid.uuid4(),
        title="Numeric Test",
        rule_config={"target_field": "turnover", "operator": "GT", "expected_value": 1000},
    )
    ev = make_test_evidence(uuid.uuid4(), "turnover", "Not-A-Number")
    res = evaluate_single_requirement(req, [ev])
    assert res.status == EvaluationStatus.ERROR
    assert "cannot be parsed as a number" in res.reason


def test_regex_matching_and_invalid_pattern():
    # 1. Valid regex match
    req = Requirement(
        id=uuid.uuid4(),
        tender_id=uuid.uuid4(),
        title="GSTIN Format",
        rule_config={
            "target_field": "gstin",
            "operator": "REGEX",
            "expected_value": r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$",
        },
    )
    ev_valid = make_test_evidence(uuid.uuid4(), "gstin", "09ABCDE1234F1Z5")
    assert evaluate_single_requirement(req, [ev_valid]).status == EvaluationStatus.COMPLIANT

    ev_invalid = make_test_evidence(uuid.uuid4(), "gstin", "INVALID-GST")
    assert evaluate_single_requirement(req, [ev_invalid]).status == EvaluationStatus.NON_COMPLIANT

    # 2. Malformed regex pattern returns ERROR without crashing
    req_bad = Requirement(
        id=uuid.uuid4(),
        tender_id=uuid.uuid4(),
        title="Bad Regex",
        rule_config={"target_field": "gstin", "operator": "REGEX", "expected_value": "[unclosed"},
    )
    res_bad = evaluate_single_requirement(req_bad, [ev_valid])
    assert res_bad.status == EvaluationStatus.ERROR
    assert "Invalid regular expression pattern" in res_bad.reason


def test_normalized_vs_raw_value_comparison():
    req_raw = Requirement(
        id=uuid.uuid4(),
        tender_id=uuid.uuid4(),
        title="Raw Match",
        rule_config={
            "target_field": "company_name",
            "operator": "EQUALS",
            "expected_value": "ABC PVT LTD",
            "use_normalized": False,
        },
    )
    req_norm = Requirement(
        id=uuid.uuid4(),
        tender_id=uuid.uuid4(),
        title="Normalized Match",
        rule_config={
            "target_field": "company_name",
            "operator": "EQUALS",
            "expected_value": "ABC PRIVATE LIMITED",
            "use_normalized": True,
        },
    )
    ev = make_test_evidence(
        uuid.uuid4(),
        "company_name",
        value="ABC PVT LTD",
        value_normalized="ABC PRIVATE LIMITED",
    )

    assert evaluate_single_requirement(req_raw, [ev]).status == EvaluationStatus.COMPLIANT
    assert evaluate_single_requirement(req_norm, [ev]).status == EvaluationStatus.COMPLIANT


def test_case_sensitivity_flag():
    req_sensitive = Requirement(
        id=uuid.uuid4(),
        tender_id=uuid.uuid4(),
        title="Case Sensitive",
        rule_config={
            "target_field": "code",
            "operator": "EQUALS",
            "expected_value": "UPPERCASE",
            "case_sensitive": True,
        },
    )
    req_insensitive = Requirement(
        id=uuid.uuid4(),
        tender_id=uuid.uuid4(),
        title="Case Insensitive",
        rule_config={
            "target_field": "code",
            "operator": "EQUALS",
            "expected_value": "UPPERCASE",
            "case_sensitive": False,
        },
    )
    ev = make_test_evidence(uuid.uuid4(), "code", "uppercase")

    assert evaluate_single_requirement(req_sensitive, [ev]).status == EvaluationStatus.NON_COMPLIANT
    assert evaluate_single_requirement(req_insensitive, [ev]).status == EvaluationStatus.COMPLIANT


def test_document_type_filtering():
    doc1 = Document(id=uuid.uuid4(), document_type="UDYAM_CERTIFICATE", original_filename="u.pdf", content_hash="h1", storage_path="/p1")
    doc2 = Document(id=uuid.uuid4(), document_type="GST_CERTIFICATE", original_filename="g.pdf", content_hash="h2", storage_path="/p2")

    ev1 = make_test_evidence(doc1.id, "enterprise_name", "ACME UDYAM", document=doc1)
    ev2 = make_test_evidence(doc2.id, "enterprise_name", "ACME GST", document=doc2)

    req = Requirement(
        id=uuid.uuid4(),
        tender_id=uuid.uuid4(),
        title="GST Certificate Name",
        rule_config={
            "target_field": "enterprise_name",
            "operator": "EQUALS",
            "expected_value": "ACME GST",
            "document_type": "GST_CERTIFICATE",
        },
    )

    res = evaluate_single_requirement(req, [ev1, ev2])
    assert res.status == EvaluationStatus.COMPLIANT
    assert res.evidence_id == ev2.id


def test_invalid_rule_config_and_unknown_operator():
    # Missing rule_config
    req1 = Requirement(id=uuid.uuid4(), tender_id=uuid.uuid4(), title="Empty", rule_config={})
    assert evaluate_single_requirement(req1, []).status == EvaluationStatus.ERROR

    # Missing target_field
    req2 = Requirement(id=uuid.uuid4(), tender_id=uuid.uuid4(), title="No Field", rule_config={"operator": "EXISTS"})
    assert evaluate_single_requirement(req2, []).status == EvaluationStatus.ERROR

    # Unknown operator
    req3 = Requirement(id=uuid.uuid4(), tender_id=uuid.uuid4(), title="Bad Op", rule_config={"target_field": "gstin", "operator": "UNKNOWN_OP"})
    ev = make_test_evidence(uuid.uuid4(), "gstin", "123")
    assert evaluate_single_requirement(req3, [ev]).status == EvaluationStatus.ERROR


def test_immutability_of_requirement_and_evidence():
    original_config = {"target_field": "gstin", "operator": "EQUALS", "expected_value": "09ABCDE1234F1Z5"}
    req = Requirement(
        id=uuid.uuid4(),
        tender_id=uuid.uuid4(),
        title="Immutable Req",
        rule_config=dict(original_config),
    )
    ev = make_test_evidence(uuid.uuid4(), "gstin", "09ABCDE1234F1Z5")

    evaluate_single_requirement(req, [ev])

    assert req.rule_config == original_config
    assert ev.value == "09ABCDE1234F1Z5"


# ==============================================================================
# INTEGRATION TESTS: DATABASE PERSISTENCE, SCOPING, RBAC, AND IDEMPOTENCY
# ==============================================================================


async def setup_bid_with_persisted_evidence(client: AsyncClient, db_session):
    headers = await auth_headers(client)
    tender, bidder, bid = await document_context(client, headers)

    # Create 2 requirements for the tender
    req1 = await create_requirement(
        client,
        headers,
        tender["id"],
        {
            "title": "GST Registration",
            "is_mandatory": True,
            "weight": "2.00",
            "rule_config": {
                "target_field": "gstin",
                "operator": "EQUALS",
                "expected_value": "09ABCDE1234F1Z5",
            },
        },
    )
    req2 = await create_requirement(
        client,
        headers,
        tender["id"],
        {
            "title": "Turnover Requirement",
            "is_mandatory": False,
            "weight": "1.00",
            "rule_config": {
                "target_field": "turnover",
                "operator": "GTE",
                "expected_value": 5000000,
            },
        },
    )

    # Insert a document and evidence directly
    doc = Document(
        id=uuid.uuid4(),
        bid_id=uuid.UUID(bid["id"]),
        original_filename="gst_cert.pdf",
        document_type="GST_CERTIFICATE",
        content_hash="mockhash123",
        storage_path="/tmp/mock",
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

    ml_res = MLProcessingResult(
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
    db_session.add(ml_res)
    await db_session.flush()

    ev1 = Evidence(
        id=uuid.uuid4(),
        evidence_id=f"ev_{doc.id.hex[:6]}_gstin",
        document_id=doc.id,
        ml_result_id=ml_res.id,
        field_name="gstin",
        value="09ABCDE1234F1Z5",
        confidence=0.98,
        page_number=1,
        extraction_method="ocr_anchor",
        evidence_type="ML_EXTRACTION",
    )
    ev2 = Evidence(
        id=uuid.uuid4(),
        evidence_id=f"ev_{doc.id.hex[:6]}_turnover",
        document_id=doc.id,
        ml_result_id=ml_res.id,
        field_name="turnover",
        value="3000000",  # Below 5,000,000 -> NON_COMPLIANT
        confidence=0.92,
        page_number=2,
        extraction_method="ocr",
        evidence_type="ML_EXTRACTION",
    )
    db_session.add_all([ev1, ev2])
    await db_session.commit()

    return headers, tender, bid, [req1, req2], [ev1, ev2]


@pytest.mark.asyncio
async def test_evaluate_bid_requirements_persists_results_without_bid_mutation(
    client: AsyncClient, db_session
):
    headers, tender, bid, reqs, evs = await setup_bid_with_persisted_evidence(client, db_session)

    # Trigger evaluation via API
    resp = await client.post(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/evaluations",
        headers=headers,
    )
    assert resp.status_code == 200
    evals = resp.json()
    assert len(evals) == 2

    evals_by_req = {e["requirement_id"]: e for e in evs_by_id(evals, reqs)}

    # Req 1: GSTIN matches -> COMPLIANT
    gst_eval = evals_by_req[reqs[0]["id"]]
    assert gst_eval["status"] == EvaluationStatus.COMPLIANT
    assert gst_eval["evidence_id"] == str(evs[0].id)
    assert gst_eval["extracted_value"] == "09ABCDE1234F1Z5"

    # Req 2: Turnover 3M < 5M -> NON_COMPLIANT
    to_eval = evals_by_req[reqs[1]["id"]]
    assert to_eval["status"] == EvaluationStatus.NON_COMPLIANT
    assert to_eval["evidence_id"] is None

    # Verify database persistence
    db_evals = (
        await db_session.execute(
            select(RequirementEvaluation).where(RequirementEvaluation.bid_id == bid["id"])
        )
    ).scalars().all()
    assert len(db_evals) == 2

    # Verify Bid.status is NOT mutated to QUALIFIED/DISQUALIFIED (Locked decision 7)
    db_bid = (
        await db_session.execute(select(Bid).where(Bid.id == bid["id"]))
    ).scalar_one()
    assert db_bid.status == BidStatus.SUBMITTED


@pytest.mark.asyncio
async def test_repeated_evaluation_is_idempotent(client: AsyncClient, db_session):
    headers, tender, bid, _, _ = await setup_bid_with_persisted_evidence(client, db_session)

    # First evaluation
    resp1 = await client.post(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/evaluations",
        headers=headers,
    )
    assert resp1.status_code == 200

    # Second evaluation
    resp2 = await client.post(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/evaluations",
        headers=headers,
    )
    assert resp2.status_code == 200

    # Results identical
    assert resp1.json() == resp2.json()

    # Exact same 2 rows in DB (no duplicates created)
    db_evals = (
        await db_session.execute(
            select(RequirementEvaluation).where(RequirementEvaluation.bid_id == bid["id"])
        )
    ).scalars().all()
    assert len(db_evals) == 2


@pytest.mark.asyncio
async def test_evaluation_read_endpoints_and_scoping(client: AsyncClient, db_session):
    headers, tender, bid, reqs, _ = await setup_bid_with_persisted_evidence(client, db_session)

    # Run evaluation
    await client.post(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/evaluations",
        headers=headers,
    )

    # 1. List evaluations
    list_resp = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/evaluations",
        headers=headers,
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 2

    # 2. Get single evaluation
    req1_id = reqs[0]["id"]
    get_resp = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/evaluations/{req1_id}",
        headers=headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["requirement_id"] == req1_id

    # 3. Scoping tests: wrong tender -> 404
    bad_id = str(uuid.uuid4())
    res_bad_tender = await client.get(
        f"/api/v1/tenders/{bad_id}/bids/{bid['id']}/evaluations",
        headers=headers,
    )
    assert res_bad_tender.status_code == 404

    # 4. Wrong bid -> 404
    res_bad_bid = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids/{bad_id}/evaluations",
        headers=headers,
    )
    assert res_bad_bid.status_code == 404

    # 5. Wrong requirement -> 404
    res_bad_req = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/evaluations/{bad_id}",
        headers=headers,
    )
    assert res_bad_req.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_evaluation_access_rejected(client: AsyncClient, db_session):
    _, tender, bid, reqs, _ = await setup_bid_with_persisted_evidence(client, db_session)

    # POST without auth -> 401
    res1 = await client.post(f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/evaluations")
    assert res1.status_code == 401

    # GET without auth -> 401
    res2 = await client.get(f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/evaluations")
    assert res2.status_code == 401

    # GET single without auth -> 401
    res3 = await client.get(
        f"/api/v1/tenders/{tender['id']}/bids/{bid['id']}/evaluations/{reqs[0]['id']}"
    )
    assert res3.status_code == 401


def evs_by_id(evals_json: list[dict], reqs: list[dict]) -> list[dict]:
    return evals_json
