from fastapi import APIRouter, File, UploadFile, HTTPException
from pydantic import BaseModel
from shared.validators import validate_image_path, validate_image_bytes
from .forensics_service import inspect_pdf_forensics, inspect_image_forensics, PIKEPDF_AVAILABLE

router = APIRouter(prefix="/ml2/forensics", tags=["Document Forensics"])


class FilePathRequest(BaseModel):
    file_path: str


@router.post("/process")
def process_file_path(request: FilePathRequest):
    """Evaluates document integrity and forensics from a local filesystem path."""
    validated_path = validate_image_path(request.file_path)
    with open(validated_path, "rb") as f:
        file_bytes = f.read()
    return inspect_pdf_forensics(file_bytes, filename=validated_path.name)


@router.post("/upload")
async def upload_and_inspect(file: UploadFile = File(...)):
    """Evaluates document integrity, metadata anomalies, and digital signatures from an upload stream."""
    file_bytes = await file.read()
    filename = file.filename or "uploaded_document"
    return inspect_pdf_forensics(file_bytes, filename=filename)


@router.get("/health")
def health():
    """Health check reporting forensics module readiness and pikepdf engine status."""
    return {
        "status": "ok" if PIKEPDF_AVAILABLE else "degraded",
        "module": "ml2_forensics",
        "pikepdf_available": PIKEPDF_AVAILABLE,
    }
