import hashlib
import json
import mimetypes
import uuid
from decimal import Decimal
from pathlib import Path, PurePosixPath
from uuid import UUID

import httpx
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.compliance import ExtractedFact
from app.models.document import Document, DocumentProcessingStatus
from app.services.audit_service import append_audit_event
from app.services.storage_service import (
    StorageError,
    StoredObjectNotFoundError,
    get_storage_service,
)

ALLOWED_SIGNATURES = {
    "application/pdf": lambda value: value.startswith(b"%PDF"),
    "image/png": lambda value: value.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/jpeg": lambda value: value.startswith(b"\xff\xd8\xff"),
}


def _safe_name(filename: str | None) -> str:
    name = Path(filename or "document.bin").name
    return "".join(ch if ch.isalnum() or ch in {".", "-", "_"} else "_" for ch in name)[
        :255
    ]


def _detect_content_type(filename: str, supplied: str | None, content: bytes) -> str:
    guessed = mimetypes.guess_type(filename)[0]
    candidate = supplied if supplied in ALLOWED_SIGNATURES else guessed
    if candidate not in ALLOWED_SIGNATURES or not ALLOWED_SIGNATURES[candidate](
        content
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only valid PDF, PNG, and JPEG documents are accepted",
        )
    return candidate


async def store_uploaded_document(
    db: AsyncSession,
    *,
    tender_id: UUID,
    bid_id: UUID,
    actor_id: UUID,
    upload: UploadFile,
) -> Document:
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await upload.read(max_bytes + 1)
    if not content:
        raise HTTPException(status_code=422, detail="Uploaded document is empty")
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Document exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit",
        )

    filename = _safe_name(upload.filename)
    mime_type = _detect_content_type(filename, upload.content_type, content)
    content_hash = hashlib.sha256(content).hexdigest()
    duplicate = await db.execute(
        select(Document).where(
            Document.bid_id == bid_id, Document.content_hash == content_hash
        )
    )
    if duplicate.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409, detail="This document was already uploaded for the bid"
        )

    document_id = uuid.uuid4()
    object_key = str(
        PurePosixPath("documents")
        / str(tender_id)
        / str(bid_id)
        / f"{document_id}_{filename}"
    )
    storage = get_storage_service(settings.STORAGE_ROOT)
    try:
        await storage.store_bytes(content, object_key, max_bytes)
    except StorageError as exc:
        raise HTTPException(status_code=500, detail="Document storage failed") from exc

    document = Document(
        id=document_id,
        bid_id=bid_id,
        original_filename=filename,
        document_type="UNCLASSIFIED",
        content_hash=content_hash,
        storage_path=object_key,
        processing_status=DocumentProcessingStatus.UPLOADED,
        file_size_bytes=len(content),
        mime_type=mime_type,
    )
    db.add(document)
    await append_audit_event(
        db,
        event_type="DOCUMENT_UPLOADED",
        tender_id=tender_id,
        bid_id=bid_id,
        actor_id=actor_id,
        payload={
            "document_id": str(document_id),
            "filename": filename,
            "sha256": content_hash,
        },
    )
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        try:
            await storage.delete(object_key)
        except StorageError:
            pass
        raise
    await db.refresh(document)
    return document


async def process_document_with_ml(
    db: AsyncSession,
    *,
    document: Document,
    tender_id: UUID,
    actor_id: UUID,
) -> tuple[list[ExtractedFact], float | None, list[str]]:
    storage = get_storage_service(settings.STORAGE_ROOT)
    try:
        content = await storage.read(document.storage_path)
    except StoredObjectNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail="Stored document bytes were not found"
        ) from exc
    except StorageError as exc:
        raise HTTPException(status_code=503, detail="Document storage is unavailable") from exc

    document.processing_status = DocumentProcessingStatus.PROCESSING
    await db.commit()
    warnings: list[str] = []
    try:
        async with httpx.AsyncClient(
            timeout=settings.ML_REQUEST_TIMEOUT_SECONDS
        ) as client:
            headers = {}
            if settings.ML_SHARED_SECRET:
                headers["X-ML-Service-Key"] = settings.ML_SHARED_SECRET
            response = await client.post(
                f"{settings.ML_SERVICE_URL.rstrip('/')}/ml1/process/upload",
                files={
                    "file": (document.original_filename, content, document.mime_type)
                },
                headers=headers,
            )
            response.raise_for_status()
            result = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        document.processing_status = DocumentProcessingStatus.FAILED
        await append_audit_event(
            db,
            event_type="DOCUMENT_PROCESSING_FAILED",
            tender_id=tender_id,
            bid_id=document.bid_id,
            actor_id=actor_id,
            payload={"document_id": str(document.id), "error": type(exc).__name__},
        )
        await db.commit()
        raise HTTPException(
            status_code=502,
            detail="ML document service is unavailable or returned an invalid result",
        ) from exc

    classification = result.get("document_classification") or {}
    document.document_type = classification.get("document_type") or "UNKNOWN"
    classification_confidence = classification.get("confidence")
    await db.execute(
        delete(ExtractedFact).where(ExtractedFact.document_id == document.id)
    )

    facts: list[ExtractedFact] = []
    for raw in result.get("fields") or []:
        value = raw.get("value")
        normalized = raw.get("value_normalized")
        fact = ExtractedFact(
            document_id=document.id,
            field_name=raw.get("field") or "unknown",
            raw_value=json.dumps(value, default=str)
            if isinstance(value, (dict, list))
            else (str(value) if value is not None else None),
            normalized_value=(
                json.dumps(normalized, default=str)
                if isinstance(normalized, (dict, list))
                else (
                    str(normalized)
                    if normalized is not None
                    else (str(value) if value is not None else None)
                )
            ),
            confidence=Decimal(
                str(max(0.0, min(1.0, float(raw.get("confidence") or 0.0))))
            ),
            page_number=raw.get("page"),
            bbox=raw.get("bounding_box"),
            extraction_method=raw.get("extraction_method"),
            evidence_id=raw.get("evidence_id") or f"ev_{uuid.uuid4().hex[:12]}",
            extractor_version="ml1-v1",
        )
        facts.append(fact)
        db.add(fact)

    if (
        classification_confidence is not None
        and float(classification_confidence) < 0.60
    ):
        document.processing_status = DocumentProcessingStatus.REVIEW
        warnings.append(
            "Low-confidence document classification requires officer review"
        )
    else:
        document.processing_status = DocumentProcessingStatus.READY

    await append_audit_event(
        db,
        event_type="DOCUMENT_PROCESSED",
        tender_id=tender_id,
        bid_id=document.bid_id,
        actor_id=actor_id,
        payload={
            "document_id": str(document.id),
            "document_type": document.document_type,
            "fact_count": len(facts),
            "extractor_version": "ml1-v1",
        },
    )
    await db.commit()
    for fact in facts:
        await db.refresh(fact)
    return (
        facts,
        float(classification_confidence)
        if classification_confidence is not None
        else None,
        warnings,
    )


async def list_document_facts(
    db: AsyncSession, document_id: UUID
) -> list[ExtractedFact]:
    result = await db.execute(
        select(ExtractedFact)
        .where(ExtractedFact.document_id == document_id)
        .order_by(ExtractedFact.created_at.asc())
    )
    return list(result.scalars().all())
