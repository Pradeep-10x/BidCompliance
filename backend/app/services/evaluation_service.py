import re
import uuid
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.bid import Bid
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.requirement import Requirement
from app.models.requirement_evaluation import RequirementEvaluation
from app.models.tender import Tender
from app.schemas.compliance import (
    BidComplianceSummaryResponse,
    ComplianceSummaryStatus,
    RequirementSummaryItem,
)
from app.schemas.evaluation import EvaluationResult, EvaluationStatus



SUPPORTED_OPERATORS = {
    "EXISTS",
    "EQUALS",
    "EQ",
    "NOT_EQUALS",
    "NEQ",
    "IN",
    "CONTAINS",
    "STARTS_WITH",
    "REGEX",
    "MATCHES",
    "GT",
    "GTE",
    "LT",
    "LTE",
}


def evaluate_single_requirement(
    requirement: Requirement, evidence_list: list[Evidence]
) -> EvaluationResult:
    """Pure, deterministic requirement evaluation against persisted Evidence.
    
    Returns a plain EvaluationResult object without mutating Requirement or Evidence.
    """
    rule_config = requirement.rule_config
    if not isinstance(rule_config, dict) or not rule_config:
        return EvaluationResult(
            status=EvaluationStatus.ERROR,
            requirement_id=requirement.id,
            target_field=None,
            extracted_value=None,
            confidence=None,
            evidence_id=None,
            reason="Requirement rule_config is missing or empty",
            details={"rule_config": rule_config},
        )

    target_field = rule_config.get("target_field")
    if not target_field or not isinstance(target_field, str) or not target_field.strip():
        return EvaluationResult(
            status=EvaluationStatus.ERROR,
            requirement_id=requirement.id,
            target_field=None,
            extracted_value=None,
            confidence=None,
            evidence_id=None,
            reason="Requirement rule_config missing valid 'target_field'",
            details={"rule_config": rule_config},
        )
    target_field = target_field.strip()

    raw_operator = rule_config.get("operator")
    if not raw_operator or not isinstance(raw_operator, str) or not raw_operator.strip():
        return EvaluationResult(
            status=EvaluationStatus.ERROR,
            requirement_id=requirement.id,
            target_field=target_field,
            extracted_value=None,
            confidence=None,
            evidence_id=None,
            reason="Requirement rule_config missing 'operator'",
            details={"rule_config": rule_config},
        )
    operator = raw_operator.strip().upper()

    if operator not in SUPPORTED_OPERATORS:
        return EvaluationResult(
            status=EvaluationStatus.ERROR,
            requirement_id=requirement.id,
            target_field=target_field,
            extracted_value=None,
            confidence=None,
            evidence_id=None,
            reason=f"Unsupported operator '{raw_operator}'",
            details={"rule_config": rule_config},
        )

    # Step 1: Filter Evidence by target_field
    candidates = [ev for ev in evidence_list if ev.field_name == target_field]

    # Step 2: Filter by document_type if specified in rule_config
    doc_type_filter = rule_config.get("document_type")
    if doc_type_filter and isinstance(doc_type_filter, str) and doc_type_filter.strip():
        req_doc_type = doc_type_filter.strip().upper()
        candidates = [
            ev for ev in candidates
            if ev.document and ev.document.document_type.upper() == req_doc_type
        ]

    # Step 8: If no candidates exist at all -> MISSING_EVIDENCE
    if not candidates:
        return EvaluationResult(
            status=EvaluationStatus.MISSING_EVIDENCE,
            requirement_id=requirement.id,
            target_field=target_field,
            extracted_value=None,
            confidence=None,
            evidence_id=None,
            reason=f"No evidence found for target field '{target_field}'",
            details={
                "operator": operator,
                "document_type": doc_type_filter,
                "candidate_evidence_ids": [],
            },
        )

    candidate_ids = [str(ev.id) for ev in candidates]

    # Step 3: Check min_confidence threshold
    min_confidence = rule_config.get("min_confidence")
    eligible_candidates: list[Evidence] = []
    if min_confidence is not None:
        try:
            min_conf_val = float(min_confidence)
        except (ValueError, TypeError):
            return EvaluationResult(
                status=EvaluationStatus.ERROR,
                requirement_id=requirement.id,
                target_field=target_field,
                extracted_value=None,
                confidence=None,
                evidence_id=None,
                reason=f"Invalid min_confidence '{min_confidence}', must be a float",
                details={"rule_config": rule_config},
            )
        eligible_candidates = [
            ev for ev in candidates
            if ev.confidence is not None and ev.confidence >= min_conf_val
        ]
        # Step 7: Matching-field candidates exist, but all are below min_confidence -> LOW_CONFIDENCE
        if not eligible_candidates:
            return EvaluationResult(
                status=EvaluationStatus.LOW_CONFIDENCE,
                requirement_id=requirement.id,
                target_field=target_field,
                extracted_value=candidates[0].value,
                confidence=candidates[0].confidence,
                evidence_id=None,
                reason=(
                    f"Evidence found for '{target_field}', but all candidates "
                    f"had confidence below min_confidence ({min_conf_val})"
                ),
                details={
                    "operator": operator,
                    "min_confidence": min_conf_val,
                    "candidate_evidence_ids": candidate_ids,
                    "candidates_confidence": [ev.confidence for ev in candidates],
                },
            )
    else:
        min_conf_val = None
        eligible_candidates = candidates

    # Step 4: Evaluate eligible candidates against the operator
    use_normalized = bool(rule_config.get("use_normalized", False))
    case_sensitive = bool(rule_config.get("case_sensitive", False))
    expected_value = rule_config.get("expected_value")
    expected_values = rule_config.get("expected_values")

    base_details = {
        "operator": operator,
        "expected_value": expected_value,
        "expected_values": expected_values,
        "use_normalized": use_normalized,
        "case_sensitive": case_sensitive,
        "min_confidence": min_conf_val,
        "document_type": doc_type_filter,
        "candidate_evidence_ids": candidate_ids,
    }

    # Pre-validation for specific operators
    if operator in {"EQUALS", "EQ", "NOT_EQUALS", "NEQ"} and expected_value is None:
        return EvaluationResult(
            status=EvaluationStatus.ERROR,
            requirement_id=requirement.id,
            target_field=target_field,
            extracted_value=None,
            confidence=None,
            evidence_id=None,
            reason=f"Operator '{operator}' requires 'expected_value'",
            details=base_details,
        )

    if operator == "IN":
        in_list = expected_values if expected_values is not None else expected_value
        if not isinstance(in_list, (list, tuple, set)):
            return EvaluationResult(
                status=EvaluationStatus.ERROR,
                requirement_id=requirement.id,
                target_field=target_field,
                extracted_value=None,
                confidence=None,
                evidence_id=None,
                reason="Operator 'IN' requires a list in 'expected_values'",
                details=base_details,
            )

    if operator in {"CONTAINS", "STARTS_WITH"} and expected_value is None:
        return EvaluationResult(
            status=EvaluationStatus.ERROR,
            requirement_id=requirement.id,
            target_field=target_field,
            extracted_value=None,
            confidence=None,
            evidence_id=None,
            reason=f"Operator '{operator}' requires 'expected_value'",
            details=base_details,
        )

    compiled_regex = None
    if operator in {"REGEX", "MATCHES"}:
        pattern = expected_value if expected_value is not None else rule_config.get("pattern")
        if pattern is None or not str(pattern).strip():
            return EvaluationResult(
                status=EvaluationStatus.ERROR,
                requirement_id=requirement.id,
                target_field=target_field,
                extracted_value=None,
                confidence=None,
                evidence_id=None,
                reason="Operator 'REGEX' requires a regex string in 'expected_value' or 'pattern'",
                details=base_details,
            )
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            compiled_regex = re.compile(str(pattern), flags)
        except re.error as exc:
            return EvaluationResult(
                status=EvaluationStatus.ERROR,
                requirement_id=requirement.id,
                target_field=target_field,
                extracted_value=None,
                confidence=None,
                evidence_id=None,
                reason=f"Invalid regular expression pattern: {exc}",
                details=base_details,
            )

    numeric_exp: Optional[float] = None
    if operator in {"GT", "GTE", "LT", "LTE"}:
        if expected_value is None:
            return EvaluationResult(
                status=EvaluationStatus.ERROR,
                requirement_id=requirement.id,
                target_field=target_field,
                extracted_value=None,
                confidence=None,
                evidence_id=None,
                reason=f"Operator '{operator}' requires numeric 'expected_value'",
                details=base_details,
            )
        try:
            numeric_exp = float(str(expected_value).strip().replace(",", ""))
        except (ValueError, TypeError):
            return EvaluationResult(
                status=EvaluationStatus.ERROR,
                requirement_id=requirement.id,
                target_field=target_field,
                extracted_value=None,
                confidence=None,
                evidence_id=None,
                reason=f"Operator '{operator}' requires a valid numeric expected_value, got '{expected_value}'",
                details=base_details,
            )

    # Step 5: Check each eligible candidate
    for ev in eligible_candidates:
        act_val = ev.value_normalized if use_normalized else ev.value
        matched = False

        if operator == "EXISTS":
            matched = True

        elif operator in {"EQUALS", "EQ"}:
            if act_val is not None:
                if case_sensitive:
                    matched = act_val == str(expected_value)
                else:
                    matched = act_val.lower() == str(expected_value).lower()

        elif operator in {"NOT_EQUALS", "NEQ"}:
            if act_val is None:
                matched = True
            else:
                if case_sensitive:
                    matched = act_val != str(expected_value)
                else:
                    matched = act_val.lower() != str(expected_value).lower()

        elif operator == "IN":
            if act_val is not None:
                in_list = expected_values if expected_values is not None else expected_value
                if case_sensitive:
                    matched = act_val in [str(x) for x in in_list]
                else:
                    matched = act_val.lower() in [str(x).lower() for x in in_list]

        elif operator == "CONTAINS":
            if act_val is not None:
                if case_sensitive:
                    matched = str(expected_value) in act_val
                else:
                    matched = str(expected_value).lower() in act_val.lower()

        elif operator == "STARTS_WITH":
            if act_val is not None:
                if case_sensitive:
                    matched = act_val.startswith(str(expected_value))
                else:
                    matched = act_val.lower().startswith(str(expected_value).lower())

        elif operator in {"REGEX", "MATCHES"}:
            if act_val is not None and compiled_regex is not None:
                matched = bool(compiled_regex.search(act_val))

        elif operator in {"GT", "GTE", "LT", "LTE"}:
            if act_val is not None:
                clean_num_str = act_val.strip().replace(",", "")
                try:
                    act_num = float(clean_num_str)
                    if operator == "GT":
                        matched = act_num > numeric_exp
                    elif operator == "GTE":
                        matched = act_num >= numeric_exp
                    elif operator == "LT":
                        matched = act_num < numeric_exp
                    elif operator == "LTE":
                        matched = act_num <= numeric_exp
                except (ValueError, TypeError):
                    return EvaluationResult(
                        status=EvaluationStatus.ERROR,
                        requirement_id=requirement.id,
                        target_field=target_field,
                        extracted_value=act_val,
                        confidence=ev.confidence,
                        evidence_id=ev.id,
                        reason=f"Extracted value '{act_val}' cannot be parsed as a number for operator '{operator}'",
                        details=base_details,
                    )

        if matched:
            result_details = dict(base_details)
            result_details.update({
                "matched_evidence_id": str(ev.id),
                "matched_evidence_auth_id": ev.evidence_id,
                "matched_document_id": str(ev.document_id),
                "matched_page_number": ev.page_number,
                "comparison_value": act_val,
            })
            return EvaluationResult(
                status=EvaluationStatus.COMPLIANT,
                requirement_id=requirement.id,
                target_field=target_field,
                extracted_value=act_val,
                confidence=ev.confidence,
                evidence_id=ev.id,
                reason=f"Evidence satisfies requirement '{requirement.title}' via operator '{operator}'",
                details=result_details,
            )

    # Step 6: If eligible candidates exist but none satisfy the rule -> NON_COMPLIANT
    best_candidate = eligible_candidates[0]
    best_val = best_candidate.value_normalized if use_normalized else best_candidate.value
    result_details = dict(base_details)
    result_details.update({
        "comparison_value": best_val,
        "evaluated_candidates_count": len(eligible_candidates),
    })
    return EvaluationResult(
        status=EvaluationStatus.NON_COMPLIANT,
        requirement_id=requirement.id,
        target_field=target_field,
        extracted_value=best_val,
        confidence=best_candidate.confidence,
        evidence_id=None,
        reason=(
            f"Evaluated {len(eligible_candidates)} candidate(s) for '{target_field}', "
            f"none satisfied operator '{operator}'"
        ),
        details=result_details,
    )


async def evaluate_bid_requirements(
    db: AsyncSession, tender_id: UUID, bid_id: UUID
) -> list[RequirementEvaluation]:
    """Deterministically evaluate all requirements of a tender against a bid's persisted evidence.
    
    Upserts RequirementEvaluation records idempotently and commits transactionally.
    Does NOT mutate Bid.status or Requirement.
    """
    # 1. Verify Tender existence
    tender_stmt = select(Tender).where(Tender.id == tender_id)
    tender_res = await db.execute(tender_stmt)
    tender = tender_res.scalar_one_or_none()
    if tender is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tender not found"
        )

    # 2. Verify Bid existence and Tender ownership
    bid_stmt = select(Bid).where(Bid.id == bid_id, Bid.tender_id == tender_id)
    bid_res = await db.execute(bid_stmt)
    bid = bid_res.scalar_one_or_none()
    if bid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bid not found"
        )

    # 3. Load all Requirements for the Tender
    req_stmt = (
        select(Requirement)
        .where(Requirement.tender_id == tender_id)
        .order_by(Requirement.created_at.asc())
    )
    req_res = await db.execute(req_stmt)
    requirements = list(req_res.scalars().all())

    # 4. Load all persisted Evidence across Documents for this Bid
    evidence_stmt = (
        select(Evidence)
        .join(Document, Document.id == Evidence.document_id)
        .options(joinedload(Evidence.document))
        .where(Document.bid_id == bid_id)
        .order_by(Evidence.created_at.asc())
    )
    evidence_res = await db.execute(evidence_stmt)
    bid_evidence = list(evidence_res.scalars().all())

    # 5. Load existing RequirementEvaluation records for idempotency
    existing_eval_stmt = (
        select(RequirementEvaluation)
        .where(RequirementEvaluation.bid_id == bid_id)
    )
    existing_eval_res = await db.execute(existing_eval_stmt)
    existing_evals = {
        ev.requirement_id: ev for ev in existing_eval_res.scalars().all()
    }

    evaluations_to_return: list[RequirementEvaluation] = []

    # 6. Evaluate each requirement deterministically
    for req in requirements:
        eval_result = evaluate_single_requirement(req, bid_evidence)

        record = existing_evals.get(req.id)
        if record is not None:
            # Update existing record
            record.evidence_id = eval_result.evidence_id
            record.status = eval_result.status
            record.is_mandatory = req.is_mandatory
            record.target_field = eval_result.target_field
            record.extracted_value = eval_result.extracted_value
            record.confidence = eval_result.confidence
            record.reason = eval_result.reason
            record.details = eval_result.details
        else:
            # Create new evaluation record
            record = RequirementEvaluation(
                id=uuid.uuid4(),
                tender_id=tender_id,
                bid_id=bid_id,
                requirement_id=req.id,
                evidence_id=eval_result.evidence_id,
                status=eval_result.status,
                is_mandatory=req.is_mandatory,
                target_field=eval_result.target_field,
                extracted_value=eval_result.extracted_value,
                confidence=eval_result.confidence,
                reason=eval_result.reason,
                details=eval_result.details,
            )
            db.add(record)

        evaluations_to_return.append(record)

    await db.commit()
    for item in evaluations_to_return:
        await db.refresh(item)

    return evaluations_to_return


async def list_bid_evaluations(
    db: AsyncSession, tender_id: UUID, bid_id: UUID
) -> list[RequirementEvaluation]:
    """Retrieve persisted evaluations for a bid, enforcing tender/bid scoping."""
    # Scoping check
    bid_stmt = select(Bid).where(Bid.id == bid_id, Bid.tender_id == tender_id)
    bid_res = await db.execute(bid_stmt)
    if bid_res.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bid not found"
        )

    stmt = (
        select(RequirementEvaluation)
        .where(
            RequirementEvaluation.bid_id == bid_id,
            RequirementEvaluation.tender_id == tender_id,
        )
        .order_by(RequirementEvaluation.created_at.asc())
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def get_bid_evaluation(
    db: AsyncSession, tender_id: UUID, bid_id: UUID, requirement_id: UUID
) -> RequirementEvaluation:
    """Retrieve a single requirement evaluation for a bid, enforcing scoping."""
    bid_stmt = select(Bid).where(Bid.id == bid_id, Bid.tender_id == tender_id)
    bid_res = await db.execute(bid_stmt)
    if bid_res.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bid not found"
        )

    req_stmt = select(Requirement).where(
        Requirement.id == requirement_id, Requirement.tender_id == tender_id
    )
    req_res = await db.execute(req_stmt)
    if req_res.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found"
        )

    stmt = select(RequirementEvaluation).where(
        RequirementEvaluation.bid_id == bid_id,
        RequirementEvaluation.tender_id == tender_id,
        RequirementEvaluation.requirement_id == requirement_id,
    )
    res = await db.execute(stmt)
    record = res.scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation not found for this requirement",
        )
    return record


async def get_bid_compliance_summary(
    db: AsyncSession, tender_id: UUID, bid_id: UUID
) -> BidComplianceSummaryResponse:
    """Deterministically aggregate requirement evaluations for a bid.

    Enforces tender/bid scoping.
    Preserves full provenance linking requirements to RequirementEvaluation and Evidence.
    Does NOT mutate Bid.status, Requirement, or Evidence.
    """
    # 1. Scoping check: verify bid exists and belongs to tender
    bid_stmt = select(Bid).where(Bid.id == bid_id, Bid.tender_id == tender_id)
    bid_res = await db.execute(bid_stmt)
    bid = bid_res.scalar_one_or_none()
    if bid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bid not found or does not belong to the specified tender",
        )

    # 2. Fetch all Requirements for tender in deterministic order
    req_stmt = (
        select(Requirement)
        .where(Requirement.tender_id == tender_id)
        .order_by(Requirement.created_at.asc(), Requirement.id.asc())
    )
    req_res = await db.execute(req_stmt)
    requirements = list(req_res.scalars().all())

    # 3. Fetch all persisted RequirementEvaluation records for bid
    eval_stmt = (
        select(RequirementEvaluation)
        .where(
            RequirementEvaluation.bid_id == bid_id,
            RequirementEvaluation.tender_id == tender_id,
        )
    )
    eval_res = await db.execute(eval_stmt)
    evaluations = list(eval_res.scalars().all())
    eval_map: dict[UUID, RequirementEvaluation] = {
        ev.requirement_id: ev for ev in evaluations
    }

    # 4. Deterministic aggregation
    total_requirements = len(requirements)
    evaluated_requirements = 0
    unevaluated_requirements = 0
    compliant = 0
    non_compliant = 0
    missing_evidence = 0
    low_confidence = 0
    error = 0

    mandatory_total = 0
    mandatory_evaluated = 0
    mandatory_compliant = 0
    mandatory_non_compliant = 0

    summary_items: list[RequirementSummaryItem] = []
    total_weight = 0.0
    compliant_weight = 0.0

    for req in requirements:
        weight_val = max(0.0, float(req.weight) if req.weight is not None else 1.0)
        total_weight += weight_val

        if req.is_mandatory:
            mandatory_total += 1

        ev = eval_map.get(req.id)
        if ev is None:
            unevaluated_requirements += 1
            item = RequirementSummaryItem(
                requirement_id=req.id,
                title=req.title,
                is_mandatory=req.is_mandatory,
                weight=float(req.weight) if req.weight is not None else 1.0,
                evaluation_id=None,
                status="UNEVALUATED",
                target_field=None,
                extracted_value=None,
                confidence=None,
                evidence_id=None,
                reason="Requirement has not been evaluated yet for this bid",
                details=None,
            )
        else:
            evaluated_requirements += 1
            if req.is_mandatory:
                mandatory_evaluated += 1

            if ev.status == EvaluationStatus.COMPLIANT:
                compliant += 1
                compliant_weight += weight_val
                if req.is_mandatory:
                    mandatory_compliant += 1
            elif ev.status == EvaluationStatus.NON_COMPLIANT:
                non_compliant += 1
                if req.is_mandatory:
                    mandatory_non_compliant += 1
            elif ev.status == EvaluationStatus.MISSING_EVIDENCE:
                missing_evidence += 1
                if req.is_mandatory:
                    mandatory_non_compliant += 1
            elif ev.status == EvaluationStatus.LOW_CONFIDENCE:
                low_confidence += 1
                if req.is_mandatory:
                    mandatory_non_compliant += 1
            elif ev.status == EvaluationStatus.ERROR:
                error += 1
                if req.is_mandatory:
                    mandatory_non_compliant += 1
            else:
                non_compliant += 1
                if req.is_mandatory:
                    mandatory_non_compliant += 1

            item = RequirementSummaryItem(
                requirement_id=req.id,
                title=req.title,
                is_mandatory=req.is_mandatory,
                weight=float(req.weight) if req.weight is not None else 1.0,
                evaluation_id=ev.id,
                status=ev.status,
                target_field=ev.target_field,
                extracted_value=ev.extracted_value,
                confidence=ev.confidence,
                evidence_id=ev.evidence_id,
                reason=ev.reason,
                details=ev.details,
            )
        summary_items.append(item)

    # 5. Ratios
    if total_requirements == 0:
        compliance_ratio = 1.0
        weighted_compliance_ratio = 1.0
    else:
        compliance_ratio = round(compliant / total_requirements, 4)
        if total_weight <= 0.0:
            weighted_compliance_ratio = compliance_ratio
        else:
            weighted_compliance_ratio = round(compliant_weight / total_weight, 4)

    # 6. Neutral Summary Status
    if error > 0:
        summary_status = ComplianceSummaryStatus.ERROR
    elif unevaluated_requirements > 0:
        summary_status = ComplianceSummaryStatus.INCOMPLETE
    elif (
        mandatory_compliant < mandatory_total
        or non_compliant > 0
        or missing_evidence > 0
        or low_confidence > 0
    ):
        summary_status = ComplianceSummaryStatus.REVIEW_REQUIRED
    else:
        summary_status = ComplianceSummaryStatus.READY_FOR_REVIEW

    return BidComplianceSummaryResponse(
        bid_id=bid_id,
        tender_id=tender_id,
        total_requirements=total_requirements,
        evaluated_requirements=evaluated_requirements,
        unevaluated_requirements=unevaluated_requirements,
        compliant=compliant,
        non_compliant=non_compliant,
        missing_evidence=missing_evidence,
        low_confidence=low_confidence,
        error=error,
        mandatory_total=mandatory_total,
        mandatory_evaluated=mandatory_evaluated,
        mandatory_compliant=mandatory_compliant,
        mandatory_non_compliant=mandatory_non_compliant,
        summary_status=summary_status,
        compliance_ratio=compliance_ratio,
        weighted_compliance_ratio=weighted_compliance_ratio,
        requirements=summary_items,
    )

