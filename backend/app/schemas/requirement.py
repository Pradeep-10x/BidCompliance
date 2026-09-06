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

    model_config = ConfigDict(extra="forbid")


class RequirementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    is_mandatory: bool | None = None
    weight: Decimal | None = Field(default=None, max_digits=5, decimal_places=2)
    rule_config: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")


class RequirementResponse(BaseModel):
    id: UUID
    tender_id: UUID
    title: str
    description: str | None
    is_mandatory: bool
    weight: Decimal
    rule_config: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
