from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import get_current_active_user
from app.models.tender import Tender
from app.models.user import User
from app.schemas.tender import TenderCreate, TenderResponse, TenderUpdate
from app.schemas.tender_document import TenderAnalysisResponse, TenderDocumentResponse
from app.services.tender_service import (
    DuplicateReferenceNumberError,
    InvalidTenderDatesError,
    create_tender,
    delete_tender,
    get_tender,
    list_tenders,
    update_tender,
)
from app.services.tender_analysis_service import (
    analyze_latest_tender,
    list_tender_documents,
    store_tender_document,
)

router = APIRouter()


def tender_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tender not found")


@router.post(
    "/{tender_id}/documents",
    response_model=TenderDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_tender_document(
    tender_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    tender = await get_tender(db, tender_id)
    if tender is None:
        raise tender_not_found()
    return await store_tender_document(
        db, tender_id=tender_id, actor_id=current_user.id, upload=file
    )


@router.get("/{tender_id}/documents", response_model=list[TenderDocumentResponse])
async def get_tender_documents(
    tender_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    tender = await get_tender(db, tender_id)
    if tender is None:
        raise tender_not_found()
    return await list_tender_documents(db, tender_id)


@router.post("/{tender_id}/analyze", response_model=TenderAnalysisResponse)
async def analyze_tender(
    tender_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    tender = await get_tender(db, tender_id)
    if tender is None:
        raise tender_not_found()
    document, candidates, warnings = await analyze_latest_tender(
        db, tender_id=tender_id, actor_id=current_user.id
    )
    return TenderAnalysisResponse(
        tender_document_id=document.id,
        processing_status=document.processing_status,
        extracted_character_count=len(document.extracted_text or ""),
        candidates=candidates,
        warnings=warnings,
    )


@router.post("", response_model=TenderResponse, status_code=status.HTTP_201_CREATED)
async def create(
    tender_in: TenderCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> Tender:
    try:
        return await create_tender(db, tender_in)
    except DuplicateReferenceNumberError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reference number already exists",
        )


@router.get("", response_model=list[TenderResponse])
async def list_all(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> list[Tender]:
    return await list_tenders(db, skip, limit)


@router.get("/{tender_id}", response_model=TenderResponse)
async def get_one(
    tender_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> Tender:
    tender = await get_tender(db, tender_id)
    if tender is None:
        raise tender_not_found()
    return tender


@router.patch("/{tender_id}", response_model=TenderResponse)
async def update(
    tender_id: UUID,
    tender_in: TenderUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> Tender:
    tender = await get_tender(db, tender_id)
    if tender is None:
        raise tender_not_found()
    try:
        return await update_tender(db, tender, tender_in)
    except InvalidTenderDatesError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="closing_date must be on or after opening_date",
        )
    except DuplicateReferenceNumberError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reference number already exists",
        )


@router.delete("/{tender_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    tender_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> None:
    tender = await get_tender(db, tender_id)
    if tender is None:
        raise tender_not_found()
    await delete_tender(db, tender)
