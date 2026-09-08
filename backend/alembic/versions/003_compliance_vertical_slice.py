"""compliance vertical slice

Revision ID: 003_compliance_vertical_slice
Revises: 002_core_domain
Create Date: 2026-09-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003_compliance_vertical_slice"
down_revision: Union[str, None] = "002_core_domain"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for value in ("UPLOADED", "QUEUED", "OCR", "EXTRACTING", "READY", "REVIEW"):
        op.execute(f"ALTER TYPE document_processing_status ADD VALUE IF NOT EXISTS '{value}'")

    op.create_table(
        "extracted_facts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_name", sa.String(150), nullable=False),
        sa.Column("raw_value", sa.Text(), nullable=True),
        sa.Column("normalized_value", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("bbox", postgresql.JSONB(), nullable=True),
        sa.Column("extraction_method", sa.String(100), nullable=True),
        sa.Column("evidence_id", sa.String(100), nullable=False),
        sa.Column("extractor_version", sa.String(100), nullable=False, server_default="ml1-current"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_extracted_facts_document_id", "extracted_facts", ["document_id"])
    op.create_index("ix_extracted_facts_field_name", "extracted_facts", ["field_name"])
    op.create_index("ix_extracted_facts_evidence_id", "extracted_facts", ["evidence_id"])

    op.create_table(
        "verification_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bid_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bids.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("mode", sa.String(50), nullable=False),
        sa.Column("request_id", sa.String(100), nullable=False, unique=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("effective_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("source_record_id", sa.String(255), nullable=True),
        sa.Column("fields", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("matched_fields", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("mismatches", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("warnings", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("evidence_refs", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("adapter_version", sa.String(100), nullable=False, server_default="mock-v1"),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="0"),
    )
    op.create_index("ix_verification_results_bid_id", "verification_results", ["bid_id"])
    op.create_index("ix_verification_results_source", "verification_results", ["source"])
    op.create_index("ix_verification_results_status", "verification_results", ["status"])

    op.create_table(
        "assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tender_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bid_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bids.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("mandatory_gate_status", sa.String(30), nullable=False),
        sa.Column("compliance_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("verification_depth", sa.Numeric(5, 2), nullable=False),
        sa.Column("evidence_coverage", sa.Numeric(5, 2), nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("rule_version_set", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("bid_id", "version", name="uq_assessments_bid_version"),
    )
    op.create_index("ix_assessments_tender_id", "assessments", ["tender_id"])
    op.create_index("ix_assessments_bid_id", "assessments", ["bid_id"])

    op.create_table(
        "requirement_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requirement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_refs", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("rule_snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False),
        sa.Column("weight", sa.Numeric(5, 2), nullable=False),
        sa.UniqueConstraint("assessment_id", "requirement_id", name="uq_requirement_results_assessment_requirement"),
    )
    op.create_index("ix_requirement_results_assessment_id", "requirement_results", ["assessment_id"])
    op.create_index("ix_requirement_results_requirement_id", "requirement_results", ["requirement_id"])

    op.create_table(
        "findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requirement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("requirements.id", ondelete="SET NULL"), nullable=True),
        sa.Column("finding_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("evidence_refs", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_findings_assessment_id", "findings", ["assessment_id"])

    op.create_table(
        "decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("officer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_decisions_assessment_id", "decisions", ["assessment_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tender_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("bid_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bids.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("previous_event_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_events_tender_id", "audit_events", ["tender_id"])
    op.create_index("ix_audit_events_bid_id", "audit_events", ["bid_id"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("decisions")
    op.drop_table("findings")
    op.drop_table("requirement_results")
    op.drop_table("assessments")
    op.drop_table("verification_results")
    op.drop_table("extracted_facts")
    # PostgreSQL enum values are intentionally retained; removing enum values safely
    # requires recreating the type and is not necessary for data-safe rollback.
