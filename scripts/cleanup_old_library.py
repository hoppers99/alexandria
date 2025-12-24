#!/usr/bin/env python3
"""
Cleanup script for migrated library files.

This script:
1. Deletes files from the old library that have been migrated or marked as duplicates
2. Moves pending files to the new library's .returns folder
3. Updates database paths for moved files

Usage:
    uv run python scripts/cleanup_old_library.py --dry-run  # Preview changes
    uv run python scripts/cleanup_old_library.py            # Execute cleanup
"""

import argparse
import shutil
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from librarian.config import settings


def delete_migrated_files(session: Session, dry_run: bool = True) -> tuple[int, int]:
    """Delete files that have been successfully migrated or are duplicates."""
    # Get migrated and duplicate source files
    result = session.execute(
        text("""
            SELECT id, source_path, status
            FROM source_files
            WHERE status IN ('migrated', 'duplicate')
        """)
    )

    deleted = 0
    errors = 0

    for row in result:
        source_path = Path(row.source_path)

        if not source_path.exists():
            print(f"  [SKIP] Already gone: {source_path}")
            continue

        if dry_run:
            print(f"  [DRY-RUN] Would delete: {source_path}")
            deleted += 1
        else:
            try:
                source_path.unlink()
                print(f"  [DELETED] {source_path}")
                deleted += 1

                # Clean up empty parent directories
                parent = source_path.parent
                while parent.exists() and not any(parent.iterdir()):
                    print(f"  [RMDIR] {parent}")
                    parent.rmdir()
                    parent = parent.parent

            except Exception as e:
                print(f"  [ERROR] {source_path}: {e}")
                errors += 1

    return deleted, errors


def move_pending_files(
    session: Session,
    new_returns_dir: Path,
    dry_run: bool = True
) -> tuple[int, int]:
    """Move pending files to the new library's .returns folder."""
    result = session.execute(
        text("""
            SELECT id, source_path, filename
            FROM source_files
            WHERE status = 'pending'
        """)
    )

    moved = 0
    errors = 0

    for row in result:
        source_path = Path(row.source_path)

        if not source_path.exists():
            print(f"  [SKIP] Missing: {source_path}")
            continue

        # Destination is .returns/filename
        dest_path = new_returns_dir / row.filename

        # Handle name conflicts
        if dest_path.exists():
            stem = dest_path.stem
            suffix = dest_path.suffix
            counter = 1
            while dest_path.exists():
                dest_path = new_returns_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        if dry_run:
            print(f"  [DRY-RUN] Would move: {source_path.name}")
            print(f"            -> {dest_path}")
            moved += 1
        else:
            try:
                # Ensure destination directory exists
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                # Move the file
                shutil.move(str(source_path), str(dest_path))
                print(f"  [MOVED] {source_path.name}")
                print(f"          -> {dest_path}")

                # Update database with new path
                session.execute(
                    text("""
                        UPDATE source_files
                        SET source_path = :new_path
                        WHERE id = :id
                    """),
                    {"new_path": str(dest_path), "id": row.id}
                )

                moved += 1

                # Clean up empty parent directories in old location
                parent = source_path.parent
                while parent.exists() and not any(parent.iterdir()):
                    print(f"  [RMDIR] {parent}")
                    parent.rmdir()
                    parent = parent.parent

            except Exception as e:
                print(f"  [ERROR] {source_path}: {e}")
                errors += 1

    return moved, errors


def main():
    parser = argparse.ArgumentParser(description="Clean up old library after migration")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without making them"
    )
    parser.add_argument(
        "--skip-delete",
        action="store_true",
        help="Skip deletion of migrated files"
    )
    parser.add_argument(
        "--skip-move",
        action="store_true",
        help="Skip moving pending files"
    )
    args = parser.parse_args()

    # Get library root from settings
    library_root = settings.library_root
    returns_dir = settings.returns_dir

    print(f"Library root: {library_root}")
    print(f"Returns folder: {returns_dir}")
    print(f"Dry run: {args.dry_run}")
    print()

    # Connect to database
    engine = create_engine(settings.database_url)

    with Session(engine) as session:
        # Step 1: Delete migrated and duplicate files
        if not args.skip_delete:
            print("=" * 60)
            print("DELETING MIGRATED/DUPLICATE FILES FROM OLD LIBRARY")
            print("=" * 60)
            deleted, errors = delete_migrated_files(session, args.dry_run)
            print(f"\nDeleted: {deleted}, Errors: {errors}")
            print()

        # Step 2: Move pending files
        if not args.skip_move:
            print("=" * 60)
            print("MOVING PENDING FILES TO NEW RETURNS FOLDER")
            print("=" * 60)
            moved, errors = move_pending_files(session, returns_dir, args.dry_run)
            print(f"\nMoved: {moved}, Errors: {errors}")
            print()

        # Commit changes if not dry run
        if not args.dry_run:
            session.commit()
            print("Changes committed to database.")
        else:
            print("DRY RUN - No changes made. Run without --dry-run to execute.")


if __name__ == "__main__":
    main()
