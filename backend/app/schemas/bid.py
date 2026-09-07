from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.bid import BidStatus


class BidCreate(BaseModel):
    bidder_id: UUID
    bid_amount: Decimal | None = Field(
        default=None, max_digits=15, decimal_places=2
    )
    status: BidStatus = BidStatus.SUBMITTED

    model_config = ConfigDict(extra="forbid")


class BidUpdate(BaseModel):
    bidder_id: UUID | None = None
    bid_amount: Decimal | None = Field(
        default=None, max_digits=15, decimal_places=2
    )
    status: BidStatus | None = None

    model_config = ConfigDict(extra="forbid")


class BidResponse(BaseModel):
    id: UUID
    tender_id: UUID
    bidder_id: UUID
    bid_amount: Decimal | None
    status: BidStatus
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
