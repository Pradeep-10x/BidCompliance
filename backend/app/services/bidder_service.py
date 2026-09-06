from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bidder import Bidder
from app.schemas.bidder import BidderCreate, BidderUpdate


async def create_bidder(db: AsyncSession, bidder_in: BidderCreate) -> Bidder:
    values = bidder_in.model_dump(exclude_unset=True)
    bidder = Bidder(**values)
    db.add(bidder)
    await db.commit()
    await db.refresh(bidder)
    return bidder


async def list_bidders(
    db: AsyncSession, skip: int, limit: int
) -> list[Bidder]:
    result = await db.execute(
        select(Bidder).order_by(Bidder.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def get_bidder(db: AsyncSession, bidder_id: UUID) -> Bidder | None:
    return await db.get(Bidder, bidder_id)


async def update_bidder(
    db: AsyncSession, bidder: Bidder, bidder_in: BidderUpdate
) -> Bidder:
    for field, value in bidder_in.model_dump(exclude_unset=True).items():
        setattr(bidder, field, value)
    await db.commit()
    await db.refresh(bidder)
    return bidder
