"""add_tts_settings_table

Revision ID: 8594c45493c3
Revises: 07bc32e4e2a1
Create Date: 2025-12-30 11:14:14.721278

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8594c45493c3'
down_revision: Union[str, None] = '07bc32e4e2a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create system_settings table for storing TTS and other system-wide configuration
    op.create_table(
        'system_settings',
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('value_type', sa.String(length=20), nullable=False, server_default='string'),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('key')
    )

    # Insert default TTS settings
    op.execute("""
        INSERT INTO system_settings (key, value, value_type, description) VALUES
        ('tts.engine', 'chatterbox', 'string', 'TTS engine to use: coqui or chatterbox'),
        ('tts.voice', 'alloy', 'string', 'Default voice for TTS generation'),
        ('tts.exaggeration', '0.5', 'float', 'Emotion intensity for Chatterbox (0.25-2.0)'),
        ('tts.cfg_weight', '0.4', 'float', 'Pace control for Chatterbox (0.0-1.0)'),
        ('tts.temperature', '0.9', 'float', 'Sampling variance for Chatterbox (0.05-5.0)')
    """)


def downgrade() -> None:
    # Drop system_settings table
    op.drop_table('system_settings')
