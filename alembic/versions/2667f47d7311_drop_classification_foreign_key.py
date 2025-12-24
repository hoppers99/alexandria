"""drop_classification_foreign_key

Revision ID: 2667f47d7311
Revises: 75b0e362b398
Create Date: 2025-12-23 19:37:56.266003

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2667f47d7311'
down_revision: Union[str, None] = '75b0e362b398'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the foreign key constraint on classification_code
    # This allows storing any DDC code without requiring it in classifications table
    op.drop_constraint('items_classification_code_fkey', 'items', type_='foreignkey')


def downgrade() -> None:
    # Re-add the foreign key constraint
    op.create_foreign_key(
        'items_classification_code_fkey',
        'items',
        'classifications',
        ['classification_code'],
        ['code'],
    )
