"""add evidence model

Revision ID: 005_evidence
Revises: 004_ml_processing_results
Create Date: 2026-09-07 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "005_evidence"
down_revision: Union[str, None] = "004_ml_processing_results"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("evidence_id", sa.String(length=150), nullable=False),
        sa.Column("source_evidence_id", sa.String(length=150), nullable=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "ml_result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ml_processing_results.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(length=150), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("value_normalized", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("bounding_box", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_text", sa.Text(), nullable=True),
        sa.Column("extraction_method", sa.String(length=100), nullable=True),
        sa.Column(
            "evidence_type",
            sa.String(length=50),
            server_default="ML_EXTRACTION",
            nullable=False,
        ),
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
        sa.UniqueConstraint("evidence_id", name="uq_evidence_evidence_id"),
        sa.UniqueConstraint("ml_result_id", "evidence_id", name="uq_evidence_ml_result_evidence_id"),
    )
    op.create_index("ix_evidence_evidence_id", "evidence", ["evidence_id"])
    op.create_index("ix_evidence_source_evidence_id", "evidence", ["source_evidence_id"])
    op.create_index("ix_evidence_document_id", "evidence", ["document_id"])
    op.create_index("ix_evidence_ml_result_id", "evidence", ["ml_result_id"])
    op.create_index("ix_evidence_field_name", "evidence", ["field_name"])


def downgrade() -> None:
    op.drop_index("ix_evidence_field_name", table_name="evidence")
    op.drop_index("ix_evidence_ml_result_id", table_name="evidence")
    op.drop_index("ix_evidence_document_id", table_name="evidence")
    op.drop_index("ix_evidence_source_evidence_id", table_name="evidence")
    op.drop_index("ix_evidence_evidence_id", table_name="evidence")
    op.drop_table("evidence")
