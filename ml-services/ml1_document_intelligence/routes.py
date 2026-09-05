from typing import Optional
from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel

from shared.validators import validate_image_path, validate_image_bytes
from .ocr_service import run_ocr, run_ocr_from_bytes, is_tesseract_available
from .classifier import classify_document
from .field_extractors.gst import extract_gst_fields
from .field_extractors.pan import extract_pan_fields
from .field_extractors.udyam import extract_udyam_fields
from .field_extractors.mca import extract_mca_fields

router = APIRouter(prefix="/ml1", tags=["Document Intelligence"])

EXTRACTOR_MAP = {
    "gst_registration_certificate": extract_gst_fields,
    "pan_document": extract_pan_fields,
    "udyam_registration_certificate": extract_udyam_fields,
    "mca_incorporation_certificate": extract_mca_fields,
}


class DocumentPathRequest(BaseModel):
    image_path: str


def _build_pipeline_result(ocr_text: str) -> dict:
    """Helper that runs classification and extraction given extracted OCR text."""
    classification = classify_document(ocr_text)
    doc_type = classification.get("document_type")
    extractor = EXTRACTOR_MAP.get(doc_type)

    fields = extractor(ocr_text) if extractor else []

    return {
        "document_classification": classification,
        "fields": fields,
        "ocr_metadata": {
            "character_count": len(ocr_text),
            "word_count": len(ocr_text.split()),
        },
    }


# ==========================================
# 1. JSON Path Endpoints (Local/Batch Usage)
# ==========================================

@router.post("/classify")
def classify(request: DocumentPathRequest):
    """OCR + classification from a validated local filesystem path."""
    validated_path = validate_image_path(request.image_path)
    ocr_text = run_ocr(str(validated_path))
    return classify_document(ocr_text)


@router.post("/process")
def process_document(request: DocumentPathRequest):
    """Full pipeline: Validation -> OCR -> Classification -> Field Extraction from a file path."""
    validated_path = validate_image_path(request.image_path)
    ocr_text = run_ocr(str(validated_path))
    return _build_pipeline_result(ocr_text)


# ==========================================
# 2. File Upload Endpoints (Microservice HTTP)
# ==========================================

@router.post("/classify/upload")
async def classify_upload(file: UploadFile = File(...)):
    """OCR + classification directly from an uploaded binary file stream."""
    image_bytes = await file.read()
    validate_image_bytes(image_bytes, filename=file.filename)
    ocr_text = run_ocr_from_bytes(image_bytes)
    return classify_document(ocr_text)


@router.post("/process/upload")
async def process_document_upload(file: UploadFile = File(...)):
    """Full pipeline directly from an uploaded binary file stream."""
    image_bytes = await file.read()
    validate_image_bytes(image_bytes, filename=file.filename)
    ocr_text = run_ocr_from_bytes(image_bytes)
    return _build_pipeline_result(ocr_text)


# ==========================================
# 3. Health & Readiness Check
# ==========================================

@router.get("/health")
def health():
    """Health check reporting module status and OCR engine readiness."""
    tesseract_ready = is_tesseract_available()
    return {
        "status": "ok" if tesseract_ready else "degraded",
        "module": "ml1",
        "ocr_engine_available": tesseract_ready,
    }