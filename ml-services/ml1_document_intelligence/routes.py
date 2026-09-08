import uuid
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel
from shared.validators import validate_image_bytes, validate_image_path

from .classifier import classify_document
from .field_extractors.bis import extract_bis_fields
from .field_extractors.ca import extract_ca_fields
from .field_extractors.dpiit import extract_dpiit_fields
from .field_extractors.gst import extract_gst_fields
from .field_extractors.mca import extract_mca_fields
from .field_extractors.mii import extract_mii_fields
from .field_extractors.oem import extract_oem_fields
from .field_extractors.pan import extract_pan_fields
from .field_extractors.standing import extract_standing_fields
from .field_extractors.udyam import extract_udyam_fields
from .ocr_service import (
    extract_from_digital_pdf_bytes,
    extract_word_data_multi,
    find_phrase_box,
    is_tesseract_available,
    run_ocr_from_bytes,
    run_ocr_multi,
)

router = APIRouter(prefix="/ml1", tags=["Document Intelligence"])

# Current extractor version — increment when extraction logic changes
EXTRACTOR_VERSION = "1.0.0"

EXTRACTOR_MAP = {
    "gst_registration_certificate": extract_gst_fields,
    "pan_document": extract_pan_fields,
    "udyam_registration_certificate": extract_udyam_fields,
    "udyam_msme_registration_certificate": extract_udyam_fields,
    "mca_incorporation_certificate": extract_mca_fields,
    "mca_incorporation_or_company_document": extract_mca_fields,
    "bis_certificate_or_licence": extract_bis_fields,
    "dpiit_startup_recognition_certificate": extract_dpiit_fields,
    "ca_turnover_certificate": extract_ca_fields,
    "oem_authorization_certificate": extract_oem_fields,
    "make_in_india_declaration": extract_mii_fields,
    "bidder_legal_financial_standing": extract_standing_fields,
}


class DocumentPathRequest(BaseModel):
    image_path: str


class DocumentIntelligenceRequest(BaseModel):
    job_id: UUID
    bid_id: UUID
    document_id: UUID
    page_id: UUID | None
    page_number: int
    file_type: str
    image_path: str
    document_hash: str
    callback_url: str | None
    pipeline_stage: str


def _extract_uploaded_pages(content: bytes, filename: str | None) -> list[str]:
    """Extract page text from a digital PDF or OCR an image/scanned PDF."""
    validate_image_bytes(content, filename=filename)
    if content.startswith(b"%PDF-"):
        digital_result = extract_from_digital_pdf_bytes(content)
        if digital_result:
            return digital_result["page_texts"]
    return [run_ocr_from_bytes(content)]


def _resolve_queued_document_path(image_path: str) -> Path:
    root = Path(os.getenv("ML_DOCUMENT_ROOT", ".")).resolve()
    candidate = Path(image_path)
    target = (
        candidate.resolve()
        if candidate.is_absolute()
        else (root / candidate).resolve()
    )
    if root != target and root not in target.parents:
        raise ValueError("Document path escapes ML_DOCUMENT_ROOT")
    return validate_image_path(str(target))


def _build_pipeline_result(
    ocr_pages: list[str],
    word_data: Optional[list[dict]] = None,
    document_id: Optional[str] = None,
) -> dict:
    """Run classification and extraction on OCR pages.

    Produces PRD §5.2 aligned ExtractedFact schema with:
        - field, raw_value, normalized_value, confidence
        - page_number, bbox (wired from word_data via find_phrase_box)
        - extraction_method, extractor_version, evidence_id, document_id
    """
    concatenated_ocr = "\n".join(ocr_pages)
    doc_id = document_id or f"doc_{uuid.uuid4().hex[:8]}"

    classification = classify_document(concatenated_ocr)
    doc_type = classification.get("document_type")
    extractor = EXTRACTOR_MAP.get(doc_type)

    raw_fields = extractor(concatenated_ocr) if extractor else []

    # Build PRD-aligned ExtractedFact list
    unified_fields: list[dict] = []
    for f in raw_fields:
        # Handle both old (field_name/field_value) and new (field/value) schemas
        field_name = f.get("field") or f.get("field_name")
        raw_val = f.get("value") if "value" in f else f.get("field_value")
        conf = f.get("confidence", 0.0)
        method = f.get("extraction_method", "unknown")

        # Wire bounding box provenance from word_data
        bbox_info = None
        page_number = f.get("page")
        if word_data and raw_val and isinstance(raw_val, str) and len(raw_val) > 2:
            phrase_result = find_phrase_box(word_data, raw_val)
            if phrase_result:
                bbox_info = phrase_result["bbox"]
                page_number = phrase_result["page"]

        normalized_value = f.get("value_normalized") or raw_val
        evidence_id = f.get("evidence_id") or f"ev_{uuid.uuid4().hex[:8]}"
        unified_fields.append(
            {
                "field": field_name,
                # Keep both canonical PRD names and compatibility aliases while
                # the queued and synchronous prototype consumers coexist.
                "value": raw_val,
                "raw_value": raw_val,
                "confidence": conf,
                "page": page_number,
                "page_number": page_number,
                "bounding_box": bbox_info,
                "bbox": bbox_info,
                "value_normalized": normalized_value,
                "normalized_value": normalized_value,
                "extraction_method": method,
                "source_text": f.get("source_text"),
                "extractor_version": EXTRACTOR_VERSION,
                "evidence_id": evidence_id,
                "document_id": doc_id,
            }
        )
    return {
        "document_id": doc_id,
        "document_classification": classification,
        "fields": unified_fields,
        "extractor_version": EXTRACTOR_VERSION,
        "ocr_metadata": {
            "page_count": len(ocr_pages),
            "character_count": sum(len(p) for p in ocr_pages),
            "word_count": sum(len(p.split()) for p in ocr_pages),
            "word_data_available": word_data is not None and len(word_data) > 0,
        },
    }


@router.post("/classify")
def classify(request: DocumentPathRequest):
    """OCR + classification from a validated local filesystem path."""
    validated_path = validate_image_path(request.image_path)
    ocr_pages = run_ocr_multi(str(validated_path))
    concatenated_ocr = "\n".join(ocr_pages)
    return classify_document(concatenated_ocr)


@router.post("/process")
def process_document(request: DocumentPathRequest):
    """Full pipeline: Validation -> OCR -> Classification -> Field Extraction from a file path."""
    validated_path = validate_image_path(request.image_path)
    ocr_pages = run_ocr_multi(str(validated_path))
    word_data = extract_word_data_multi(str(validated_path))
    doc_id = f"doc_{validated_path.stem}"
    return _build_pipeline_result(ocr_pages, word_data=word_data, document_id=doc_id)


@router.post("/classify/upload")
async def classify_upload(file: UploadFile = File(...)):
    """OCR + classification directly from an uploaded binary file stream."""
    image_bytes = await file.read()
    pages = _extract_uploaded_pages(image_bytes, file.filename)
    return classify_document("\n".join(pages))


@router.post("/process/upload")
async def process_document_upload(file: UploadFile = File(...)):
    """Full pipeline directly from an uploaded binary file stream."""
    image_bytes = await file.read()
    pages = _extract_uploaded_pages(image_bytes, file.filename)
    doc_id = (
        f"doc_{file.filename.split('.')[0] if file.filename else uuid.uuid4().hex[:8]}"
    )
    return _build_pipeline_result(pages, word_data=None, document_id=doc_id)


@router.post("/document-intelligence")
def document_intelligence(request: DocumentIntelligenceRequest):
    """Process the identity-bound job envelope used by the Celery worker."""
    started = time.perf_counter()
    path = _resolve_queued_document_path(request.image_path)
    pages = run_ocr_multi(str(path))
    word_data = extract_word_data_multi(str(path))
    result = _build_pipeline_result(
        pages,
        word_data=word_data,
        document_id=str(request.document_id),
    )
    return {
        "job_id": request.job_id,
        "bid_id": request.bid_id,
        "document_id": request.document_id,
        "page_id": request.page_id,
        "page_number": request.page_number,
        "module": "ml1_document_intelligence",
        "model_name": "tesseract_rule_pipeline",
        "model_version": EXTRACTOR_VERSION,
        "status": "success",
        "processing_time_ms": int((time.perf_counter() - started) * 1000),
        "result": result,
        "errors": [],
        "created_at": datetime.now(timezone.utc),
    }


@router.get("/health")
def health():
    """Health check reporting module status and OCR engine readiness."""
    tesseract_ready = is_tesseract_available()
    return {
        "status": "ok" if tesseract_ready else "degraded",
        "module": "ml1",
        "ocr_engine_available": tesseract_ready,
    }
