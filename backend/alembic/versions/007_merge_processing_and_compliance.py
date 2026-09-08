"""merge queued-processing and SIH compliance migration branches

Revision ID: 007_merge_processing_compliance
Revises: 006_requirement_evaluations, 004_tender_intelligence
Create Date: 2026-09-08
"""

from typing import Sequence, Union


revision: str = "007_merge_processing_compliance"
down_revision: Union[str, tuple[str, str]] = (
    "006_requirement_evaluations",
    "004_tender_intelligence",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Join the two independently developed migration histories."""


def downgrade() -> None:
    """Splitting the history requires no schema operation."""
