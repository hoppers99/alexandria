"""add_backdrop_path

Revision ID: 66b920a99afe
Revises: cd19c4aa26ac
Create Date: 2025-12-26 10:21:18.396577

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '66b920a99afe'
down_revision: Union[str, None] = 'cd19c4aa26ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('items', sa.Column('backdrop_path', sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column('items', 'backdrop_path')
