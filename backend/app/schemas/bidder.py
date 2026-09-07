from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BidderCreate(BaseModel):
    legal_name: str = Field(min_length=1, max_length=255)
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=50)
    identifiers: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")


class BidderUpdate(BaseModel):
    legal_name: str | None = Field(default=None, min_length=1, max_length=255)
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=50)
    identifiers: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")


class BidderResponse(BaseModel):
    id: UUID
    legal_name: str
    contact_email: str | None
    contact_phone: str | None
    identifiers: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
