"""core domain migration

Revision ID: 002_core_domain
Revises: 001_initial_auth
Create Date: 2026-09-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_core_domain'
down_revision: Union[str, None] = '001_initial_auth'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Enum Types
    tender_status_enum = postgresql.ENUM(
        'DRAFT', 'PUBLISHED', 'CLOSED', 'EVALUATING', 'AWARDED', 'CANCELLED',
        name='tender_status'
    )
    tender_status_enum.create(op.get_bind(), checkfirst=True)

    bid_status_enum = postgresql.ENUM(
        'SUBMITTED', 'UNDER_REVIEW', 'QUALIFIED', 'DISQUALIFIED', 'WITHDRAWN',
        name='bid_status'
    )
    bid_status_enum.create(op.get_bind(), checkfirst=True)

    doc_status_enum = postgresql.ENUM(
        'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED',
        name='document_processing_status'
    )
    doc_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create tenders table
    op.create_table(
        'tenders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('reference_number', sa.String(length=100), nullable=False),
        sa.Column(
            'status',
            postgresql.ENUM('DRAFT', 'PUBLISHED', 'CLOSED', 'EVALUATING', 'AWARDED', 'CANCELLED', name='tender_status', create_type=False),
            nullable=False,
            server_default='DRAFT',
        ),
        sa.Column('budget', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('opening_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closing_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_tenders_reference_number'), 'tenders', ['reference_number'], unique=True)

    # 3. Create requirements table
    op.create_table(
        'requirements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tender_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_mandatory', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('weight', sa.Numeric(precision=5, scale=2), nullable=False, server_default='1.00'),
        sa.Column('rule_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_requirements_tender_id'), 'requirements', ['tender_id'], unique=False)

    # 4. Create bidders table
    op.create_table(
        'bidders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('legal_name', sa.String(length=255), nullable=False),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('contact_phone', sa.String(length=50), nullable=True),
        sa.Column('identifiers', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_bidders_contact_email'), 'bidders', ['contact_email'], unique=False)

    # 5. Create bids table
    op.create_table(
        'bids',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tender_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bidder_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('bidders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bid_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column(
            'status',
            postgresql.ENUM('SUBMITTED', 'UNDER_REVIEW', 'QUALIFIED', 'DISQUALIFIED', 'WITHDRAWN', name='bid_status', create_type=False),
            nullable=False,
            server_default='SUBMITTED',
        ),
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_bids_tender_id'), 'bids', ['tender_id'], unique=False)
    op.create_index(op.f('ix_bids_bidder_id'), 'bids', ['bidder_id'], unique=False)
    op.create_unique_constraint('uq_bids_tender_bidder', 'bids', ['tender_id', 'bidder_id'])

    # 6. Create documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('bid_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('bids.id', ondelete='CASCADE'), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('document_type', sa.String(length=100), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('storage_path', sa.String(length=512), nullable=False),
        sa.Column(
            'processing_status',
            postgresql.ENUM('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='document_processing_status', create_type=False),
            nullable=False,
            server_default='PENDING',
        ),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_documents_bid_id'), 'documents', ['bid_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_documents_bid_id'), table_name='documents')
    op.drop_table('documents')

    op.drop_constraint('uq_bids_tender_bidder', 'bids', type_='unique')
    op.drop_index(op.f('ix_bids_bidder_id'), table_name='bids')
    op.drop_index(op.f('ix_bids_tender_id'), table_name='bids')
    op.drop_table('bids')

    op.drop_index(op.f('ix_bidders_contact_email'), table_name='bidders')
    op.drop_table('bidders')

    op.drop_index(op.f('ix_requirements_tender_id'), table_name='requirements')
    op.drop_table('requirements')

    op.drop_index(op.f('ix_tenders_reference_number'), table_name='tenders')
    op.drop_table('tenders')

    doc_status_enum = postgresql.ENUM('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='document_processing_status')
    doc_status_enum.drop(op.get_bind(), checkfirst=True)

    bid_status_enum = postgresql.ENUM('SUBMITTED', 'UNDER_REVIEW', 'QUALIFIED', 'DISQUALIFIED', 'WITHDRAWN', name='bid_status')
    bid_status_enum.drop(op.get_bind(), checkfirst=True)

    tender_status_enum = postgresql.ENUM('DRAFT', 'PUBLISHED', 'CLOSED', 'EVALUATING', 'AWARDED', 'CANCELLED', name='tender_status')
    tender_status_enum.drop(op.get_bind(), checkfirst=True)
