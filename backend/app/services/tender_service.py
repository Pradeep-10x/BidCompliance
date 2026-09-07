from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tender import Tender
from app.schemas.tender import TenderCreate, TenderUpdate


class DuplicateReferenceNumberError(Exception):
    pass


class InvalidTenderDatesError(Exception):
    pass


async def create_tender(db: AsyncSession, tender_in: TenderCreate) -> Tender:
    tender = Tender(**tender_in.model_dump())
    db.add(tender)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise DuplicateReferenceNumberError from exc
    await db.refresh(tender)
    return tender


async def list_tenders(
    db: AsyncSession, skip: int, limit: int
) -> list[Tender]:
    result = await db.execute(
        select(Tender).order_by(Tender.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def get_tender(db: AsyncSession, tender_id: UUID) -> Tender | None:
    return await db.get(Tender, tender_id)


async def update_tender(
    db: AsyncSession, tender: Tender, tender_in: TenderUpdate
) -> Tender:
    updates = tender_in.model_dump(exclude_unset=True)
    opening_date = updates.get("opening_date", tender.opening_date)
    closing_date = updates.get("closing_date", tender.closing_date)
    if (
        opening_date is not None
        and closing_date is not None
        and closing_date < opening_date
    ):
        raise InvalidTenderDatesError
    for field, value in updates.items():
        setattr(tender, field, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise DuplicateReferenceNumberError from exc
    await db.refresh(tender)
    return tender


async def delete_tender(db: AsyncSession, tender: Tender) -> None:
    await db.delete(tender)
    await db.commit()
