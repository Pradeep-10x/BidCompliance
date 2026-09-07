from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EvidenceResponse(BaseModel):
    id: UUID
    evidence_id: str
    source_evidence_id: Optional[str] = None
    document_id: UUID
    ml_result_id: UUID
    field_name: str
    value: Optional[str] = None
    value_normalized: Optional[str] = None
    confidence: Optional[float] = None
    page_number: Optional[int] = None
    bounding_box: Optional[Any] = None
    source_text: Optional[str] = None
    extraction_method: Optional[str] = None
    evidence_type: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
