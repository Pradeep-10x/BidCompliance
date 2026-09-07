from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bid import Bid
from app.models.bidder import Bidder
from app.models.tender import Tender
from app.schemas.bid import BidCreate, BidUpdate


class DuplicateBidError(Exception):
    pass


async def get_tender(db: AsyncSession, tender_id: UUID) -> Tender | None:
    return await db.get(Tender, tender_id)


async def get_bidder(db: AsyncSession, bidder_id: UUID) -> Bidder | None:
    return await db.get(Bidder, bidder_id)


async def create_bid(
    db: AsyncSession, tender_id: UUID, bid_in: BidCreate
) -> Bid:
    bid = Bid(tender_id=tender_id, **bid_in.model_dump())
    db.add(bid)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise DuplicateBidError from exc
    await db.refresh(bid)
    return bid


async def list_bids(db: AsyncSession, tender_id: UUID, skip: int, limit: int) -> list[Bid]:
    result = await db.execute(
        select(Bid)
        .where(Bid.tender_id == tender_id)
        .order_by(Bid.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_bid(
    db: AsyncSession, tender_id: UUID, bid_id: UUID
) -> Bid | None:
    result = await db.execute(
        select(Bid).where(Bid.id == bid_id, Bid.tender_id == tender_id)
    )
    return result.scalar_one_or_none()


async def update_bid(db: AsyncSession, bid: Bid, bid_in: BidUpdate) -> Bid:
    for field, value in bid_in.model_dump(exclude_unset=True).items():
        setattr(bid, field, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise DuplicateBidError from exc
    await db.refresh(bid)
    return bid
