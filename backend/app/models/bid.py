import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.bidder import Bidder
    from app.models.document import Document
    from app.models.tender import Tender


class BidStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    QUALIFIED = "QUALIFIED"
    DISQUALIFIED = "DISQUALIFIED"
    WITHDRAWN = "WITHDRAWN"


class Bid(Base):
    __tablename__ = "bids"
    __table_args__ = (
        UniqueConstraint("tender_id", "bidder_id", name="uq_bids_tender_bidder"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bidder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bidders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bid_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    status: Mapped[BidStatus] = mapped_column(
        SQLEnum(BidStatus, name="bid_status", native_enum=True),
        default=BidStatus.SUBMITTED,
        nullable=False,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    tender: Mapped["Tender"] = relationship("Tender", back_populates="bids")
    bidder: Mapped["Bidder"] = relationship("Bidder", back_populates="bids")
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="bid", cascade="all, delete-orphan"
    )
