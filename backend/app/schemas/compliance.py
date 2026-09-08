from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    status: str
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


class ExtractedFactResponse(BaseModel):
    id: UUID
    document_id: UUID
    field_name: str
    raw_value: str | None
    normalized_value: str | None
    confidence: Decimal
    page_number: int | None
    bbox: dict[str, Any] | list[Any] | None
    extraction_method: str | None
    evidence_id: str
    extractor_version: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentProcessingResponse(BaseModel):
    document_id: UUID
    processing_status: str
    document_type: str
    classification_confidence: float | None = None
    facts: list[ExtractedFactResponse]
    warnings: list[str] = Field(default_factory=list)


class VerificationRunRequest(BaseModel):
    source: str = Field(min_length=2, max_length=50)
    scenario: Literal["MATCH", "MISMATCH", "NOT_FOUND", "UNAVAILABLE", "EXPIRED"] = (
        "MATCH"
    )
    effective_date: datetime | None = None

    model_config = ConfigDict(extra="forbid")


class VerificationResultResponse(BaseModel):
    id: UUID
    bid_id: UUID
    document_id: UUID | None
    source: str
    mode: str
    request_id: str
    checked_at: datetime
    effective_date: datetime | None
    status: str
    source_record_id: str | None
    fields: dict[str, Any]
    matched_fields: list[Any]
    mismatches: list[Any]
    warnings: list[Any]
    evidence_refs: list[Any]
    adapter_version: str
    confidence: Decimal

    model_config = ConfigDict(from_attributes=True)


class RequirementResultResponse(BaseModel):
    id: UUID
    assessment_id: UUID
    requirement_id: UUID
    status: str
    reason: str
    evidence_refs: list[Any]
    rule_snapshot: dict[str, Any]
    is_mandatory: bool
    weight: Decimal

    model_config = ConfigDict(from_attributes=True)


class FindingResponse(BaseModel):
    id: UUID
    assessment_id: UUID
    requirement_id: UUID | None
    finding_type: str
    severity: str
    title: str
    description: str
    status: str
    evidence_refs: list[Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssessmentResponse(BaseModel):
    id: UUID
    tender_id: UUID
    bid_id: UUID
    version: int
    mandatory_gate_status: str
    compliance_score: Decimal
    verification_depth: Decimal
    evidence_coverage: Decimal
    risk_level: str
    rule_version_set: dict[str, Any]
    generated_at: datetime
    requirement_results: list[RequirementResultResponse] = Field(default_factory=list)
    findings: list[FindingResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class DecisionCreate(BaseModel):
    action: Literal[
        "ACCEPT", "OVERRIDE", "REQUEST_CLARIFICATION", "ESCALATE", "DISQUALIFY"
    ]
    reason: str | None = Field(default=None, max_length=2000)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def require_reason_for_consequential_action(self):
        if self.action in {
            "OVERRIDE",
            "REQUEST_CLARIFICATION",
            "ESCALATE",
            "DISQUALIFY",
        } and (not self.reason or not self.reason.strip()):
            raise ValueError(f"reason is required for {self.action}")
        return self


class DecisionResponse(BaseModel):
    id: UUID
    assessment_id: UUID
    officer_id: UUID
    action: str
    reason: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditEventResponse(BaseModel):
    id: UUID
    tender_id: UUID | None
    bid_id: UUID | None
    actor_id: UUID | None
    event_type: str
    payload: dict[str, Any]
    payload_hash: str
    previous_event_hash: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
