"""add requirement evaluations

Revision ID: 006_requirement_evaluations
Revises: 005_evidence
Create Date: 2026-09-07 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "006_requirement_evaluations"
down_revision: Union[str, None] = "005_evidence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "requirement_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tender_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "bid_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bids.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requirement_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("requirements.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "evidence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evidence.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False),
        sa.Column("target_field", sa.String(length=150), nullable=True),
        sa.Column("extracted_value", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "bid_id", "requirement_id", name="uq_requirement_evaluations_bid_req"
        ),
    )
    op.create_index("ix_requirement_evaluations_tender_id", "requirement_evaluations", ["tender_id"])
    op.create_index("ix_requirement_evaluations_bid_id", "requirement_evaluations", ["bid_id"])
    op.create_index("ix_requirement_evaluations_requirement_id", "requirement_evaluations", ["requirement_id"])
    op.create_index("ix_requirement_evaluations_evidence_id", "requirement_evaluations", ["evidence_id"])
    op.create_index("ix_requirement_evaluations_status", "requirement_evaluations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_requirement_evaluations_status", table_name="requirement_evaluations")
    op.drop_index("ix_requirement_evaluations_evidence_id", table_name="requirement_evaluations")
    op.drop_index("ix_requirement_evaluations_requirement_id", table_name="requirement_evaluations")
    op.drop_index("ix_requirement_evaluations_bid_id", table_name="requirement_evaluations")
    op.drop_index("ix_requirement_evaluations_tender_id", table_name="requirement_evaluations")
    op.drop_table("requirement_evaluations")
