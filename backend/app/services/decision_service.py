from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance import Assessment, Decision
from app.schemas.compliance import DecisionCreate
from app.services.audit_service import append_audit_event


async def create_decision(
    db: AsyncSession,
    *,
    assessment: Assessment,
    officer_id: UUID,
    decision_in: DecisionCreate,
) -> Decision:
    decision = Decision(
        assessment_id=assessment.id,
        officer_id=officer_id,
        action=decision_in.action,
        reason=decision_in.reason.strip() if decision_in.reason else None,
    )
    db.add(decision)
    await append_audit_event(
        db,
        event_type="OFFICER_DECISION_RECORDED",
        tender_id=assessment.tender_id,
        bid_id=assessment.bid_id,
        actor_id=officer_id,
        payload={
            "assessment_id": str(assessment.id),
            "assessment_version": assessment.version,
            "action": decision.action,
            "reason": decision.reason,
        },
    )
    await db.commit()
    await db.refresh(decision)
    return decision
