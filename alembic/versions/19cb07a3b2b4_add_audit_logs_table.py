"""add_audit_logs_table

Revision ID: 19cb07a3b2b4
Revises: b2640a924996
Create Date: 2025-12-28 08:30:03.100611

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '19cb07a3b2b4'
down_revision: Union[str, None] = 'b2640a924996'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('event_category', sa.String(length=20), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_user', 'audit_logs', ['user_id'], unique=False)
    op.create_index('idx_audit_event_type', 'audit_logs', ['event_type'], unique=False)
    op.create_index('idx_audit_created', 'audit_logs', ['created_at'], unique=False)
    op.create_index('idx_audit_category', 'audit_logs', ['event_category'], unique=False)


def downgrade() -> None:
    # Drop audit_logs table
    op.drop_index('idx_audit_category', table_name='audit_logs')
    op.drop_index('idx_audit_created', table_name='audit_logs')
    op.drop_index('idx_audit_event_type', table_name='audit_logs')
    op.drop_index('idx_audit_user', table_name='audit_logs')
    op.drop_table('audit_logs')
