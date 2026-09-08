from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.compliance import (
    Assessment,
    ExtractedFact,
    Finding,
    RequirementResult,
    VerificationResult,
)
from app.models.document import Document
from app.models.requirement import Requirement
from app.services.audit_service import append_audit_event


@dataclass(frozen=True)
class Evaluation:
    status: str
    reason: str
    evidence_refs: list[str]


def _normalized(value: Any) -> str:
    return " ".join(str(value).strip().upper().split())


def evaluate_rule(
    rule: dict[str, Any],
    *,
    facts: dict[str, ExtractedFact],
    document_types: set[str],
    verifications: dict[str, VerificationResult],
) -> Evaluation:
    kind = str(rule.get("kind") or "").lower()
    if not kind:
        return Evaluation("REVIEW", "No deterministic rule is configured", [])

    if kind == "not_applicable":
        return Evaluation("NOT_APPLICABLE", "Requirement marked not applicable", [])

    if kind == "evidence_present":
        expected = rule.get("document_types") or [rule.get("document_type")]
        expected = {_normalized(item) for item in expected if item}
        present = {_normalized(item) for item in document_types}
        matched = sorted(expected & present)
        if matched:
            return Evaluation(
                "PASS", f"Required evidence is present: {', '.join(matched)}", []
            )
        status = str(rule.get("on_missing") or "FAIL").upper()
        return Evaluation(
            status, f"Required evidence is missing: {', '.join(sorted(expected))}", []
        )

    if kind == "field_present":
        field_name = str(rule.get("field") or "")
        fact = facts.get(field_name)
        if fact and fact.normalized_value:
            return Evaluation(
                "PASS", f"Extracted field {field_name} is present", [fact.evidence_id]
            )
        status = str(rule.get("on_missing") or "REVIEW").upper()
        return Evaluation(status, f"Extracted field {field_name} is missing", [])

    if kind == "field_equals":
        field_name = str(rule.get("field") or "")
        fact = facts.get(field_name)
        if not fact or not fact.normalized_value:
            return Evaluation(
                str(rule.get("on_missing") or "REVIEW").upper(),
                f"Extracted field {field_name} is missing",
                [],
            )
        expected_values = rule.get("allowed_values") or [rule.get("expected")]
        expected = {
            _normalized(value) for value in expected_values if value is not None
        }
        actual = _normalized(fact.normalized_value)
        if actual in expected:
            return Evaluation(
                "PASS", f"{field_name} matches an allowed value", [fact.evidence_id]
            )
        return Evaluation(
            "FAIL",
            f"{field_name} value {fact.normalized_value!r} is not allowed",
            [fact.evidence_id],
        )

    if kind == "verification_status":
        source = str(rule.get("source") or "").upper()
        verification = verifications.get(source)
        if verification is None:
            return Evaluation(
                str(rule.get("on_missing") or "UNVERIFIED").upper(),
                f"No {source} verification result is available",
                [],
            )
        if verification.status == "UNAVAILABLE":
            return Evaluation(
                str(rule.get("on_unavailable") or "REVIEW").upper(),
                f"{source} source was unavailable",
                list(verification.evidence_refs),
            )
        allowed = {
            str(item).upper() for item in (rule.get("allowed_statuses") or ["VERIFIED"])
        }
        if verification.status in allowed:
            return Evaluation(
                "PASS",
                f"{source} verification status is {verification.status}",
                list(verification.evidence_refs),
            )
        failure_status = str(rule.get("on_failure") or "FAIL").upper()
        return Evaluation(
            failure_status,
            f"{source} verification status is {verification.status}",
            list(verification.evidence_refs),
        )

    return Evaluation("REVIEW", f"Unsupported rule kind: {kind}", [])


def _percent(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def run_assessment(
    db: AsyncSession,
    *,
    tender_id: UUID,
    bid_id: UUID,
    actor_id: UUID,
) -> Assessment:
    requirements_result = await db.execute(
        select(Requirement)
        .where(
            Requirement.tender_id == tender_id,
            Requirement.status.in_(["CONFIRMED", "ADDED_MANUALLY"]),
        )
        .order_by(Requirement.created_at.asc())
    )
    requirements = list(requirements_result.scalars().all())
    if not requirements:
        raise ValueError("Tender has no confirmed or manually added requirements")

    documents_result = await db.execute(
        select(Document).where(Document.bid_id == bid_id)
    )
    documents = list(documents_result.scalars().all())
    document_types = {document.document_type for document in documents}

    facts_result = await db.execute(
        select(ExtractedFact)
        .join(Document, Document.id == ExtractedFact.document_id)
        .where(Document.bid_id == bid_id)
        .order_by(ExtractedFact.created_at.desc())
    )
    facts: dict[str, ExtractedFact] = {}
    for fact in facts_result.scalars().all():
        facts.setdefault(fact.field_name, fact)

    verifications_result = await db.execute(
        select(VerificationResult)
        .where(VerificationResult.bid_id == bid_id)
        .order_by(VerificationResult.checked_at.desc())
    )
    verifications: dict[str, VerificationResult] = {}
    for verification in verifications_result.scalars().all():
        verifications.setdefault(verification.source, verification)

    version_result = await db.execute(
        select(func.coalesce(func.max(Assessment.version), 0)).where(
            Assessment.bid_id == bid_id
        )
    )
    version = int(version_result.scalar_one()) + 1
    assessment = Assessment(
        tender_id=tender_id,
        bid_id=bid_id,
        version=version,
        mandatory_gate_status="PENDING",
        compliance_score=Decimal("0"),
        verification_depth=Decimal("0"),
        evidence_coverage=Decimal("0"),
        risk_level="LOW",
        rule_version_set={"engine": "deterministic-v1"},
    )
    db.add(assessment)
    await db.flush()

    evaluations: list[tuple[Requirement, Evaluation]] = []
    for requirement in requirements:
        rule_snapshot = requirement.rule_config or {}
        evaluation = evaluate_rule(
            rule_snapshot,
            facts=facts,
            document_types=document_types,
            verifications=verifications,
        )
        evaluations.append((requirement, evaluation))
        db.add(
            RequirementResult(
                assessment_id=assessment.id,
                requirement_id=requirement.id,
                status=evaluation.status,
                reason=evaluation.reason,
                evidence_refs=evaluation.evidence_refs,
                rule_snapshot=rule_snapshot,
                is_mandatory=requirement.is_mandatory,
                weight=requirement.weight,
            )
        )

        if evaluation.status not in {"PASS", "NOT_APPLICABLE"}:
            severity = (
                "CRITICAL"
                if requirement.is_mandatory and evaluation.status == "FAIL"
                else ("HIGH" if evaluation.status == "FAIL" else "MEDIUM")
            )
            db.add(
                Finding(
                    assessment_id=assessment.id,
                    requirement_id=requirement.id,
                    finding_type="REQUIREMENT_RESULT",
                    severity=severity,
                    title=f"{requirement.title}: {evaluation.status}",
                    description=evaluation.reason,
                    evidence_refs=evaluation.evidence_refs,
                )
            )

    mandatory_statuses = [
        evaluation.status
        for requirement, evaluation in evaluations
        if requirement.is_mandatory
    ]
    if any(value == "FAIL" for value in mandatory_statuses):
        assessment.mandatory_gate_status = "FAIL"
    elif any(value in {"REVIEW", "UNVERIFIED"} for value in mandatory_statuses):
        assessment.mandatory_gate_status = "REVIEW"
    else:
        assessment.mandatory_gate_status = "PASS"

    applicable = [
        (requirement, evaluation)
        for requirement, evaluation in evaluations
        if evaluation.status != "NOT_APPLICABLE"
    ]
    total_weight = sum(
        (requirement.weight for requirement, _ in applicable), Decimal("0")
    )
    passed_weight = sum(
        (
            requirement.weight
            for requirement, evaluation in applicable
            if evaluation.status == "PASS"
        ),
        Decimal("0"),
    )
    assessment.compliance_score = _percent(
        (passed_weight / total_weight * 100) if total_weight else Decimal("0")
    )
    assessment.evidence_coverage = _percent(
        Decimal(sum(1 for _, evaluation in applicable if evaluation.evidence_refs))
        / Decimal(len(applicable))
        * 100
        if applicable
        else Decimal("0")
    )
    assessment.verification_depth = _percent(
        Decimal(sum(1 for item in verifications.values() if item.status == "VERIFIED"))
        / Decimal(len(verifications))
        * 100
        if verifications
        else Decimal("0")
    )

    statuses = {evaluation.status for _, evaluation in evaluations}
    verification_statuses = {item.status for item in verifications.values()}
    if assessment.mandatory_gate_status == "FAIL":
        assessment.risk_level = "CRITICAL"
    elif "FAIL" in statuses or "MISMATCH" in verification_statuses:
        assessment.risk_level = "HIGH"
    elif statuses & {"REVIEW", "UNVERIFIED"} or "UNAVAILABLE" in verification_statuses:
        assessment.risk_level = "MEDIUM"
    else:
        assessment.risk_level = "LOW"

    await append_audit_event(
        db,
        event_type="ASSESSMENT_COMPLETED",
        tender_id=tender_id,
        bid_id=bid_id,
        actor_id=actor_id,
        payload={
            "assessment_id": str(assessment.id),
            "version": version,
            "mandatory_gate_status": assessment.mandatory_gate_status,
            "compliance_score": str(assessment.compliance_score),
            "risk_level": assessment.risk_level,
        },
    )
    await db.commit()
    return await get_assessment(db, assessment.id)


async def get_assessment(db: AsyncSession, assessment_id: UUID) -> Assessment | None:
    result = await db.execute(
        select(Assessment)
        .where(Assessment.id == assessment_id)
        .options(
            selectinload(Assessment.requirement_results),
            selectinload(Assessment.findings),
        )
    )
    return result.scalar_one_or_none()


async def get_latest_assessment(
    db: AsyncSession, tender_id: UUID, bid_id: UUID
) -> Assessment | None:
    result = await db.execute(
        select(Assessment)
        .where(Assessment.tender_id == tender_id, Assessment.bid_id == bid_id)
        .order_by(Assessment.version.desc())
        .options(
            selectinload(Assessment.requirement_results),
            selectinload(Assessment.findings),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()
