from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import get_current_active_user
from app.models.bid import Bid
from app.models.compliance import VerificationResult
from app.models.user import User
from app.schemas.compliance import VerificationResultResponse, VerificationRunRequest
from app.services.verification_service import run_mock_verification

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
    "/run",
    response_model=VerificationResultResponse,
    status_code=status.HTTP_201_CREATED,
)
async def run(
    tender_id: UUID,
    bid_id: UUID,
    verification_in: VerificationRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> VerificationResult:
    await require_bid(db, tender_id, bid_id)
    return await run_mock_verification(
        db,
        tender_id=tender_id,
        bid_id=bid_id,
        request=verification_in,
        actor_id=current_user.id,
    )


@router.get("", response_model=list[VerificationResultResponse])
async def list_all(
    tender_id: UUID,
    bid_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> list[VerificationResult]:
    await require_bid(db, tender_id, bid_id)
    result = await db.execute(
        select(VerificationResult)
        .where(VerificationResult.bid_id == bid_id)
        .order_by(VerificationResult.checked_at.desc())
    )
    return list(result.scalars().all())
