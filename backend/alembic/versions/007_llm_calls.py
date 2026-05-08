"""Add llm_calls table for LLM usage tracking

Revision ID: 007_llm_calls
Revises: 006_case_checklist_items
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision = "007_llm_calls"
down_revision = "006_case_checklist_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create llm_calls table
    op.create_table(
        "llm_calls",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("model", sa.String(80), nullable=False),
        sa.Column("task_type", sa.String(50), nullable=False),
        sa.Column("caller_service", sa.String(30), nullable=True),
        sa.Column("case_id", UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("tokens_input", sa.Integer(), nullable=True),
        sa.Column("tokens_output", sa.Integer(), nullable=True),
        sa.Column(
            "tokens_total",
            sa.Integer(),
            sa.Computed("COALESCE(tokens_input, 0) + COALESCE(tokens_output, 0)", persisted=True),
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_type", sa.String(50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("is_fallback", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("original_provider", sa.String(30), nullable=True),
        sa.Column("original_model", sa.String(80), nullable=True),
        sa.Column("quality_score", sa.Numeric(3, 2), nullable=True),
        sa.Column("request_metadata", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )

    # Create indexes
    op.create_index("idx_llm_calls_created", "llm_calls", ["created_at"])
    op.create_index("idx_llm_calls_provider", "llm_calls", ["provider", "created_at"])
    op.create_index("idx_llm_calls_task", "llm_calls", ["task_type", "created_at"])
    op.create_index("idx_llm_calls_status", "llm_calls", ["status"])
    op.create_index("idx_llm_calls_caller", "llm_calls", ["caller_service", "created_at"])
    op.create_index(
        "idx_llm_calls_case",
        "llm_calls",
        ["case_id"],
        postgresql_where=sa.text("case_id IS NOT NULL"),
    )
    op.create_index(
        "idx_llm_calls_user",
        "llm_calls",
        ["user_id"],
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.create_index(
        "idx_llm_calls_fallback",
        "llm_calls",
        ["is_fallback"],
        postgresql_where=sa.text("is_fallback = TRUE"),
    )

    # Add embedding_model and embedding_dim to knowledge_chunks if not present
    op.execute(
        """
        ALTER TABLE knowledge_chunks
        ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(50) NOT NULL DEFAULT 'openai/text-embedding-3-small'
        """
    )
    op.execute(
        """
        ALTER TABLE knowledge_chunks
        ADD COLUMN IF NOT EXISTS embedding_dim INTEGER NOT NULL DEFAULT 1536
        """
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_llm_calls_fallback", table_name="llm_calls")
    op.drop_index("idx_llm_calls_user", table_name="llm_calls")
    op.drop_index("idx_llm_calls_case", table_name="llm_calls")
    op.drop_index("idx_llm_calls_caller", table_name="llm_calls")
    op.drop_index("idx_llm_calls_status", table_name="llm_calls")
    op.drop_index("idx_llm_calls_task", table_name="llm_calls")
    op.drop_index("idx_llm_calls_provider", table_name="llm_calls")
    op.drop_index("idx_llm_calls_created", table_name="llm_calls")

    # Drop table
    op.drop_table("llm_calls")

    # Remove columns from knowledge_chunks
    op.execute("ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS embedding_model")
    op.execute("ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS embedding_dim")