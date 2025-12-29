#!/usr/bin/env python3
"""
Remove duplicate format files from items, keeping the largest file of each format.

When an item has multiple files of the same format (e.g., 2 EPUBs), this script
keeps the largest one and moves the others to .trash (and removes from database).
"""

import sys
from collections import defaultdict
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from librarian.config import settings
from librarian.db.models import File, Item, SourceFile
from librarian.filer.transfer import move_to_trash


def find_items_with_duplicate_formats(session: Session) -> dict[int, dict[str, list[File]]]:
    """Find items that have multiple files of the same format."""
    # Query for items with duplicate formats
    duplicates_query = (
        select(File.item_id, File.format, func.count(File.id).label("count"))
        .group_by(File.item_id, File.format)
        .having(func.count(File.id) > 1)
    )

    result = session.execute(duplicates_query)
    duplicate_info = result.all()

    # Build a dict of item_id -> format -> list of files
    items_with_dupes: dict[int, dict[str, list[File]]] = defaultdict(lambda: defaultdict(list))

    for item_id, fmt, count in duplicate_info:
        files = session.query(File).filter(
            File.item_id == item_id,
            File.format == fmt
        ).order_by(File.size_bytes.desc()).all()

        items_with_dupes[item_id][fmt] = files

    return dict(items_with_dupes)


def dedupe_item_files(
    session: Session,
    item_id: int,
    format_files: dict[str, list[File]],
    dry_run: bool = True,
) -> tuple[int, int]:
    """
    Remove duplicate files for an item, keeping the largest of each format.

    Returns (files_removed, bytes_freed).
    """
    item = session.get(Item, item_id)
    if not item:
        return 0, 0

    files_removed = 0
    bytes_freed = 0

    for fmt, files in format_files.items():
        if len(files) <= 1:
            continue

        # Files are already sorted by size descending, so first is largest
        keep_file = files[0]
        remove_files = files[1:]

        print(f"    {fmt.upper()}: keeping {keep_file.size_bytes:,} bytes, removing {len(remove_files)} smaller file(s)")

        for f in remove_files:
            file_path = Path(settings.library_root) / f.file_path
            print(f"      - Removing: {f.file_path} ({f.size_bytes:,} bytes)")

            if not dry_run:
                # Clear any source_files references to this file
                session.query(SourceFile).filter(
                    SourceFile.migrated_file_id == f.id
                ).update({SourceFile.migrated_file_id: None})

                # Move to trash instead of deleting
                move_to_trash(
                    file_path,
                    library_root=settings.library_root,
                    trash_dir=settings.trash_dir,
                )

                # Remove from database
                session.delete(f)

            files_removed += 1
            bytes_freed += f.size_bytes or 0

    return files_removed, bytes_freed


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Remove duplicate format files, keeping largest")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--item-id", type=int, help="Only process a specific item ID")
    args = parser.parse_args()

    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        print("Finding items with duplicate format files...")
        items_with_dupes = find_items_with_duplicate_formats(session)

        if args.item_id:
            if args.item_id in items_with_dupes:
                items_with_dupes = {args.item_id: items_with_dupes[args.item_id]}
            else:
                print(f"Item {args.item_id} has no duplicate format files")
                return

        if not items_with_dupes:
            print("No items with duplicate format files found!")
            return

        print(f"Found {len(items_with_dupes)} item(s) with duplicate format files:\n")

        total_removed = 0
        total_bytes = 0

        for item_id, format_files in items_with_dupes.items():
            item = session.get(Item, item_id)
            if not item:
                continue

            formats_summary = ", ".join(f"{fmt}:{len(files)}" for fmt, files in format_files.items())
            print(f"Item {item_id}: '{item.title}' ({formats_summary})")

            removed, freed = dedupe_item_files(session, item_id, format_files, dry_run=args.dry_run)
            total_removed += removed
            total_bytes += freed
            print()

        if not args.dry_run:
            session.commit()
            print(f"Done! Moved {total_removed} file(s) to .trash, freed {total_bytes:,} bytes ({total_bytes / 1024 / 1024:.1f} MB)")
        else:
            print(f"[DRY RUN] Would remove {total_removed} file(s), freeing {total_bytes:,} bytes ({total_bytes / 1024 / 1024:.1f} MB)")

    finally:
        session.close()


if __name__ == "__main__":
    main()
