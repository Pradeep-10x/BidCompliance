import io
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.rbac import get_current_active_user
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentResponse, DocumentUpdate
from app.schemas.compliance import DocumentProcessingResponse, ExtractedFactResponse
from app.services.document_service import (
    create_document,
    get_bid,
    get_document,
    get_tender,
    list_documents,
    update_document,
)
from app.services.storage_service import (
    EmptyUploadError,
    StorageError,
    StoredObjectNotFoundError,
    UploadTooLargeError,
    generate_object_key,
    get_storage_service,
    normalize_filename,
)
from app.core.queue import JobPublisher, get_job_publisher
from app.schemas.job import ProcessingJobResponse
from app.services.job_service import (
    get_job_for_document,
    list_document_jobs,
)
from app.schemas.evidence import EvidenceResponse
from app.services.evidence_service import (
    get_document_evidence,
    list_document_evidence,
)
from app.services.processing_service import (
    list_document_facts,
    process_document_with_ml,
    store_uploaded_document,
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


SUPPORTED_MIME_TYPES = {
    "application/pdf": b"%PDF-",
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/jpeg": b"\xff\xd8\xff",
    "image/jpg": b"\xff\xd8\xff",
}


async def validate_upload(file: UploadFile) -> str:
    mime_type = (file.content_type or "").split(";", 1)[0].lower()
    signature = SUPPORTED_MIME_TYPES.get(mime_type)
    if signature is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported document MIME type",
        )
    header = await file.read(max(len(value) for value in SUPPORTED_MIME_TYPES.values()))
    await file.seek(0)
    if not header.startswith(signature):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file signature does not match its MIME type",
        )
    return mime_type


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload, validate, hash, and store a bidder document",
)
async def upload_document(
    tender_id: UUID,
    bid_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Document:
    await require_bid(db, tender_id, bid_id)
    return await store_uploaded_document(
        db,
        tender_id=tender_id,
        bid_id=bid_id,
        actor_id=current_user.id,
        upload=file,
    )


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create(
    tender_id: UUID,
    bid_id: UUID,
    file: UploadFile = File(...),
    document_type: str = Form(default="GENERAL"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
    storage=Depends(get_storage_service),
    publisher: JobPublisher = Depends(get_job_publisher),
) -> Document:
    await require_bid(db, tender_id, bid_id)
    mime_type = await validate_upload(file)
    if not document_type.strip() or len(document_type) > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="document_type must contain 1 to 100 characters",
        )
    try:
        stored = await storage.store(
            file,
            generate_object_key(file.filename),
            settings.MAX_UPLOAD_SIZE_BYTES,
        )
        document = await create_document(
            db,
            bid_id,
            normalize_filename(file.filename),
            document_type.strip(),
            mime_type,
            stored,
            storage,
        )
        if settings.PROCESSING_QUEUE_ENABLED:
            from app.services.job_service import create_initial_job

            await create_initial_job(db, document.id, publisher)
        return document
    except EmptyUploadError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )
    except UploadTooLargeError:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded file exceeds the maximum size",
        )
    except StorageError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document storage failed",
        )


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


@router.post("/{document_id}/process", response_model=DocumentProcessingResponse)
async def process_document(
    tender_id: UUID,
    bid_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DocumentProcessingResponse:
    await require_bid(db, tender_id, bid_id)
    document = await get_document(db, bid_id, document_id)
    if document is None:
        raise not_found("Document not found")
    facts, confidence, warnings = await process_document_with_ml(
        db,
        document=document,
        tender_id=tender_id,
        actor_id=current_user.id,
    )
    await db.refresh(document)
    return DocumentProcessingResponse(
        document_id=document.id,
        processing_status=document.processing_status.value,
        document_type=document.document_type,
        classification_confidence=confidence,
        facts=[ExtractedFactResponse.model_validate(fact) for fact in facts],
        warnings=warnings,
    )


@router.get("/{document_id}/facts", response_model=list[ExtractedFactResponse])
async def get_facts(
    tender_id: UUID,
    bid_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    await require_bid(db, tender_id, bid_id)
    document = await get_document(db, bid_id, document_id)
    if document is None:
        raise not_found("Document not found")
    return await list_document_facts(db, document.id)


@router.get("/{document_id}/download", response_class=StreamingResponse)
async def download_document(
    tender_id: UUID,
    bid_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    await require_bid(db, tender_id, bid_id)
    document = await get_document(db, bid_id, document_id)
    if document is None:
        raise not_found("Document not found")
    storage = get_storage_service(settings.STORAGE_ROOT)
    try:
        content = await storage.read(document.storage_path)
    except StoredObjectNotFoundError:
        raise not_found("Stored document bytes were not found")
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document storage is unavailable",
        ) from exc
    safe_filename = normalize_filename(document.original_filename).replace('"', "")
    return StreamingResponse(
        io.BytesIO(content),
        media_type=document.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "Content-Length": str(len(content)),
        },
    )


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


@router.get("/{document_id}/jobs", response_model=list[ProcessingJobResponse])
async def list_jobs(
    tender_id: UUID,
    bid_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> list:
    await require_bid(db, tender_id, bid_id)
    if await get_document(db, bid_id, document_id) is None:
        raise not_found("Document not found")
    return await list_document_jobs(db, tender_id, bid_id, document_id)


@router.get(
    "/{document_id}/jobs/{job_id}", response_model=ProcessingJobResponse
)
async def get_job_status(
    tender_id: UUID,
    bid_id: UUID,
    document_id: UUID,
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    await require_bid(db, tender_id, bid_id)
    job = await get_job_for_document(
        db, tender_id, bid_id, document_id, job_id
    )
    if job is None:
        raise not_found("Processing job not found")
    return job


@router.get("/{document_id}/evidence", response_model=list[EvidenceResponse])
async def list_evidence(
    tender_id: UUID,
    bid_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> list:
    await require_bid(db, tender_id, bid_id)
    if await get_document(db, bid_id, document_id) is None:
        raise not_found("Document not found")
    return await list_document_evidence(db, document_id)


@router.get(
    "/{document_id}/evidence/{evidence_id}", response_model=EvidenceResponse
)
async def get_evidence(
    tender_id: UUID,
    bid_id: UUID,
    document_id: UUID,
    evidence_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    await require_bid(db, tender_id, bid_id)
    if await get_document(db, bid_id, document_id) is None:
        raise not_found("Document not found")
    evidence = await get_document_evidence(db, document_id, evidence_id)
    if evidence is None:
        raise not_found("Evidence not found")
    return evidence
