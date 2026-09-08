from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.requirement import RequirementResponse


class TenderDocumentResponse(BaseModel):
    id: UUID
    tender_id: UUID
    version: int
    original_filename: str
    content_hash: str
    storage_path: str
    file_size_bytes: int
    mime_type: str
    processing_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenderAnalysisResponse(BaseModel):
    tender_document_id: UUID
    processing_status: str
    extracted_character_count: int = Field(ge=0)
    candidates: list[RequirementResponse]
    warnings: list[str] = Field(default_factory=list)
