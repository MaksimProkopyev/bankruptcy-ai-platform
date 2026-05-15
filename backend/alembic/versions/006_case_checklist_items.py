"""Add case_checklist_items table and document_type to documents

Revision ID: 006_case_checklist_items
Revises: 005_prospects
Create Date: 2026-04-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "006_case_checklist_items"
down_revision: Union[str, None] = "005_prospects"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add document_type column to documents table if it doesn't already exist,
    # then ensure it is nullable (migration 001 created it as NOT NULL).
    op.execute(
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS document_type VARCHAR(50)"
    )
    op.execute(
        "ALTER TABLE documents ALTER COLUMN document_type DROP NOT NULL"
    )

    # Create case_checklist_items table
    op.create_table(
        "case_checklist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checklist_id", sa.String(50), nullable=False),
        sa.Column("checklist_item_id", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'missing'"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("matched_by", sa.String(20), server_default=sa.text("'manual'"), nullable=True),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("case_id", "checklist_id", "checklist_item_id", name="uq_case_checklist_item"),
    )

    # Create indexes
    op.create_index("idx_checklist_items_case", "case_checklist_items", ["case_id"])
    op.create_index("idx_checklist_items_status", "case_checklist_items", ["case_id", "status"])
    op.create_index(
        "idx_checklist_items_document",
        "case_checklist_items",
        ["document_id"],
        postgresql_where=sa.text("document_id IS NOT NULL")
    )
    op.create_index(
        "idx_checklist_items_reviewer",
        "case_checklist_items",
        ["reviewer_id"],
        postgresql_where=sa.text("reviewer_id IS NOT NULL")
    )

    # Create indexes for documents table
    op.create_index(
        "idx_documents_type",
        "documents",
        ["document_type"],
        postgresql_where=sa.text("document_type IS NOT NULL")
    )
    op.create_index("idx_documents_case_type", "documents", ["case_id", "document_type"])


def downgrade() -> None:
    # Drop indexes for documents table
    op.drop_index("idx_documents_case_type", table_name="documents")
    op.drop_index("idx_documents_type", table_name="documents")

    # Drop indexes for case_checklist_items table
    op.drop_index("idx_checklist_items_reviewer", table_name="case_checklist_items")
    op.drop_index("idx_checklist_items_document", table_name="case_checklist_items")
    op.drop_index("idx_checklist_items_status", table_name="case_checklist_items")
    op.drop_index("idx_checklist_items_case", table_name="case_checklist_items")

    # Drop case_checklist_items table
    op.drop_table("case_checklist_items")

    # Drop document_type column from documents table
    op.drop_column("documents", "document_type")