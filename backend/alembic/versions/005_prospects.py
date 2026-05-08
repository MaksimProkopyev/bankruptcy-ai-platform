"""prospects: leadgen/prospecting layer

Revision ID: 005_prospects
Revises: 004_lead_collector
Create Date: 2026-04-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "005_prospects"
down_revision: Union[str, None] = "004_lead_collector"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create prospects table
    op.create_table(
        "prospects",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("source_category", sa.String(20), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("acquisition_mode", sa.String(10), server_default="inbound", nullable=False),
        sa.Column("source_external_id", sa.String(255), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_raw_data", postgresql.JSONB(), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("inn", sa.String(12), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("debt_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("debt_type", sa.String(50), nullable=True),
        sa.Column("creditor_count", sa.Integer(), nullable=True),
        sa.Column("has_property", sa.Boolean(), nullable=True),
        sa.Column("enrichment_data", postgresql.JSONB(), nullable=True),
        sa.Column("enriched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), server_default="new", nullable=False),
        sa.Column("outreach_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_outreach_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outreach_channel", sa.String(20), nullable=True),
        sa.Column("outreach_response", sa.Text(), nullable=True),
        sa.Column("converted_lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(100), nullable=True),
        sa.Column("prospect_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("temperature", sa.String(10), server_default="cold", nullable=False),
        sa.Column("utm_source", sa.String(100), nullable=True),
        sa.Column("utm_medium", sa.String(100), nullable=True),
        sa.Column("utm_campaign", sa.String(100), nullable=True),
        sa.Column("utm_content", sa.String(100), nullable=True),
        sa.Column("utm_term", sa.String(100), nullable=True),
        sa.Column("referral_code", sa.String(20), nullable=True),
        sa.Column("referrer_client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["converted_lead_id"], ["leads.id"], name="fk_prospects_converted_lead_id"),
        sa.ForeignKeyConstraint(["referrer_client_id"], ["clients.id"], name="fk_prospects_referrer_client_id"),
        sa.UniqueConstraint("source_type", "source_external_id", name="uq_prospects_source_external_id"),
    )
    # Create indexes
    op.create_index("idx_prospects_status", "prospects", ["status"])
    op.create_index("idx_prospects_category", "prospects", ["source_category"])
    op.create_index("idx_prospects_source", "prospects", ["source_type"])
    op.create_index("idx_prospects_inn", "prospects", ["inn"], postgresql_where=sa.text("inn IS NOT NULL"))
    op.create_index("idx_prospects_phone", "prospects", ["phone"], postgresql_where=sa.text("phone IS NOT NULL"))
    op.create_index("idx_prospects_region", "prospects", ["region"])
    op.create_index("idx_prospects_temperature", "prospects", ["temperature"])
    op.create_index("idx_prospects_created", "prospects", ["created_at"], postgresql_using="brin")
    op.create_index("idx_prospects_score", "prospects", ["prospect_score"])
    op.create_index("idx_prospects_utm", "prospects", ["utm_source", "utm_medium", "utm_campaign"], postgresql_where=sa.text("utm_source IS NOT NULL"))
    op.create_index("idx_prospects_referral", "prospects", ["referral_code"], postgresql_where=sa.text("referral_code IS NOT NULL"))

    # Create prospect_sources_config table
    op.create_table(
        "prospect_sources_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("source_category", sa.String(20), nullable=False),
        sa.Column("source_type", sa.String(50), unique=True, nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("display_icon", sa.String(10), nullable=True),
        sa.Column("acquisition_mode", sa.String(10), server_default="inbound", nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_automated", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("schedule_cron", sa.String(50), nullable=True),
        sa.Column("config", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_status", sa.String(20), nullable=True),
        sa.Column("last_run_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("stats", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # Insert initial data for government sources
    op.execute("""
        INSERT INTO prospect_sources_config (source_category, source_type, display_name, display_icon, acquisition_mode, is_automated, config) VALUES
        ('government', 'fssp',        'ФССП',        '⚖️', 'parsed', true,  '{"min_debt": 500000, "regions": ["77", "50", "78"], "mock_mode": true}'),
        ('government', 'efrsb',       'ЕФРСБ',       '📋', 'parsed', true,  '{"filter": "no_representative", "mock_mode": true}'),
        ('government', 'kad_arbitr',  'КАД Арбитр',  '🏛', 'parsed', true,  '{"filter": "returned_or_left_without_motion", "mock_mode": true}'),
        ('government', 'fns',         'ФНС',         '🏦', 'parsed', true,  '{"filter": "former_ip_with_debt", "mock_mode": true}'),
        ('government', 'rosreestr',   'Росреестр',    '🏠', 'parsed', true,  '{"filter": "arrests_encumbrances", "mock_mode": true}'),
        ('government', 'mfc',         'МФЦ',         '🏢', 'parsed', true,  '{"filter": "rejected_extrajudicial", "mock_mode": true}')
    """)

    # Insert inbound sources
    op.execute("""
        INSERT INTO prospect_sources_config (source_category, source_type, display_name, display_icon, acquisition_mode, is_automated) VALUES
        ('website',  'website_form',       'Форма на сайте',   '🌐', 'inbound', false),
        ('website',  'website_calculator', 'Калькулятор',      '🧮', 'inbound', false),
        ('website',  'website_chat',       'Чат на сайте',     '💬', 'inbound', false),
        ('ads',      'yandex_direct',      'Яндекс.Директ',   '📢', 'inbound', false),
        ('ads',      'vk_ads',             'VK Реклама',       '📣', 'inbound', false),
        ('social',   'telegram_bot',       'Telegram-бот',     '📱', 'inbound', false),
        ('social',   'telegram_channel',   'Telegram-канал',   '📢', 'inbound', false),
        ('social',   'vk_organic',         'VK сообщество',    '👥', 'inbound', false),
        ('referral', 'client_referral',    'Реферал клиента',  '🤝', 'inbound', false),
        ('partner',  'partner_referral',   'Партнёр',          '🏢', 'inbound', false),
        ('manual',   'manual_entry',       'Ручной ввод',      '✍️', 'manual',  false),
        ('manual',   'phone_call',         'Входящий звонок',  '📞', 'manual',  false)
    """)


def downgrade() -> None:
    op.drop_table("prospect_sources_config")
    op.drop_table("prospects")