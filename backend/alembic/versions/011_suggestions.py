"""Staff suggestions and tasks tables

Revision ID: 011_suggestions
Revises: 010_rbac_rls
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa

revision = '011_suggestions'
down_revision = '010_rbac_rls'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Tasks table (personal tasks assigned to staff)
    op.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            case_id     UUID REFERENCES cases(id) ON DELETE SET NULL,
            assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
            title       TEXT NOT NULL,
            description TEXT,
            status      TEXT NOT NULL DEFAULT 'new',
            priority    TEXT NOT NULL DEFAULT 'medium',
            due_date    TIMESTAMPTZ,
            created_at  TIMESTAMPTZ DEFAULT NOW(),
            updated_at  TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON tasks(assigned_to);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_case_id ON tasks(case_id);")

    # 2. Suggestions table
    op.execute("""
        CREATE TABLE IF NOT EXISTS suggestions (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            author_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title       TEXT NOT NULL,
            body        TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'new',
            admin_note  TEXT,
            created_at  TIMESTAMPTZ DEFAULT NOW(),
            updated_at  TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_suggestions_author ON suggestions(author_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_suggestions_status ON suggestions(status);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS suggestions;")
    op.execute("DROP TABLE IF EXISTS tasks;")
