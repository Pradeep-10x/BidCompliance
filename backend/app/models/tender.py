import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum as SQLEnum, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.bid import Bid
    from app.models.requirement import Requirement


class TenderStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CLOSED = "CLOSED"
    EVALUATING = "EVALUATING"
    AWARDED = "AWARDED"
    CANCELLED = "CANCELLED"


class Tender(Base):
    __tablename__ = "tenders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reference_number: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    status: Mapped[TenderStatus] = mapped_column(
        SQLEnum(TenderStatus, name="tender_status", native_enum=True),
        default=TenderStatus.DRAFT,
        nullable=False,
    )
    budget: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    opening_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closing_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
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

    requirements: Mapped[list["Requirement"]] = relationship(
        "Requirement", back_populates="tender", cascade="all, delete-orphan"
    )
    bids: Mapped[list["Bid"]] = relationship(
        "Bid", back_populates="tender", cascade="all, delete-orphan"
    )
