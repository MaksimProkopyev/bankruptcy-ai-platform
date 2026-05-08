"""lead collector: leads table for external sources

Revision ID: 004_lead_collector
Revises: 003_rag_v2
Create Date: 2026-04-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "004_lead_collector"
down_revision: Union[str, None] = "003_rag_v2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), server_default="new", nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("assigned_lawyer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("qualification_data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("briefing_card", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("external_id", sa.String(100), nullable=True),
        sa.Column("external_data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("debt_amount_estimated", sa.BigInteger(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("contacted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contact_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("deduplicated_from", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assigned_lawyer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["deduplicated_from"], ["leads.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_id", name="uq_leads_source_external_id"),
    )
    op.create_index("idx_leads_status", "leads", ["status"])
    op.create_index("idx_leads_source", "leads", ["source"])
    op.create_index("idx_leads_external_id", "leads", ["external_id"])
    op.create_index("idx_leads_region", "leads", ["region"])
    op.create_index("idx_leads_phone", "leads", ["phone"])
    op.create_index("idx_leads_email", "leads", ["email"])
    op.create_index("idx_leads_deduplicated_from", "leads", ["deduplicated_from"])


def downgrade() -> None:
    op.drop_index("idx_leads_deduplicated_from", table_name="leads")
    op.drop_index("idx_leads_email", table_name="leads")
    op.drop_index("idx_leads_phone", table_name="leads")
    op.drop_index("idx_leads_region", table_name="leads")
    op.drop_index("idx_leads_external_id", table_name="leads")
    op.drop_index("idx_leads_source", table_name="leads")
    op.drop_index("idx_leads_status", table_name="leads")
    op.drop_table("leads")

