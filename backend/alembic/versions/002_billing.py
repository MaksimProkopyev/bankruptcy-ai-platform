"""billing: templates, signatures, invoices

Revision ID: 002_billing
Revises: 001_initial
Create Date: 2025-03-25
"""
from typing import Sequence, Union
from alembic import op

revision: str = '002_billing'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Billing tables were merged into 001_initial.
    # Keep this migration as a lightweight compatibility step.
    op.execute("CREATE SEQUENCE IF NOT EXISTS invoice_number_seq START 1001")


def downgrade() -> None:
    op.execute("DROP SEQUENCE IF EXISTS invoice_number_seq")
