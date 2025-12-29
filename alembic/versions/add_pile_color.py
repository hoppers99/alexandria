"""Add color to collections/piles

Revision ID: add_pile_color
Revises: c1fc57423096
Create Date: 2024-12-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_pile_color'
down_revision: Union[str, None] = 'c1fc57423096'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Default colours for system piles
SYSTEM_PILE_COLORS = {
    'to_read': '#f59e0b',      # Amber for "want to read"
    'currently_reading': '#3b82f6',  # Blue for "reading"
    'read': '#22c55e',         # Green for "finished"
}


def upgrade() -> None:
    # Add color column
    op.add_column('collections', sa.Column('color', sa.String(7), nullable=True))

    # Set default colours for system piles
    for system_key, color in SYSTEM_PILE_COLORS.items():
        op.execute(
            f"UPDATE collections SET color = '{color}' WHERE system_key = '{system_key}'"
        )


def downgrade() -> None:
    op.drop_column('collections', 'color')
