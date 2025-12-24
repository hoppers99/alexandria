"""restore_classification_fk_with_data

Revision ID: ce410afb8eee
Revises: 2667f47d7311
Create Date: 2025-12-23 19:41:39.354242

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce410afb8eee'
down_revision: Union[str, None] = '2667f47d7311'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# DDC class names for generating missing classifications
DDC_CLASS_NAMES = {
    "000": "Computer Science, Information & General Works",
    "100": "Philosophy & Psychology",
    "200": "Religion",
    "300": "Social Sciences",
    "400": "Language",
    "500": "Science",
    "600": "Technology",
    "700": "Arts & Recreation",
    "800": "Literature",
    "900": "History & Geography",
}


def get_ddc_name(code: str) -> str:
    """Generate a name for a DDC code."""
    if len(code) < 3:
        code = code.zfill(3)

    # Get top-level class name
    top_level = code[0] + "00"
    class_name = DDC_CLASS_NAMES.get(top_level, "General")

    return f"{class_name} - {code}"


def upgrade() -> None:
    # Get connection for data operations
    conn = op.get_bind()

    # Find all classification codes used in items that don't exist in classifications
    result = conn.execute(sa.text("""
        SELECT DISTINCT i.classification_code
        FROM items i
        LEFT JOIN classifications c ON i.classification_code = c.code
        WHERE i.classification_code IS NOT NULL
        AND c.code IS NULL
    """))

    missing_codes = [row[0] for row in result]

    # Insert missing classifications
    for code in missing_codes:
        name = get_ddc_name(code)
        # Get parent code (e.g., "816" -> "810")
        parent_code = code[0] + "10" if len(code) >= 3 else None

        # Check if parent exists
        if parent_code:
            parent_exists = conn.execute(
                sa.text("SELECT 1 FROM classifications WHERE code = :code"),
                {"code": parent_code}
            ).fetchone()
            if not parent_exists:
                parent_code = code[0] + "00"  # Fall back to top-level

        conn.execute(
            sa.text("""
                INSERT INTO classifications (code, name, parent_code, system)
                VALUES (:code, :name, :parent_code, 'ddc')
                ON CONFLICT (code) DO NOTHING
            """),
            {"code": code, "name": name, "parent_code": parent_code}
        )

    # Re-add the foreign key constraint
    op.create_foreign_key(
        'items_classification_code_fkey',
        'items',
        'classifications',
        ['classification_code'],
        ['code'],
    )


def downgrade() -> None:
    # Drop the foreign key constraint
    op.drop_constraint('items_classification_code_fkey', 'items', type_='foreignkey')
