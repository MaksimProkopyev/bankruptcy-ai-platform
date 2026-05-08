"""initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2025-03-24
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # Users
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('patronymic', sa.String(100), nullable=True),
        sa.Column('role', sa.String(30), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('max_cases', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_role', 'users', ['role'])

    # Clients
    op.create_table('clients',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('patronymic', sa.String(100), nullable=True),
        sa.Column('birth_date', sa.Date(), nullable=True),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('telegram_id', sa.String(100), nullable=True),
        sa.Column('whatsapp_phone', sa.String(20), nullable=True),
        sa.Column('preferred_channel', sa.String(20), server_default='phone'),
        sa.Column('inn', sa.String(12), nullable=True),
        sa.Column('snils', sa.String(14), nullable=True),
        sa.Column('marital_status', sa.String(20), nullable=True),
        sa.Column('region', sa.String(100), nullable=True),
        sa.Column('is_employed', sa.Boolean(), nullable=True),
        sa.Column('monthly_income', sa.Numeric(12, 2), nullable=True),
        sa.Column('utm_source', sa.String(100), nullable=True),
        sa.Column('utm_medium', sa.String(100), nullable=True),
        sa.Column('utm_campaign', sa.String(100), nullable=True),
        sa.Column('lead_source', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_clients_phone', 'clients', ['phone'])

    # Cases
    op.create_table('cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('case_number', sa.String(50), nullable=True),
        sa.Column('court_case_number', sa.String(100), nullable=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_lawyer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assigned_paralegal_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assigned_manager_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('financial_manager_name', sa.String(255), nullable=True),
        sa.Column('financial_manager_sro', sa.String(255), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='lead'),
        sa.Column('procedure_type', sa.String(30), server_default='undetermined'),
        sa.Column('total_debt', sa.Numeric(14, 2), nullable=True),
        sa.Column('secured_debt', sa.Numeric(14, 2), nullable=True),
        sa.Column('unsecured_debt', sa.Numeric(14, 2), nullable=True),
        sa.Column('ai_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('ai_recommended_procedure', sa.String(30), nullable=True),
        sa.Column('ai_risk_level', sa.String(20), nullable=True),
        sa.Column('ai_scoring_details', postgresql.JSONB(), nullable=True),
        sa.Column('court_name', sa.String(255), nullable=True),
        sa.Column('court_region', sa.String(100), nullable=True),
        sa.Column('filing_date', sa.Date(), nullable=True),
        sa.Column('first_hearing_date', sa.Date(), nullable=True),
        sa.Column('procedure_start_date', sa.Date(), nullable=True),
        sa.Column('completion_date', sa.Date(), nullable=True),
        sa.Column('service_fee', sa.Numeric(12, 2), nullable=True),
        sa.Column('total_cost', sa.Numeric(12, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String(50)), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('case_number'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id']),
        sa.ForeignKeyConstraint(['assigned_lawyer_id'], ['users.id']),
        sa.ForeignKeyConstraint(['assigned_paralegal_id'], ['users.id']),
        sa.ForeignKeyConstraint(['assigned_manager_id'], ['users.id']),
    )
    op.create_index('idx_cases_status', 'cases', ['status'])
    op.create_index('idx_cases_client', 'cases', ['client_id'])
    op.create_index('idx_cases_lawyer', 'cases', ['assigned_lawyer_id'])

    # Creditors
    op.create_table('creditors',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('creditor_type', sa.String(20), nullable=False),
        sa.Column('inn', sa.String(12), nullable=True),
        sa.Column('principal_amount', sa.Numeric(14, 2), nullable=True),
        sa.Column('interest_amount', sa.Numeric(14, 2), nullable=True),
        sa.Column('penalty_amount', sa.Numeric(14, 2), nullable=True),
        sa.Column('total_amount', sa.Numeric(14, 2), nullable=False),
        sa.Column('contract_number', sa.String(100), nullable=True),
        sa.Column('contract_date', sa.Date(), nullable=True),
        sa.Column('included_in_registry', sa.Boolean(), server_default='false'),
        sa.Column('is_secured', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    )

    # Documents
    op.create_table('documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_type', sa.String(30), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('file_name', sa.String(255), nullable=True),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('ocr_text', sa.Text(), nullable=True),
        sa.Column('extracted_data', postgresql.JSONB(), nullable=True),
        sa.Column('ai_confidence', sa.Numeric(5, 2), nullable=True),
        sa.Column('ai_validation_notes', sa.Text(), nullable=True),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('uploaded_by_client', sa.Boolean(), server_default='false'),
        sa.Column('version', sa.Integer(), server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id']),
    )

    # Case Events
    op.create_table('case_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_system_event', sa.Boolean(), server_default='false'),
        sa.Column('is_visible_to_client', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
    )

    # Deadlines
    op.create_table('deadlines',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('priority', sa.String(20), server_default='medium'),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_reminded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id']),
    )

    # Payments
    op.create_table('payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_type', sa.String(30), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('paid_date', sa.Date(), nullable=True),
        sa.Column('invoice_number', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    )

    # AI Tasks
    op.create_table('ai_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('agent_name', sa.String(100), nullable=False),
        sa.Column('task_type', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), server_default='queued'),
        sa.Column('priority', sa.Integer(), server_default='5'),
        sa.Column('input_data', postgresql.JSONB(), nullable=False),
        sa.Column('output_data', postgresql.JSONB(), nullable=True),
        sa.Column('confidence_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('llm_tokens_used', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0'),
        sa.Column('max_retries', sa.Integer(), server_default='3'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id']),
    )

    # Knowledge Base (RAG)
    op.create_table('knowledge_base',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_name', sa.String(255), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    # Vector column added separately (Alembic doesn't handle pgvector natively)
    op.execute("ALTER TABLE knowledge_base ADD COLUMN embedding vector(1536)")

    # Audit Log
    op.create_table('audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('changes', postgresql.JSONB(), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )

    # Notifications
    op.create_table('notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('channel', sa.String(20), server_default='in_app'),
        sa.Column('is_read', sa.Boolean(), server_default='false'),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id']),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id']),
    )

    # Case number sequence + trigger
    op.execute("CREATE SEQUENCE IF NOT EXISTS case_number_seq START 10001")

    # Messages (client ↔ staff communication)
    op.create_table('messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('channel', sa.String(20), nullable=False),
        sa.Column('direction', sa.String(10), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('is_ai_generated', sa.Boolean(), server_default='false'),
        sa.Column('ai_agent_name', sa.String(100), nullable=True),
        sa.Column('is_ai_handled', sa.Boolean(), server_default='false'),
        sa.Column('sent_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id']),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id']),
        sa.ForeignKeyConstraint(['sent_by'], ['users.id']),
    )

    # Consultations (booking between client and lawyer)
    op.create_table('consultations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lawyer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), server_default='30'),
        sa.Column('consultation_type', sa.String(20), server_default='phone'),
        sa.Column('status', sa.String(20), server_default='scheduled'),
        sa.Column('topic', sa.String(255), nullable=True),
        sa.Column('client_notes', sa.Text(), nullable=True),
        sa.Column('lawyer_notes', sa.Text(), nullable=True),
        sa.Column('internal_notes', sa.Text(), nullable=True),
        sa.Column('meeting_url', sa.String(500), nullable=True),
        sa.Column('recording_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id']),
        sa.ForeignKeyConstraint(['lawyer_id'], ['users.id']),
    )

    # Document Requests (lawyer asks client for specific docs)
    op.create_table('document_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('priority', sa.String(20), server_default='normal'),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('requested_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id']),
    )

    # Document Templates
    op.create_table('document_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content_html', sa.Text(), nullable=False),
        sa.Column('variables', postgresql.JSONB(), nullable=True),
        sa.Column('output_format', sa.String(10), server_default='pdf'),
        sa.Column('version', sa.Integer(), server_default='1'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
    )

    # E-Signatures
    op.create_table('e_signatures',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('document_draft_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('document_title', sa.String(255), nullable=False),
        sa.Column('document_hash', sa.String(64), nullable=False),
        sa.Column('method', sa.String(20), server_default='sms'),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('signing_code', sa.String(6), nullable=True),
        sa.Column('code_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('code_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('code_attempts', sa.Integer(), server_default='0'),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('signed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('signer_full_name', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id']),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id']),
    )

    # Document Drafts (generated from templates)
    op.create_table('document_drafts',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content_html', sa.Text(), nullable=False),
        sa.Column('filled_variables', postgresql.JSONB(), nullable=True),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('file_hash', sa.String(64), nullable=True),
        sa.Column('status', sa.String(20), server_default='draft'),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('requires_client_signature', sa.Boolean(), server_default='true'),
        sa.Column('requires_lawyer_signature', sa.Boolean(), server_default='false'),
        sa.Column('signature_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1'),
        sa.Column('parent_draft_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['document_templates.id']),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id']),
        sa.ForeignKeyConstraint(['signature_id'], ['e_signatures.id']),
        sa.ForeignKeyConstraint(['parent_draft_id'], ['document_drafts.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
    )

    # Invoices
    op.create_table('invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('invoice_number', sa.String(50), unique=True, nullable=False),
        sa.Column('invoice_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('items', postgresql.JSONB(), nullable=False),
        sa.Column('subtotal', sa.Numeric(12, 2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(12, 2), server_default='0'),
        sa.Column('total_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('status', sa.String(20), server_default='draft'),
        sa.Column('payment_url', sa.String(500), nullable=True),
        sa.Column('tochka_invoice_id', sa.String(100), nullable=True),
        sa.Column('sent_via', sa.String(20), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('viewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('bank_transaction_id', sa.String(100), nullable=True),
        sa.Column('reconciled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pdf_path', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id']),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id']),
    )

    # Acts (of completed work)
    op.create_table('acts',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('act_number', sa.String(50), unique=True, nullable=False),
        sa.Column('act_date', sa.Date(), nullable=False),
        sa.Column('services', postgresql.JSONB(), nullable=False),
        sa.Column('total_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('status', sa.String(20), server_default='draft'),
        sa.Column('client_signature_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('lawyer_signed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pdf_path', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id']),
        sa.ForeignKeyConstraint(['client_signature_id'], ['e_signatures.id']),
    )

    # Bank Webhooks (from Tochka)
    op.create_table('bank_webhooks',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('transaction_id', sa.String(100), nullable=True),
        sa.Column('amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('payer_name', sa.String(255), nullable=True),
        sa.Column('payer_inn', sa.String(12), nullable=True),
        sa.Column('purpose', sa.Text(), nullable=True),
        sa.Column('matched_invoice_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('matched_case_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_matched', sa.Boolean(), server_default='false'),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['matched_invoice_id'], ['invoices.id']),
        sa.ForeignKeyConstraint(['matched_case_id'], ['cases.id']),
    )
    op.execute("""
        CREATE OR REPLACE FUNCTION generate_case_number()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.case_number := 'BK-' || TO_CHAR(now(), 'YYYY') || '-' || LPAD(nextval('case_number_seq')::text, 5, '0');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_case_number
            BEFORE INSERT ON cases
            FOR EACH ROW
            WHEN (NEW.case_number IS NULL)
            EXECUTE FUNCTION generate_case_number();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_case_number ON cases")
    op.execute("DROP FUNCTION IF EXISTS generate_case_number()")
    op.execute("DROP SEQUENCE IF EXISTS case_number_seq")

    for table in [
        'bank_webhooks', 'acts', 'invoices', 'document_drafts', 'e_signatures',
        'document_templates', 'document_requests', 'consultations', 'messages',
        'notifications', 'audit_log', 'knowledge_base', 'ai_tasks',
        'payments', 'deadlines', 'case_events', 'documents',
        'creditors', 'cases', 'clients', 'users',
    ]:
        op.drop_table(table)
