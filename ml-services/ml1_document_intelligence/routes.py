import uuid
from typing import Optional
from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel

from shared.validators import validate_image_path, validate_image_bytes
from .ocr_service import (
    run_ocr,
    run_ocr_from_bytes,
    is_tesseract_available,
    run_ocr_multi,
    extract_word_data_multi,
)
from .classifier import classify_document
from .field_extractors.gst import extract_gst_fields
from .field_extractors.pan import extract_pan_fields
from .field_extractors.udyam import extract_udyam_fields
from .field_extractors.mca import extract_mca_fields
from .field_extractors.bis import extract_bis_fields
from .field_extractors.dpiit import extract_dpiit_fields
from .field_extractors.ca import extract_ca_fields
from .field_extractors.oem import extract_oem_fields
from .field_extractors.mii import extract_mii_fields
from .field_extractors.standing import extract_standing_fields

router = APIRouter(prefix="/ml1", tags=["Document Intelligence"])

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


def _build_pipeline_result(
    ocr_pages: list[str],
    word_data: Optional[list[dict]] = None,
    document_id: Optional[str] = None,
) -> dict:
    """Run classification and extraction on OCR pages, producing a unified schema output."""
    concatenated_ocr = "\n".join(ocr_pages)
    doc_id = document_id or f"doc_{uuid.uuid4().hex[:8]}"

    classification = classify_document(concatenated_ocr)
    doc_type = classification.get("document_type")
    extractor = EXTRACTOR_MAP.get(doc_type)

    raw_fields = extractor(concatenated_ocr) if extractor else []

    unified_fields: list[dict] = []
    for f in raw_fields:
        field_name = f.get("field") or f.get("field_name")
        val = f.get("value") if "value" in f else f.get("field_value")
        conf = f.get("confidence", 0.0)
        unified_fields.append({
            "field": field_name,
            "value": val,
            "confidence": conf,
            "page": f.get("page"),
            "bounding_box": f.get("bounding_box"),
            "value_normalized": f.get("value_normalized"),
            "extraction_method": f.get("extraction_method", "ocr"),
            "source_text": f.get("source_text"),
            "evidence_id": f.get("evidence_id") or f"ev_{uuid.uuid4().hex[:8]}",
            "document_id": doc_id,
        })

    existing_fields = {field["field"] for field in unified_fields if field.get("field")}
    if "address" not in existing_fields:
        unified_fields.append({
            "field": "address",
            "value": None,
            "confidence": 0.0,
            "page": None,
            "bounding_box": None,
            "value_normalized": None,
            "extraction_method": "ocr",
            "source_text": None,
            "evidence_id": f"ev_{uuid.uuid4().hex[:8]}",
            "document_id": doc_id,
        })
    if "company_address" not in existing_fields:
        unified_fields.append({
            "field": "company_address",
            "value": None,
            "confidence": 0.0,
            "page": None,
            "bounding_box": None,
            "value_normalized": None,
            "extraction_method": "ocr",
            "source_text": None,
            "evidence_id": f"ev_{uuid.uuid4().hex[:8]}",
            "document_id": doc_id,
        })

    return {
        "document_classification": classification,
        "fields": unified_fields,
        "ocr_metadata": {
            "character_count": sum(len(p) for p in ocr_pages),
            "word_count": sum(len(p.split()) for p in ocr_pages),
            "concatenated_ocr": concatenated_ocr,
            "pagewise_ocr": ocr_pages,
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
    validate_image_bytes(image_bytes, filename=file.filename)
    ocr_text = run_ocr_from_bytes(image_bytes)
    return classify_document(ocr_text)


@router.post("/process/upload")
async def process_document_upload(file: UploadFile = File(...)):
    """Full pipeline directly from an uploaded binary file stream."""
    image_bytes = await file.read()
    validate_image_bytes(image_bytes, filename=file.filename)
    ocr_text = run_ocr_from_bytes(image_bytes)
    doc_id = f"doc_{file.filename.split('.')[0] if file.filename else uuid.uuid4().hex[:8]}"
    return _build_pipeline_result([ocr_text], word_data=None, document_id=doc_id)


@router.get("/health")
def health():
    """Health check reporting module status and OCR engine readiness."""
    tesseract_ready = is_tesseract_available()
    return {
        "status": "ok" if tesseract_ready else "degraded",
        "module": "ml1",
        "ocr_engine_available": tesseract_ready,
    }
