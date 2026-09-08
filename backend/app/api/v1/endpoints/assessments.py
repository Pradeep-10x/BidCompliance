from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import get_current_active_user
from app.models.bid import Bid
from app.models.compliance import Assessment, Decision
from app.models.user import User
from app.schemas.compliance import AssessmentResponse, DecisionCreate, DecisionResponse
from app.services.assessment_service import get_latest_assessment, run_assessment
from app.services.decision_service import create_decision

router = APIRouter()


async def require_bid(db: AsyncSession, tender_id: UUID, bid_id: UUID) -> Bid:
    result = await db.execute(
        select(Bid).where(Bid.id == bid_id, Bid.tender_id == tender_id)
    )
    bid = result.scalar_one_or_none()
    if bid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tender or bid not found"
        )
    return bid


@router.post(
    "/run", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED
)
async def run(
    tender_id: UUID,
    bid_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Assessment:
    await require_bid(db, tender_id, bid_id)
    try:
        return await run_assessment(
            db, tender_id=tender_id, bid_id=bid_id, actor_id=current_user.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/latest", response_model=AssessmentResponse)
async def latest(
    tender_id: UUID,
    bid_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> Assessment:
    await require_bid(db, tender_id, bid_id)
    assessment = await get_latest_assessment(db, tender_id, bid_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment


@router.post(
    "/{assessment_id}/decisions",
    response_model=DecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def decide(
    tender_id: UUID,
    bid_id: UUID,
    assessment_id: UUID,
    decision_in: DecisionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Decision:
    await require_bid(db, tender_id, bid_id)
    assessment = await get_latest_assessment(db, tender_id, bid_id)
    if assessment is None or assessment.id != assessment_id:
        raise HTTPException(
            status_code=409,
            detail="Decisions can only be recorded against the latest assessment",
        )
    return await create_decision(
        db, assessment=assessment, officer_id=current_user.id, decision_in=decision_in
    )
