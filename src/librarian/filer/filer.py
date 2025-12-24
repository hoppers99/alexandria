"""Main filer module for copying files and creating database records."""

import logging
import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from librarian.classifier import ClassificationResult
from librarian.config import settings
from librarian.covers import download_cover, extract_cover, process_cover
from librarian.db.models import Classification, Creator, File, Item, ItemCreator, SourceFile
from librarian.enricher import EnrichedMetadata
from librarian.filer.naming import (
    ensure_unique_path,
    generate_filename,
    generate_folder_name,
    generate_path,
)
from librarian.filer.transfer import cleanup_empty_parents, copy_verify_remove
from librarian.inspector.formats import get_media_type

logger = logging.getLogger(__name__)


async def file_item(
    session: Session,
    source_file: SourceFile,
    enriched: EnrichedMetadata,
    classification: ClassificationResult,
    dry_run: bool = False,
) -> tuple[Item | None, File | None]:
    """
    File a source item into the library.

    This:
    1. Creates or finds the Item record
    2. Generates the canonical folder and filename
    3. Copies the file to Fiction/ or Non-Fiction/DDC/ structure
    4. Saves cover in item folder
    5. Creates the File record
    6. Updates SourceFile status

    Args:
        session: Database session
        source_file: The source file being processed
        enriched: Enriched metadata from API lookups
        classification: Classification result (fiction/DDC)
        dry_run: If True, don't actually copy files

    Returns:
        Tuple of (Item, File) if successful, (None, None) if failed
    """
    # Get metadata
    title = enriched.title or _title_from_filename(source_file.filename)
    authors = enriched.authors or []
    series = None
    series_index = None

    # Check extracted metadata for series info
    extracted = source_file.extracted_metadata or {}
    if extracted.get("series"):
        series = extracted["series"]
        series_index = extracted.get("series_index")

    # Generate folder name (same format as filename but without extension)
    folder_name = generate_folder_name(
        title=title,
        authors=authors,
        series=series,
        series_index=series_index,
        author_format=settings.author_format,
    )

    # Generate filename
    filename = generate_filename(
        title=title,
        authors=authors,
        series=series,
        series_index=series_index,
        extension=source_file.format,
        author_format=settings.author_format,
    )

    # Generate target path using Fiction/Non-Fiction structure
    target_path = generate_path(
        ddc=classification.ddc,
        folder_name=folder_name,
        filename=filename,
        library_root=settings.library_root,
        is_fiction=classification.is_fiction,
    )

    # Check if file already exists in database (by checksum)
    existing_file = session.query(File).filter(
        File.checksum_md5 == source_file.checksum_md5
    ).first()
    if existing_file:
        # Already migrated - this is a duplicate
        source_file.status = "duplicate"
        source_file.migrated_file_id = existing_file.id
        source_file.processed_at = datetime.now()

        # Clean up the duplicate source file
        if not dry_run:
            source_path = Path(source_file.source_path)
            try:
                source_path.unlink()
                cleanup_empty_parents(source_path.parent, settings.returns_dir)
            except OSError as e:
                logger.warning(f"Could not remove duplicate source file {source_path}: {e}")

        return existing_file.item, existing_file

    # Ensure unique path if file physically exists
    target_path = ensure_unique_path(target_path)

    # Create directory if needed (item folder)
    item_folder = target_path.parent
    if not dry_run:
        item_folder.mkdir(parents=True, exist_ok=True)

    # Find or create Item
    item = _find_or_create_item(
        session=session,
        title=title,
        authors=authors,
        enriched=enriched,
        classification=classification,
        media_type=get_media_type(source_file.format),
        series=series,
        series_index=series_index,
    )

    if not dry_run:
        session.flush()  # Get item.id

    # Copy, verify, and remove source file
    source_path = Path(source_file.source_path)
    if not dry_run:
        # Extract cover BEFORE we remove the source file
        cover_path = None
        if not item.cover_path:
            cover_path = await _save_cover_to_folder(
                source_path=source_path,
                file_format=source_file.format,
                cover_url=enriched.cover_url,
                item_folder=item_folder,
                library_root=settings.library_root,
            )

        # Now do the copy-verify-remove
        try:
            success = copy_verify_remove(
                source=source_path,
                destination=target_path,
                expected_checksum=source_file.checksum_md5,
                cleanup_parents_up_to=settings.returns_dir,
            )
            if not success:
                source_file.status = "failed"
                source_file.error_message = "Copy verification failed"
                source_file.processed_at = datetime.now()
                return None, None
        except (OSError, shutil.Error) as e:
            source_file.status = "failed"
            source_file.error_message = f"Copy failed: {e}"
            source_file.processed_at = datetime.now()
            return None, None

        # Update cover path if we got one
        if cover_path:
            item.cover_path = cover_path

    # Create File record
    file_record = File(
        item_id=item.id if not dry_run else 0,
        file_path=str(target_path.relative_to(settings.library_root)),
        format=source_file.format,
        size_bytes=source_file.size_bytes,
        checksum_md5=source_file.checksum_md5,
        checksum_sha256=source_file.checksum_sha256,
        metadata_extracted=True,
    )

    if not dry_run:
        session.add(file_record)

        # Update source file status
        source_file.status = "migrated"
        source_file.migrated_file_id = file_record.id
        source_file.processed_at = datetime.now()

    return item, file_record


async def _save_cover_to_folder(
    source_path: Path,
    file_format: str,
    cover_url: str | None,
    item_folder: Path,
    library_root: Path,
) -> str | None:
    """
    Extract or download cover and save to item folder.

    Returns relative path to cover, or None if no cover available.
    """
    cover_data: bytes | None = None

    # Try extraction first (for EPUBs)
    cover_data = extract_cover(source_path, file_format)

    # Fall back to download
    if cover_data is None and cover_url:
        cover_data = await download_cover(cover_url)

    if cover_data is None:
        return None

    # Process and save to item folder
    processed = process_cover(cover_data)
    cover_path = item_folder / "cover.jpg"
    cover_path.write_bytes(processed)

    # Return relative path from library root
    return str(cover_path.relative_to(library_root))


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


def _ensure_classification_exists(session: Session, ddc_code: str | None) -> None:
    """Ensure the DDC classification exists in the database, creating it if needed."""
    if not ddc_code:
        return

    # Check if it already exists
    existing = session.query(Classification).filter(Classification.code == ddc_code).first()
    if existing:
        return

    # Generate a name for this code
    code = ddc_code.zfill(3) if len(ddc_code) < 3 else ddc_code
    top_level = code[0] + "00"
    class_name = DDC_CLASS_NAMES.get(top_level, "General")
    name = f"{class_name} - {code}"

    # Get parent code (e.g., "816" -> "810")
    parent_code = code[0] + "10" if len(code) >= 3 else None
    if parent_code:
        parent_exists = session.query(Classification).filter(
            Classification.code == parent_code
        ).first()
        if not parent_exists:
            parent_code = code[0] + "00"  # Fall back to top-level

    # Create the classification
    classification = Classification(
        code=ddc_code,
        name=name,
        parent_code=parent_code,
        system="ddc",
    )
    session.add(classification)
    session.flush()


def _find_or_create_item(
    session: Session,
    title: str,
    authors: list[str],
    enriched: EnrichedMetadata,
    classification: ClassificationResult,
    media_type: str,
    series: str | None = None,
    series_index: float | None = None,
) -> Item:
    """Find an existing item by ISBN, title+author, or create a new one."""
    # Ensure classification exists in database
    _ensure_classification_exists(session, classification.ddc)

    # Try to find by ISBN first (most reliable)
    if enriched.isbn13:
        existing = session.query(Item).filter(Item.isbn13 == enriched.isbn13).first()
        if existing:
            return existing

    if enriched.isbn:
        existing = session.query(Item).filter(Item.isbn == enriched.isbn).first()
        if existing:
            return existing

    # Try to find by title + first author (for books without ISBN)
    existing = _find_by_title_and_author(session, title, authors)
    if existing:
        return existing

    # Determine tags - use genres for fiction, subjects for non-fiction
    if classification.is_fiction and classification.genres:
        tags = classification.genres
    elif enriched.subjects:
        tags = enriched.subjects[:10]
    else:
        tags = None

    # Create new item
    item = Item(
        title=title,
        sort_title=_generate_sort_title(title),
        subtitle=enriched.subtitle,
        classification_code=classification.ddc,
        media_type=media_type,
        isbn=enriched.isbn,
        isbn13=enriched.isbn13,
        description=enriched.description,
        publisher=enriched.publisher,
        language=enriched.language or "en",
        series_name=series,
        series_index=series_index,
        tags=tags,
        page_count=enriched.page_count,
        identifiers={
            "openlibrary": enriched.openlibrary_key,
            "google_books": enriched.google_books_id,
            "oclc_owi": enriched.oclc_owi,
            "is_fiction": classification.is_fiction,
        },
    )

    session.add(item)
    session.flush()  # Get item.id

    # Add authors (deduplicated to avoid PK violation)
    seen_authors = set()
    position = 0
    for author_name in authors:
        normalised = author_name.strip()
        if normalised.lower() in seen_authors:
            continue
        seen_authors.add(normalised.lower())

        creator = _find_or_create_creator(session, author_name)
        item_creator = ItemCreator(
            item_id=item.id,
            creator_id=creator.id,
            role="author",
            position=position,
        )
        session.add(item_creator)
        position += 1

    return item


def _find_by_title_and_author(
    session: Session,
    title: str,
    authors: list[str],
) -> Item | None:
    """
    Find an existing item by matching title and first author.

    This handles cases where we have the same book in different formats
    (e.g., epub and mobi) but no ISBN to match on.
    """
    if not title:
        return None

    # Normalise title for comparison (case-insensitive, strip whitespace)
    normalised_title = title.strip().lower()

    # Find items with matching title
    candidates = session.query(Item).filter(
        Item.title.ilike(normalised_title)
    ).all()

    if not candidates:
        return None

    # If we have authors, try to match on first author too
    if authors:
        first_author = authors[0].strip().lower()

        for candidate in candidates:
            # Get the candidate's authors
            candidate_creators = (
                session.query(Creator)
                .join(ItemCreator)
                .filter(
                    ItemCreator.item_id == candidate.id,
                    ItemCreator.role == "author",
                )
                .order_by(ItemCreator.position)
                .all()
            )

            if candidate_creators:
                candidate_first_author = candidate_creators[0].name.strip().lower()
                if candidate_first_author == first_author:
                    return candidate

        # No author match found
        return None

    # No authors provided - only match if there's exactly one candidate
    # to avoid false positives with common titles
    if len(candidates) == 1:
        return candidates[0]

    return None


def _find_or_create_creator(session: Session, name: str) -> Creator:
    """Find an existing creator or create a new one."""
    # Normalise name for comparison
    normalised = name.strip()

    existing = session.query(Creator).filter(Creator.name == normalised).first()
    if existing:
        return existing

    # Generate sort name (Last, First)
    sort_name = _generate_sort_name(normalised)

    creator = Creator(name=normalised, sort_name=sort_name)
    session.add(creator)
    session.flush()

    return creator


def _generate_sort_title(title: str) -> str:
    """Generate a sort-friendly title (without leading articles)."""
    if not title:
        return ""

    lower = title.lower()
    for article in ["the ", "a ", "an "]:
        if lower.startswith(article):
            return title[len(article):].strip()

    return title


def _generate_sort_name(name: str) -> str:
    """Generate a sort-friendly author name (Last, First)."""
    if not name:
        return ""

    # Already in "Last, First" format
    if ", " in name:
        return name

    # Split on last space
    parts = name.rsplit(" ", 1)
    if len(parts) == 2:
        return f"{parts[1]}, {parts[0]}"

    return name


def _title_from_filename(filename: str) -> str:
    """Extract a title from a filename when no metadata is available."""
    # Remove extension
    name = Path(filename).stem

    # Remove common cruft patterns
    cruft_patterns = [
        r"\[.*?\]",  # [anything in brackets]
        r"\(.*?\)",  # (anything in parens) - be careful, might remove valid info
        r"V413HAV",
        r"StormRG",
        r"BBS",
        r"eBook-\w+",
        r"\.pdf$",
        r"\.epub$",
        r"\.mobi$",
    ]

    import re
    for pattern in cruft_patterns:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE)

    # Clean up whitespace and punctuation
    name = " ".join(name.split())
    name = name.strip(" .-_")

    return name if name else "Untitled"


