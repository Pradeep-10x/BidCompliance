from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentProcessingStatus


class DocumentUpdate(BaseModel):
    original_filename: str | None = Field(
        default=None, min_length=1, max_length=255
    )
    document_type: str | None = Field(default=None, min_length=1, max_length=100)
    file_size_bytes: int | None = Field(default=None, ge=0)
    mime_type: str | None = Field(default=None, max_length=100)

    model_config = ConfigDict(extra="forbid")


class DocumentResponse(BaseModel):
    id: UUID
    bid_id: UUID
    original_filename: str
    document_type: str
    content_hash: str
    storage_path: str
    processing_status: DocumentProcessingStatus
    file_size_bytes: int | None
    mime_type: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
