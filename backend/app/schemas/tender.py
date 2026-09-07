from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.tender import TenderStatus


class TenderDatesMixin(BaseModel):
    opening_date: datetime | None = None
    closing_date: datetime | None = None

    @model_validator(mode="after")
    def validate_date_range(self):
        if (
            self.opening_date is not None
            and self.closing_date is not None
            and self.closing_date < self.opening_date
        ):
            raise ValueError("closing_date must be on or after opening_date")
        return self


class TenderCreate(TenderDatesMixin):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    reference_number: str = Field(min_length=1, max_length=100)
    status: TenderStatus = TenderStatus.DRAFT
    budget: Decimal | None = Field(default=None, max_digits=15, decimal_places=2)

    model_config = ConfigDict(extra="forbid")


class TenderUpdate(TenderDatesMixin):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    reference_number: str | None = Field(default=None, min_length=1, max_length=100)
    status: TenderStatus | None = None
    budget: Decimal | None = Field(default=None, max_digits=15, decimal_places=2)

    model_config = ConfigDict(extra="forbid")


class TenderResponse(TenderDatesMixin):
    id: UUID
    title: str
    description: str | None
    reference_number: str
    status: TenderStatus
    budget: Decimal | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
