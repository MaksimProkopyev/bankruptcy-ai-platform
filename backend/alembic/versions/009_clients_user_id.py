"""Add user_id to clients table

Revision ID: 009_clients_user_id
Revises: 007_llm_calls
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '009_clients_user_id'
down_revision = '007_llm_calls'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('clients',
        sa.Column('user_id', UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'),
                  nullable=True)
    )
    op.create_index('idx_clients_user_id', 'clients', ['user_id'])


def downgrade() -> None:
    op.drop_index('idx_clients_user_id', table_name='clients')
    op.drop_column('clients', 'user_id')
