from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ComplianceSummaryStatus:
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    INCOMPLETE = "INCOMPLETE"
    ERROR = "ERROR"


class RequirementSummaryItem(BaseModel):
    requirement_id: UUID
    title: str
    is_mandatory: bool
    weight: float
    evaluation_id: Optional[UUID] = None
    status: str  # COMPLIANT, NON_COMPLIANT, MISSING_EVIDENCE, LOW_CONFIDENCE, ERROR, UNEVALUATED
    target_field: Optional[str] = None
    extracted_value: Optional[str] = None
    confidence: Optional[float] = None
    evidence_id: Optional[UUID] = None
    reason: Optional[str] = None
    details: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class BidComplianceSummaryResponse(BaseModel):
    bid_id: UUID
    tender_id: UUID
    total_requirements: int
    evaluated_requirements: int
    unevaluated_requirements: int
    compliant: int
    non_compliant: int
    missing_evidence: int
    low_confidence: int
    error: int
    mandatory_total: int
    mandatory_evaluated: int
    mandatory_compliant: int
    mandatory_non_compliant: int
    summary_status: str
    compliance_ratio: float
    weighted_compliance_ratio: float
    requirements: list[RequirementSummaryItem]

    model_config = ConfigDict(from_attributes=True)
