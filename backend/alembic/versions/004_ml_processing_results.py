"""add ML processing results

Revision ID: 004_ml_processing_results
Revises: 003_processing_jobs
Create Date: 2026-09-07 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "004_ml_processing_results"
down_revision: Union[str, None] = "003_processing_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ml_processing_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processing_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "bid_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bids.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("module", sa.String(length=150), nullable=False),
        sa.Column("model_name", sa.String(length=150), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("errors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("job_id", name="uq_ml_processing_results_job_id"),
    )
    op.create_index("ix_ml_processing_results_job_id", "ml_processing_results", ["job_id"])
    op.create_index("ix_ml_processing_results_document_id", "ml_processing_results", ["document_id"])
    op.create_index("ix_ml_processing_results_bid_id", "ml_processing_results", ["bid_id"])


def downgrade() -> None:
    op.drop_index("ix_ml_processing_results_bid_id", table_name="ml_processing_results")
    op.drop_index("ix_ml_processing_results_document_id", table_name="ml_processing_results")
    op.drop_index("ix_ml_processing_results_job_id", table_name="ml_processing_results")
    op.drop_table("ml_processing_results")
