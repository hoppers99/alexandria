"""add_user_id_to_reading_progress

Revision ID: 5833fa3c6d93
Revises: 19cb07a3b2b4
Create Date: 2025-12-28 07:54:30.237600

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5833fa3c6d93'
down_revision: Union[str, None] = '19cb07a3b2b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add user_id column to reading_progress table
    op.add_column('reading_progress', sa.Column('user_id', sa.Integer(), nullable=True))

    # Set existing records to user_id = 1 (the default admin user)
    op.execute('UPDATE reading_progress SET user_id = 1')

    # Make user_id NOT NULL after backfilling
    op.alter_column('reading_progress', 'user_id', nullable=False)

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_reading_progress_user_id',
        'reading_progress',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Add index for user_id
    op.create_index('idx_reading_progress_user', 'reading_progress', ['user_id'])

    # Add unique constraint on (user_id, item_id) - one progress record per user per item
    op.create_unique_constraint(
        'uq_reading_progress_user_item',
        'reading_progress',
        ['user_id', 'item_id']
    )


def downgrade() -> None:
    op.drop_constraint('uq_reading_progress_user_item', 'reading_progress', type_='unique')
    op.drop_index('idx_reading_progress_user', 'reading_progress')
    op.drop_constraint('fk_reading_progress_user_id', 'reading_progress', type_='foreignkey')
    op.drop_column('reading_progress', 'user_id')
