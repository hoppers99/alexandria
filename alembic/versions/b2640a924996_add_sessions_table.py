"""add_sessions_table

Revision ID: b2640a924996
Revises: add_pile_color
Create Date: 2025-12-27 14:32:21.085688

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2640a924996'
down_revision: Union[str, None] = 'add_pile_color'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_accessed', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_sessions_user', 'sessions', ['user_id'], unique=False)
    op.create_index('idx_sessions_expires', 'sessions', ['expires_at'], unique=False)


def downgrade() -> None:
    # Drop sessions table
    op.drop_index('idx_sessions_expires', table_name='sessions')
    op.drop_index('idx_sessions_user', table_name='sessions')
    op.drop_table('sessions')
