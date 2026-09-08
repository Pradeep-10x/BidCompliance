"""tender document and candidate requirement support

Revision ID: 004_tender_intelligence
Revises: 003_compliance_vertical_slice
Create Date: 2026-09-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "004_tender_intelligence"
down_revision: Union[str, None] = "003_compliance_vertical_slice"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("requirements", sa.Column("status", sa.String(30), nullable=False, server_default="ADDED_MANUALLY"))
    op.add_column("requirements", sa.Column("category", sa.String(100), nullable=True))
    op.add_column("requirements", sa.Column("clause_reference", sa.Text(), nullable=True))
    op.add_column("requirements", sa.Column("source_page", sa.Integer(), nullable=True))
    op.add_column("requirements", sa.Column("evidence_types", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("requirements", sa.Column("verification_sources", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("requirements", sa.Column("extraction_confidence", sa.Numeric(5, 4), nullable=True))
    op.create_index("ix_requirements_status", "requirements", ["status"])

    op.create_table(
        "tender_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tender_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("storage_path", sa.String(512), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("processing_status", sa.String(30), nullable=False, server_default="UPLOADED"),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tender_id", "version", name="uq_tender_documents_tender_version"),
    )
    op.create_index("ix_tender_documents_tender_id", "tender_documents", ["tender_id"])


def downgrade() -> None:
    op.drop_table("tender_documents")
    op.drop_index("ix_requirements_status", table_name="requirements")
    op.drop_column("requirements", "extraction_confidence")
    op.drop_column("requirements", "verification_sources")
    op.drop_column("requirements", "evidence_types")
    op.drop_column("requirements", "source_page")
    op.drop_column("requirements", "clause_reference")
    op.drop_column("requirements", "category")
    op.drop_column("requirements", "status")
