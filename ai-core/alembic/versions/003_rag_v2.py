"""RAG v2 tables: knowledge_sources, knowledge_chunks, rag_queries, rag_feedback"""

revision = '003'
down_revision = '002'  # поправить на реальный revision предыдущей миграции
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

def upgrade():
    # Расширение pgvector (если не установлено)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    op.create_table(
        'knowledge_sources',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('content', sa.Text),
        sa.Column('external_url', sa.Text),
        sa.Column('file_path', sa.Text),
        sa.Column('tags', sa.ARRAY(sa.String), server_default='{}'),
        sa.Column('metadata', JSONB, server_default='{}'),
        sa.Column('auto_ingest', sa.Boolean, server_default='true'),
        sa.Column('ingestion_status', sa.String(20), server_default='pending'),
        sa.Column('chunks_count', sa.Integer, server_default='0'),
        sa.Column('ingestion_started_at', sa.DateTime(timezone=True)),
        sa.Column('ingestion_completed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    op.create_table(
        'knowledge_chunks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('source_id', UUID(as_uuid=True), sa.ForeignKey('knowledge_sources.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_type', sa.String(50)),
        sa.Column('source_title', sa.String(500)),
        sa.Column('chunk_text', sa.Text, nullable=False),
        sa.Column('chunk_index', sa.Integer, nullable=False),
        sa.Column('token_count', sa.Integer),
        sa.Column('embedding', sa.Text),  # будет заменено на vector(1536) вручную
        sa.Column('fts_index', sa.Text),  # tsvector
        sa.Column('metadata', JSONB, server_default='{}'),
        sa.Column('feedback_count', sa.Integer, server_default='0'),
        sa.Column('avg_relevance_score', sa.Float, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Конвертировать embedding в настоящий vector тип
    op.execute("ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector")
    # Конвертировать fts_index в tsvector
    op.execute("ALTER TABLE knowledge_chunks ALTER COLUMN fts_index TYPE tsvector USING fts_index::tsvector")
    
    # Индексы
    op.execute("CREATE INDEX idx_chunks_embedding ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists=100)")
    op.execute("CREATE INDEX idx_chunks_fts ON knowledge_chunks USING GIN (fts_index)")
    op.create_index('idx_chunks_source_id', 'knowledge_chunks', ['source_id'])
    
    op.create_table(
        'rag_queries',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('query_text', sa.Text, nullable=False),
        sa.Column('answer', sa.Text),
        sa.Column('confidence', sa.Float),
        sa.Column('total_time_ms', sa.Integer),
        sa.Column('filters', JSONB, server_default='{}'),
        sa.Column('sources_used', sa.ARRAY(sa.String), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    op.create_table(
        'rag_feedback',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('query_id', UUID(as_uuid=True), sa.ForeignKey('rag_queries.id')),
        sa.Column('chunk_id', UUID(as_uuid=True), sa.ForeignKey('knowledge_chunks.id')),
        sa.Column('relevance_score', sa.Integer),
        sa.Column('is_helpful', sa.Boolean),
        sa.Column('comment', sa.Text),
        sa.Column('created_by', UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table('rag_feedback')
    op.drop_table('rag_queries')
    op.drop_table('knowledge_chunks')
    op.drop_table('knowledge_sources')