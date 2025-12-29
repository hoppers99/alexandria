#!/usr/bin/env python3
"""
Fix items that have multiple files from different series books merged together.

This script identifies items where files belong to different series books
(based on file path patterns like "Book 01", "Book 02") and splits them
into separate items.
"""

import re
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from librarian.config import settings
from librarian.db.models import Creator, File, Item, ItemCreator


def extract_book_number_from_path(file_path: str) -> int | None:
    """Extract book number from file path like 'Book 01 - Title'."""
    # Match patterns like "Book 01", "Book 1", "Book 07"
    match = re.search(r"Book\s*(\d+)", file_path, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def find_items_with_merged_files(session: Session) -> list[tuple[Item, dict[int | None, list[File]]]]:
    """Find items that have files from multiple series books."""
    problematic_items = []

    # Get all items with multiple files
    items = session.query(Item).all()

    for item in items:
        if len(item.files) <= 1:
            continue

        # Group files by book number extracted from path
        files_by_book: dict[int | None, list[File]] = {}
        for f in item.files:
            book_num = extract_book_number_from_path(f.file_path)
            if book_num not in files_by_book:
                files_by_book[book_num] = []
            files_by_book[book_num].append(f)

        # If we have files from multiple different book numbers, this is a problem
        # (excluding None which means no book number in path)
        book_numbers = [k for k in files_by_book.keys() if k is not None]
        if len(book_numbers) > 1:
            problematic_items.append((item, files_by_book))

    return problematic_items


def split_merged_item(
    session: Session,
    original_item: Item,
    files_by_book: dict[int | None, list[File]],
    dry_run: bool = True,
) -> list[Item]:
    """Split a merged item into separate items per book number."""
    created_items = []

    # Get the original item's authors
    original_authors = [
        ic.creator for ic in sorted(original_item.item_creators, key=lambda x: x.position)
        if ic.role == "author"
    ]

    # Determine which book number should keep the original item
    # (the one with the most files, or the first one)
    sorted_books = sorted(
        [(k, v) for k, v in files_by_book.items() if k is not None],
        key=lambda x: (-len(x[1]), x[0])
    )

    if not sorted_books:
        print(f"  No book numbers found, skipping item {original_item.id}")
        return []

    # First book keeps the original item, others get new items
    keep_book_num = sorted_books[0][0]

    print(f"  Item {original_item.id}: '{original_item.title}'")
    print(f"    Will keep book #{keep_book_num} on original item")

    for book_num, files in sorted_books:
        if book_num == keep_book_num:
            # Update original item's series_index
            if not dry_run:
                original_item.series_index = book_num
                # Update files to stay with original item (they already are)
            print(f"    Book #{book_num}: {len(files)} file(s) - keeping on original item")
            continue

        # Create a new item for this book number
        print(f"    Book #{book_num}: {len(files)} file(s) - creating new item")

        if not dry_run:
            new_item = Item(
                title=original_item.title,
                sort_title=original_item.sort_title,
                subtitle=original_item.subtitle,
                classification_code=original_item.classification_code,
                media_type=original_item.media_type,
                isbn=None,  # Different book, different ISBN
                isbn13=None,
                description=original_item.description,
                publisher=original_item.publisher,
                language=original_item.language,
                series_name=original_item.series_name or "Book",
                series_index=book_num,
                tags=original_item.tags,
                page_count=original_item.page_count,
                identifiers=None,
            )
            session.add(new_item)
            session.flush()

            # Copy authors to new item
            for pos, creator in enumerate(original_authors):
                item_creator = ItemCreator(
                    item_id=new_item.id,
                    creator_id=creator.id,
                    role="author",
                    position=pos,
                )
                session.add(item_creator)

            # Move files to new item
            for f in files:
                f.item_id = new_item.id

            # Try to set cover from the file's folder
            if files:
                file_folder = Path(settings.library_root) / Path(files[0].file_path).parent
                cover_path = file_folder / "cover.jpg"
                if cover_path.exists():
                    new_item.cover_path = str(cover_path.relative_to(settings.library_root))

            created_items.append(new_item)

    # Handle files without a book number - keep them on original item
    if None in files_by_book:
        files_without_num = files_by_book[None]
        print(f"    No book #: {len(files_without_num)} file(s) - keeping on original item")

    return created_items


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fix merged items with files from different series books")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--item-id", type=int, help="Only process a specific item ID")
    args = parser.parse_args()

    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        print("Finding items with merged files from different series books...")
        problematic_items = find_items_with_merged_files(session)

        if args.item_id:
            problematic_items = [(i, f) for i, f in problematic_items if i.id == args.item_id]

        if not problematic_items:
            print("No problematic items found!")
            return

        print(f"Found {len(problematic_items)} item(s) with merged files:\n")

        total_created = 0
        for item, files_by_book in problematic_items:
            book_nums = sorted([k for k in files_by_book.keys() if k is not None])
            print(f"Item {item.id}: '{item.title}' has files from books: {book_nums}")

            if args.dry_run:
                print("  [DRY RUN] Would split into separate items")
                split_merged_item(session, item, files_by_book, dry_run=True)
            else:
                created = split_merged_item(session, item, files_by_book, dry_run=False)
                total_created += len(created)
            print()

        if not args.dry_run:
            session.commit()
            print(f"Done! Created {total_created} new item(s)")
        else:
            print(f"[DRY RUN] Would create new items for the merged files")

    finally:
        session.close()


if __name__ == "__main__":
    main()
