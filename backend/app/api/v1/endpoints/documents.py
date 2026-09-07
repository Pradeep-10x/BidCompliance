from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import get_current_active_user
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentCreate, DocumentResponse, DocumentUpdate
from app.services.document_service import (
    create_document,
    get_bid,
    get_document,
    get_tender,
    list_documents,
    update_document,
)

router = APIRouter()


def not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


async def require_bid(
    db: AsyncSession, tender_id: UUID, bid_id: UUID
) -> None:
    if await get_tender(db, tender_id) is None:
        raise not_found("Tender not found")
    if await get_bid(db, tender_id, bid_id) is None:
        raise not_found("Bid not found")


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create(
    tender_id: UUID,
    bid_id: UUID,
    document_in: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> Document:
    await require_bid(db, tender_id, bid_id)
    return await create_document(db, bid_id, document_in)


@router.get("", response_model=list[DocumentResponse])
async def list_all(
    tender_id: UUID,
    bid_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> list[Document]:
    await require_bid(db, tender_id, bid_id)
    return await list_documents(db, bid_id, skip, limit)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_one(
    tender_id: UUID,
    bid_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> Document:
    await require_bid(db, tender_id, bid_id)
    document = await get_document(db, bid_id, document_id)
    if document is None:
        raise not_found("Document not found")
    return document


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update(
    tender_id: UUID,
    bid_id: UUID,
    document_id: UUID,
    document_in: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> Document:
    await require_bid(db, tender_id, bid_id)
    document = await get_document(db, bid_id, document_id)
    if document is None:
        raise not_found("Document not found")
    return await update_document(db, document, document_in)
