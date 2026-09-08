import hashlib
import io
import mimetypes
import uuid
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.requirement import Requirement
from app.models.tender_document import TenderDocument
from app.services.audit_service import append_audit_event

REQUIREMENT_PATTERNS = (
    {
        "category": "MSME_REGISTRATION",
        "title": "Udyam/MSME registration",
        "keywords": ("udyam", "msme", "micro or small", "micro and small"),
        "evidence_types": ["udyam_registration_certificate"],
        "sources": ["UDYAM"],
        "rule": {
            "kind": "verification_status",
            "source": "UDYAM",
            "allowed_statuses": ["VERIFIED"],
            "on_unavailable": "REVIEW",
        },
    },
    {
        "category": "GST_REGISTRATION",
        "title": "GST registration/status",
        "keywords": ("gstin", "gst registration", "goods and services tax"),
        "evidence_types": ["gst_registration_certificate"],
        "sources": ["GST"],
        "rule": {
            "kind": "verification_status",
            "source": "GST",
            "allowed_statuses": ["VERIFIED"],
            "on_unavailable": "REVIEW",
        },
    },
    {
        "category": "COMPANY_IDENTITY",
        "title": "Company identity and incorporation",
        "keywords": ("cin", "certificate of incorporation", "mca"),
        "evidence_types": ["mca_incorporation_certificate"],
        "sources": ["MCA"],
        "rule": {
            "kind": "verification_status",
            "source": "MCA",
            "allowed_statuses": ["VERIFIED"],
            "on_unavailable": "REVIEW",
        },
    },
    {
        "category": "BIS_CERTIFICATION",
        "title": "BIS product certification",
        "keywords": ("bis licence", "bis license", "bureau of indian standards"),
        "evidence_types": ["bis_certificate_or_licence"],
        "sources": ["BIS"],
        "rule": {
            "kind": "verification_status",
            "source": "BIS",
            "allowed_statuses": ["VERIFIED"],
            "on_unavailable": "REVIEW",
        },
    },
    {
        "category": "OEM_AUTHORIZATION",
        "title": "OEM authorization",
        "keywords": (
            "oem authorization",
            "original equipment manufacturer authorization",
        ),
        "evidence_types": ["oem_authorization_certificate"],
        "sources": ["OEM"],
        "rule": {
            "kind": "evidence_present",
            "document_type": "oem_authorization_certificate",
            "on_missing": "FAIL",
        },
    },
    {
        "category": "LOCAL_CONTENT",
        "title": "Make in India/local content",
        "keywords": ("local content", "make in india", "ppp-mii"),
        "evidence_types": ["make_in_india_declaration"],
        "sources": ["DOCUMENT_ONLY"],
        "rule": {
            "kind": "field_present",
            "field": "local_content_percentage",
            "on_missing": "REVIEW",
        },
    },
    {
        "category": "DEBARMENT",
        "title": "Non-blacklisting/debarment",
        "keywords": ("debarment", "blacklisting", "blacklisted"),
        "evidence_types": ["debarment_declaration"],
        "sources": ["DEBARMENT"],
        "rule": {
            "kind": "verification_status",
            "source": "DEBARMENT",
            "allowed_statuses": ["VERIFIED"],
            "on_unavailable": "REVIEW",
        },
    },
    {
        "category": "FINANCIAL_TURNOVER",
        "title": "Financial turnover",
        "keywords": ("annual turnover", "average turnover", "turnover certificate"),
        "evidence_types": ["ca_turnover_certificate"],
        "sources": ["DOCUMENT_ONLY"],
        "rule": {
            "kind": "field_present",
            "field": "annual_turnover",
            "on_missing": "REVIEW",
        },
    },
)


def _safe_name(filename: str | None) -> str:
    name = Path(filename or "tender.pdf").name
    return "".join(ch if ch.isalnum() or ch in {".", "-", "_"} else "_" for ch in name)[
        :255
    ]


async def store_tender_document(
    db: AsyncSession,
    *,
    tender_id: UUID,
    actor_id: UUID,
    upload: UploadFile,
) -> TenderDocument:
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await upload.read(max_bytes + 1)
    if not content:
        raise HTTPException(status_code=422, detail="Uploaded tender is empty")
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Tender exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit",
        )
    filename = _safe_name(upload.filename)
    mime_type = upload.content_type or mimetypes.guess_type(filename)[0]
    if mime_type != "application/pdf" or not content.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="A valid PDF tender is required",
        )

    version_result = await db.execute(
        select(func.coalesce(func.max(TenderDocument.version), 0)).where(
            TenderDocument.tender_id == tender_id
        )
    )
    version = int(version_result.scalar_one()) + 1
    document_id = uuid.uuid4()
    relative_path = (
        Path("tenders") / str(tender_id) / f"v{version}_{document_id}_{filename}"
    )
    target = (Path(settings.STORAGE_ROOT) / relative_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)

    document = TenderDocument(
        id=document_id,
        tender_id=tender_id,
        version=version,
        original_filename=filename,
        content_hash=hashlib.sha256(content).hexdigest(),
        storage_path=str(relative_path),
        file_size_bytes=len(content),
        mime_type="application/pdf",
        processing_status="UPLOADED",
    )
    db.add(document)
    await append_audit_event(
        db,
        event_type="TENDER_DOCUMENT_UPLOADED",
        tender_id=tender_id,
        actor_id=actor_id,
        payload={
            "tender_document_id": str(document.id),
            "version": version,
            "sha256": document.content_hash,
        },
    )
    await db.commit()
    await db.refresh(document)
    return document


async def list_tender_documents(
    db: AsyncSession, tender_id: UUID
) -> list[TenderDocument]:
    result = await db.execute(
        select(TenderDocument)
        .where(TenderDocument.tender_id == tender_id)
        .order_by(TenderDocument.version.desc())
    )
    return list(result.scalars().all())


async def analyze_latest_tender(
    db: AsyncSession, *, tender_id: UUID, actor_id: UUID
) -> tuple[TenderDocument, list[Requirement], list[str]]:
    result = await db.execute(
        select(TenderDocument)
        .where(TenderDocument.tender_id == tender_id)
        .order_by(TenderDocument.version.desc())
        .limit(1)
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(
            status_code=422, detail="Upload a tender PDF before analysis"
        )

    path = (Path(settings.STORAGE_ROOT) / document.storage_path).resolve()
    if not path.exists():
        raise HTTPException(
            status_code=404, detail="Stored tender bytes were not found"
        )
    try:
        reader = PdfReader(io.BytesIO(path.read_bytes()))
        page_texts = [(page.extract_text() or "").strip() for page in reader.pages]
    except Exception as exc:
        document.processing_status = "FAILED"
        await db.commit()
        raise HTTPException(
            status_code=422, detail="Tender PDF could not be parsed"
        ) from exc

    document.extracted_text = "\n\f\n".join(page_texts)
    existing_result = await db.execute(
        select(Requirement.category).where(Requirement.tender_id == tender_id)
    )
    existing_categories = {value for value in existing_result.scalars().all() if value}
    candidates: list[Requirement] = []
    for definition in REQUIREMENT_PATTERNS:
        if definition["category"] in existing_categories:
            continue
        match_page = None
        match_clause = None
        for page_number, page_text in enumerate(page_texts, start=1):
            for line in (
                line.strip() for line in page_text.splitlines() if line.strip()
            ):
                if any(keyword in line.lower() for keyword in definition["keywords"]):
                    match_page = page_number
                    match_clause = line[:2000]
                    break
            if match_clause:
                break
        if not match_clause:
            continue
        candidate = Requirement(
            tender_id=tender_id,
            title=definition["title"],
            description=f"Candidate extracted from tender page {match_page}",
            status="CANDIDATE",
            category=definition["category"],
            clause_reference=match_clause,
            source_page=match_page,
            evidence_types=definition["evidence_types"],
            verification_sources=definition["sources"],
            extraction_confidence=Decimal("0.8500"),
            is_mandatory=any(
                token in match_clause.lower()
                for token in ("shall", "must", "mandatory", "required")
            ),
            weight=Decimal("1.00"),
            rule_config=definition["rule"],
        )
        db.add(candidate)
        candidates.append(candidate)

    document.processing_status = "RULE_REVIEW" if candidates else "REVIEW"
    warnings = (
        []
        if any(page_texts)
        else ["The PDF has no extractable text; scanned tender OCR is still required"]
    )
    if page_texts and not candidates:
        warnings.append("No supported demo requirement patterns were found")
    await append_audit_event(
        db,
        event_type="TENDER_REQUIREMENTS_ANALYZED",
        tender_id=tender_id,
        actor_id=actor_id,
        payload={
            "tender_document_id": str(document.id),
            "candidate_count": len(candidates),
            "analyzer_version": "deterministic-demo-v1",
        },
    )
    await db.commit()
    for candidate in candidates:
        await db.refresh(candidate)
    return document, candidates, warnings
