"""RAG v2 tables

Revision ID: 003_rag_v2
Revises: 002_billing
Create Date: 2026-03-29
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

revision: str = '003_rag_v2'
down_revision: Union[str, None] = '002_billing'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Knowledge sources (original documents)
    op.create_table('knowledge_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False, comment='law, court_practice, plenum, template, faq, custom'),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True, comment='Raw content if stored inline'),
        sa.Column('external_url', sa.String(2000), nullable=True),
        sa.Column('file_path', sa.String(1000), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String(100)), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('auto_ingest', sa.Boolean(), server_default='true'),
        sa.Column('ingestion_status', sa.String(30), server_default='pending', comment='pending, processing, completed, failed'),
        sa.Column('ingestion_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ingestion_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('chunks_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_knowledge_sources_type', 'knowledge_sources', ['source_type'])
    op.create_index('idx_knowledge_sources_status', 'knowledge_sources', ['ingestion_status'])

    # Knowledge chunks (vector + FTS)
    op.create_table('knowledge_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_title', sa.String(500), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('fts_index', postgresql.TSVECTOR(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['source_id'], ['knowledge_sources.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_knowledge_chunks_source', 'knowledge_chunks', ['source_id'])
    op.create_index('idx_knowledge_chunks_embedding', 'knowledge_chunks', ['embedding'], postgresql_using='ivfflat')
    op.execute("""
        CREATE INDEX idx_knowledge_chunks_fts ON knowledge_chunks USING GIN (fts_index);
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION update_fts_index() RETURNS TRIGGER AS $$
        BEGIN
            NEW.fts_index = to_tsvector('russian', NEW.chunk_text);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_fts_index BEFORE INSERT OR UPDATE ON knowledge_chunks
        FOR EACH ROW EXECUTE FUNCTION update_fts_index();
    """)

    # RAG queries (for analytics)
    op.create_table('rag_queries',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('processed_query', postgresql.JSONB(), nullable=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('source', sa.String(20), server_default='lawyer', comment='lawyer, client, api'),
        sa.Column('retrieved_count', sa.Integer(), nullable=True),
        sa.Column('reranked_count', sa.Integer(), nullable=True),
        sa.Column('generated_answer', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Numeric(5, 2), nullable=True),
        sa.Column('total_time_ms', sa.Integer(), nullable=True),
        sa.Column('embedding_time_ms', sa.Integer(), nullable=True),
        sa.Column('retrieval_time_ms', sa.Integer(), nullable=True),
        sa.Column('rerank_time_ms', sa.Integer(), nullable=True),
        sa.Column('generation_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )
    op.create_index('idx_rag_queries_created', 'rag_queries', ['created_at'])
    op.create_index('idx_rag_queries_case', 'rag_queries', ['case_id'])

    # RAG feedback (relevance scoring)
    op.create_table('rag_feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('query_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chunk_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('relevance_score', sa.Integer(), nullable=False, comment='1‑5'),
        sa.Column('is_helpful', sa.Boolean(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['query_id'], ['rag_queries.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chunk_id'], ['knowledge_chunks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
    )
    op.create_index('idx_rag_feedback_query', 'rag_feedback', ['query_id'])
    op.create_index('idx_rag_feedback_chunk', 'rag_feedback', ['chunk_id'])

    # Update existing knowledge_base table (optional) – we keep it for backward compatibility
    op.execute("""
        ALTER TABLE knowledge_base
        ADD COLUMN IF NOT EXISTS source_id UUID REFERENCES knowledge_sources(id),
        ADD COLUMN IF NOT EXISTS chunk_index INTEGER,
        ADD COLUMN IF NOT EXISTS token_count INTEGER;
    """)


def downgrade() -> None:
    op.drop_table('rag_feedback')
    op.drop_table('rag_queries')
    op.execute("DROP TRIGGER IF EXISTS trg_fts_index ON knowledge_chunks")
    op.execute("DROP FUNCTION IF EXISTS update_fts_index()")
    op.drop_table('knowledge_chunks')
    op.drop_table('knowledge_sources')
    op.execute("""
        ALTER TABLE knowledge_base
        DROP COLUMN IF EXISTS source_id,
        DROP COLUMN IF EXISTS chunk_index,
        DROP COLUMN IF EXISTS token_count;
    """)
