from fastapi import APIRouter
from pydantic import BaseModel

from .ocr_service import run_ocr
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


@router.post("/classify")
def classify(request: DocumentPathRequest):
    """OCR + classification only — returns document type and confidence."""
    ocr_text = run_ocr(request.image_path)
    classification = classify_document(ocr_text)
    return classification


@router.post("/process")
def process_document(request: DocumentPathRequest):
    """Full pipeline: OCR -> classify -> extract fields for the detected type."""
    ocr_text = run_ocr(request.image_path)
    classification = classify_document(ocr_text)

    doc_type = classification["document_type"]
    extractor = EXTRACTOR_MAP.get(doc_type)

    fields = extractor(ocr_text) if extractor else []

    return {
        "document_classification": classification,
        "fields": fields
    }


@router.get("/health")
def health():
    return {"status": "ok", "module": "ml1"}