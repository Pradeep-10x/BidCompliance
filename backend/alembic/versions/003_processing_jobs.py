"""add processing jobs

Revision ID: 003_processing_jobs
Revises: 002_core_domain
Create Date: 2026-09-07 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "003_processing_jobs"
down_revision: Union[str, None] = "002_core_domain"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    job_status = postgresql.ENUM(
        "PENDING", "QUEUED", "PROCESSING", "COMPLETED", "FAILED",
        name="processing_job_status",
    )
    job_status.create(op.get_bind(), checkfirst=True)
    pipeline_stage = postgresql.ENUM(
        "CLASSIFICATION", "OCR", "EXTRACTION", "FORENSICS", "REASONING",
        name="pipeline_stage",
    )
    pipeline_stage.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "processing_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("job_type", sa.String(length=100), nullable=False),
        sa.Column(
            "pipeline_stage",
            postgresql.ENUM("CLASSIFICATION", "OCR", "EXTRACTION", "FORENSICS", "REASONING", name="pipeline_stage", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM("PENDING", "QUEUED", "PROCESSING", "COMPLETED", "FAILED", name="processing_job_status", create_type=False),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("document_id", "pipeline_stage", name="uq_processing_jobs_document_stage"),
    )
    op.create_index("ix_processing_jobs_document_id", "processing_jobs", ["document_id"])
    op.create_index("ix_processing_jobs_status", "processing_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_processing_jobs_status", table_name="processing_jobs")
    op.drop_index("ix_processing_jobs_document_id", table_name="processing_jobs")
    op.drop_table("processing_jobs")
    postgresql.ENUM(name="pipeline_stage").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="processing_job_status").drop(op.get_bind(), checkfirst=True)
