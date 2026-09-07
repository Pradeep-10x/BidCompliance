from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bid import Bid
from app.models.document import Document
from app.models.tender import Tender
from app.schemas.document import DocumentCreate, DocumentUpdate


async def get_tender(db: AsyncSession, tender_id: UUID) -> Tender | None:
    return await db.get(Tender, tender_id)


async def get_bid(
    db: AsyncSession, tender_id: UUID, bid_id: UUID
) -> Bid | None:
    result = await db.execute(
        select(Bid).where(Bid.id == bid_id, Bid.tender_id == tender_id)
    )
    return result.scalar_one_or_none()


async def create_document(
    db: AsyncSession, bid_id: UUID, document_in: DocumentCreate
) -> Document:
    document = Document(bid_id=bid_id, **document_in.model_dump())
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document


async def list_documents(
    db: AsyncSession, bid_id: UUID, skip: int, limit: int
) -> list[Document]:
    result = await db.execute(
        select(Document)
        .where(Document.bid_id == bid_id)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_document(
    db: AsyncSession, bid_id: UUID, document_id: UUID
) -> Document | None:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.bid_id == bid_id,
        )
    )
    return result.scalar_one_or_none()


async def update_document(
    db: AsyncSession, document: Document, document_in: DocumentUpdate
) -> Document:
    for field, value in document_in.model_dump(exclude_unset=True).items():
        setattr(document, field, value)
    await db.commit()
    await db.refresh(document)
    return document
