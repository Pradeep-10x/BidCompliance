from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EvaluationStatus:
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    ERROR = "ERROR"


@dataclass
class EvaluationResult:
    status: str
    requirement_id: UUID
    target_field: Optional[str]
    extracted_value: Optional[str]
    confidence: Optional[float]
    evidence_id: Optional[UUID]
    reason: str
    details: dict[str, Any] = field(default_factory=dict)


class RequirementEvaluationResponse(BaseModel):
    id: UUID
    tender_id: UUID
    bid_id: UUID
    requirement_id: UUID
    evidence_id: Optional[UUID] = None
    status: str
    is_mandatory: bool
    target_field: Optional[str] = None
    extracted_value: Optional[str] = None
    confidence: Optional[float] = None
    reason: str
    details: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
