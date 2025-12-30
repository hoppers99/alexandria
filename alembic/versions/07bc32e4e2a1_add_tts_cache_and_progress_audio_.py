"""add_tts_cache_and_progress_audio_tracking

Revision ID: 07bc32e4e2a1
Revises: 5833fa3c6d93
Create Date: 2025-12-29 22:01:24.537615

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '07bc32e4e2a1'
down_revision: Union[str, None] = '5833fa3c6d93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create TTS cache table
    op.create_table(
        'tts_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('chapter_number', sa.Integer(), nullable=False),
        sa.Column('voice_id', sa.String(50), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('generated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ondelete='CASCADE'),
    )

    # Add indexes for efficient lookups
    op.create_index('idx_tts_cache_item_chapter', 'tts_cache', ['item_id', 'chapter_number'])
    op.create_index('idx_tts_cache_voice', 'tts_cache', ['voice_id'])

    # Add unique constraint on (item_id, chapter_number, voice_id)
    op.create_unique_constraint(
        'uq_tts_cache_item_chapter_voice',
        'tts_cache',
        ['item_id', 'chapter_number', 'voice_id']
    )

    # Add audio tracking columns to reading_progress table
    op.add_column('reading_progress',
        sa.Column('audio_chapter', sa.Integer(), nullable=True))
    op.add_column('reading_progress',
        sa.Column('audio_position_seconds', sa.Float(), nullable=True))
    op.add_column('reading_progress',
        sa.Column('last_listened_at', sa.DateTime(), nullable=True))
    op.add_column('reading_progress',
        sa.Column('preferred_mode', sa.String(10), server_default='text', nullable=False))

    # Add index for audio chapter lookups
    op.create_index('idx_reading_progress_audio', 'reading_progress', ['audio_chapter'])


def downgrade() -> None:
    # Remove indexes and columns from reading_progress
    op.drop_index('idx_reading_progress_audio', 'reading_progress')
    op.drop_column('reading_progress', 'preferred_mode')
    op.drop_column('reading_progress', 'last_listened_at')
    op.drop_column('reading_progress', 'audio_position_seconds')
    op.drop_column('reading_progress', 'audio_chapter')

    # Drop TTS cache table and constraints
    op.drop_constraint('uq_tts_cache_item_chapter_voice', 'tts_cache', type_='unique')
    op.drop_index('idx_tts_cache_voice', 'tts_cache')
    op.drop_index('idx_tts_cache_item_chapter', 'tts_cache')
    op.drop_table('tts_cache')
