from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import get_current_active_user
from app.models.bid import Bid
from app.models.user import User
from app.schemas.bid import BidCreate, BidResponse, BidUpdate
from app.services.bid_service import (
    DuplicateBidError,
    create_bid,
    get_bid,
    get_bidder,
    get_tender,
    list_bids,
    update_bid,
)

router = APIRouter()


def not_found(detail: str = "Tender or bid not found") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


async def require_tender(db: AsyncSession, tender_id: UUID) -> None:
    if await get_tender(db, tender_id) is None:
        raise not_found("Tender not found")


async def require_bidder(db: AsyncSession, bidder_id: UUID) -> None:
    if await get_bidder(db, bidder_id) is None:
        raise not_found("Bidder not found")


@router.post("", response_model=BidResponse, status_code=status.HTTP_201_CREATED)
async def create(
    tender_id: UUID,
    bid_in: BidCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> Bid:
    await require_tender(db, tender_id)
    await require_bidder(db, bid_in.bidder_id)
    try:
        return await create_bid(db, tender_id, bid_in)
    except DuplicateBidError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bidder already has a bid for this tender",
        )


@router.get("", response_model=list[BidResponse])
async def list_all(
    tender_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> list[Bid]:
    await require_tender(db, tender_id)
    return await list_bids(db, tender_id, skip, limit)


@router.get("/{bid_id}", response_model=BidResponse)
async def get_one(
    tender_id: UUID,
    bid_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> Bid:
    await require_tender(db, tender_id)
    bid = await get_bid(db, tender_id, bid_id)
    if bid is None:
        raise not_found()
    return bid


@router.patch("/{bid_id}", response_model=BidResponse)
async def update(
    tender_id: UUID,
    bid_id: UUID,
    bid_in: BidUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> Bid:
    await require_tender(db, tender_id)
    bid = await get_bid(db, tender_id, bid_id)
    if bid is None:
        raise not_found()
    if bid_in.bidder_id is not None:
        await require_bidder(db, bid_in.bidder_id)
    try:
        return await update_bid(db, bid, bid_in)
    except DuplicateBidError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bidder already has a bid for this tender",
        )
