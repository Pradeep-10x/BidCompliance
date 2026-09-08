from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RequirementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    is_mandatory: bool = True
    weight: Decimal = Field(default=Decimal("1.00"), max_digits=5, decimal_places=2)
    rule_config: dict[str, Any] | None = None
    status: str = Field(default="ADDED_MANUALLY", pattern=r"^(CANDIDATE|CONFIRMED|DISABLED|ADDED_MANUALLY)$")
    category: str | None = Field(default=None, max_length=100)
    clause_reference: str | None = None
    source_page: int | None = Field(default=None, ge=1)
    evidence_types: list[str] = Field(default_factory=list)
    verification_sources: list[str] = Field(default_factory=list)
    extraction_confidence: Decimal | None = Field(default=None, ge=0, le=1, max_digits=5, decimal_places=4)

    model_config = ConfigDict(extra="forbid")


class RequirementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    is_mandatory: bool | None = None
    weight: Decimal | None = Field(default=None, max_digits=5, decimal_places=2)
    rule_config: dict[str, Any] | None = None
    status: str | None = Field(default=None, pattern=r"^(CANDIDATE|CONFIRMED|DISABLED|ADDED_MANUALLY)$")
    category: str | None = Field(default=None, max_length=100)
    clause_reference: str | None = None
    source_page: int | None = Field(default=None, ge=1)
    evidence_types: list[str] | None = None
    verification_sources: list[str] | None = None
    extraction_confidence: Decimal | None = Field(default=None, ge=0, le=1, max_digits=5, decimal_places=4)

    model_config = ConfigDict(extra="forbid")


class RequirementResponse(BaseModel):
    id: UUID
    tender_id: UUID
    title: str
    description: str | None
    is_mandatory: bool
    weight: Decimal
    rule_config: dict[str, Any] | None
    status: str
    category: str | None
    clause_reference: str | None
    source_page: int | None
    evidence_types: list[str]
    verification_sources: list[str]
    extraction_confidence: Decimal | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RequirementConfirmRequest(BaseModel):
    requirement_ids: list[UUID] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")
