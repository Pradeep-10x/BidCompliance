import uuid
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance import ExtractedFact, VerificationResult
from app.models.document import Document
from app.schemas.compliance import VerificationRunRequest
from app.services.audit_service import append_audit_event

IDENTIFIER_FIELDS = {
    "UDYAM": ("udyam_registration_number", "udyam_number"),
    "MCA": ("cin",),
    "GST": ("gstin",),
    "PAN": ("pan", "pan_number"),
    "BIS": ("bis_license_number", "license_number"),
}

SCENARIO_STATUS = {
    "MATCH": "VERIFIED",
    "MISMATCH": "MISMATCH",
    "NOT_FOUND": "NOT_FOUND",
    "UNAVAILABLE": "UNAVAILABLE",
    "EXPIRED": "EXPIRED",
}


async def run_mock_verification(
    db: AsyncSession,
    *,
    tender_id: UUID,
    bid_id: UUID,
    request: VerificationRunRequest,
    actor_id: UUID,
) -> VerificationResult:
    source = request.source.strip().upper()
    fields_result = await db.execute(
        select(ExtractedFact, Document)
        .join(Document, Document.id == ExtractedFact.document_id)
        .where(Document.bid_id == bid_id)
        .order_by(ExtractedFact.created_at.desc())
    )
    extracted: dict[str, tuple[ExtractedFact, Document]] = {}
    for fact, document in fields_result.all():
        extracted.setdefault(fact.field_name, (fact, document))

    identifier_fact: ExtractedFact | None = None
    identifier_document: Document | None = None
    for field_name in IDENTIFIER_FIELDS.get(source, (source.lower(),)):
        candidate = extracted.get(field_name)
        if candidate and candidate[0].normalized_value:
            identifier_fact, identifier_document = candidate
            break

    scenario = request.scenario
    if scenario == "MATCH" and identifier_fact is None:
        status_value = "REVIEW"
        warnings = [f"No extracted identifier was available for {source}"]
    else:
        status_value = SCENARIO_STATUS[scenario]
        warnings = (
            ["Synthetic source outage scenario"] if scenario == "UNAVAILABLE" else []
        )

    identifier_value = identifier_fact.normalized_value if identifier_fact else None
    matched_fields = []
    mismatches = []
    if status_value == "VERIFIED" and identifier_fact:
        matched_fields = [
            {
                "field": identifier_fact.field_name,
                "value": identifier_value,
                "match": "EXACT",
            }
        ]
    elif status_value == "MISMATCH" and identifier_fact:
        mismatches = [
            {
                "field": identifier_fact.field_name,
                "submitted": identifier_value,
                "source": f"MISMATCH-{identifier_value}",
            }
        ]

    verification = VerificationResult(
        bid_id=bid_id,
        document_id=identifier_document.id if identifier_document else None,
        source=source,
        mode="MOCK",
        request_id=f"mock-{source.lower()}-{uuid.uuid4()}",
        effective_date=request.effective_date or datetime.now(timezone.utc),
        status=status_value,
        source_record_id=identifier_value
        if status_value not in {"NOT_FOUND", "UNAVAILABLE"}
        else None,
        fields={"identifier": identifier_value, "scenario": scenario},
        matched_fields=matched_fields,
        mismatches=mismatches,
        warnings=warnings,
        evidence_refs=[identifier_fact.evidence_id] if identifier_fact else [],
        adapter_version="mock-v1",
        confidence=Decimal("1.0") if status_value == "VERIFIED" else Decimal("0.8"),
    )
    db.add(verification)
    await append_audit_event(
        db,
        event_type="SOURCE_VERIFICATION_COMPLETED",
        tender_id=tender_id,
        bid_id=bid_id,
        actor_id=actor_id,
        payload={
            "verification_id": str(verification.id),
            "source": source,
            "mode": "MOCK",
            "scenario": scenario,
            "status": status_value,
            "request_id": verification.request_id,
        },
    )
    await db.commit()
    await db.refresh(verification)
    return verification


async def list_verifications(
    db: AsyncSession, bid_id: UUID
) -> list[VerificationResult]:
    result = await db.execute(
        select(VerificationResult)
        .where(VerificationResult.bid_id == bid_id)
        .order_by(VerificationResult.checked_at.desc())
    )
    return list(result.scalars().all())
