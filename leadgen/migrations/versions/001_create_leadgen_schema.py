"""Create leadgen schema and tables

Revision ID: leadgen_001
Revises:
Create Date: 2026-05-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "leadgen_001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS leadgen")

    op.execute("""
    CREATE TABLE leadgen.lead_sources (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        channel TEXT NOT NULL,
        external_id TEXT,
        name TEXT,
        phone TEXT,
        email TEXT,
        meta JSONB DEFAULT '{}',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )""")

    op.execute("""
    CREATE TABLE leadgen.leads (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        source_id UUID REFERENCES leadgen.lead_sources(id),
        channel TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'new',
        funnel_stage TEXT NOT NULL DEFAULT 'incoming',
        assigned_to UUID,
        debt_amount NUMERIC,
        debt_type TEXT,
        has_property BOOLEAN,
        has_income BOOLEAN,
        qualification_score INTEGER,
        disqualify_reason TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        converted_at TIMESTAMPTZ,
        crm_client_id UUID
    )""")

    op.execute("""
    CREATE TABLE leadgen.lead_messages (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        lead_id UUID REFERENCES leadgen.leads(id),
        direction TEXT NOT NULL,
        channel TEXT NOT NULL,
        content TEXT NOT NULL,
        content_type TEXT DEFAULT 'text',
        external_id TEXT,
        sent_at TIMESTAMPTZ DEFAULT NOW(),
        meta JSONB DEFAULT '{}'
    )""")

    op.execute("""
    CREATE TABLE leadgen.lead_scores (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        lead_id UUID REFERENCES leadgen.leads(id),
        score INTEGER NOT NULL,
        model TEXT,
        reasoning TEXT,
        signals JSONB DEFAULT '{}',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )""")

    op.execute("""
    CREATE TABLE leadgen.prospects (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        lead_id UUID REFERENCES leadgen.leads(id) UNIQUE,
        qualification_data JSONB NOT NULL,
        confirmed_by UUID,
        confirmed_at TIMESTAMPTZ,
        crm_client_id UUID,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )""")

    op.execute("""
    CREATE TABLE leadgen.qualification_tasks (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        lead_id UUID REFERENCES leadgen.leads(id),
        status TEXT DEFAULT 'pending',
        ai_studio_task_id TEXT,
        result JSONB,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        completed_at TIMESTAMPTZ
    )""")

    # Индексы
    op.execute("CREATE INDEX idx_leadgen_leads_status ON leadgen.leads(status)")
    op.execute("CREATE INDEX idx_leadgen_leads_channel ON leadgen.leads(channel)")
    op.execute("CREATE INDEX idx_leadgen_leads_assigned ON leadgen.leads(assigned_to)")
    op.execute("CREATE INDEX idx_leadgen_messages_lead ON leadgen.lead_messages(lead_id)")
    op.execute(
        "CREATE INDEX idx_leadgen_sources_channel_ext ON leadgen.lead_sources(channel, external_id)"
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA leadgen CASCADE")
