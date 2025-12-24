"""File scanner for discovering and cataloguing source files."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn
from sqlalchemy import select
from sqlalchemy.orm import Session

from librarian.db.models import SourceFile
from librarian.inspector.checksum import calculate_checksums
from librarian.inspector.formats import EXTENSION_MAP, detect_format
from librarian.inspector.metadata import ExtractedMetadata, extract_metadata

console = Console()


def _sanitise_for_json(value: Any) -> Any:
    """Remove null bytes and other problematic characters from values for JSON storage."""
    if isinstance(value, str):
        # Remove null bytes and other control characters that break PostgreSQL JSON
        # Also strip control characters (ASCII 0-31 except tab, newline, carriage return)
        result = value.replace("\x00", "").replace("\u0000", "")
        # Remove other problematic control characters
        result = "".join(
            char for char in result
            if ord(char) >= 32 or char in "\t\n\r"
        )
        return result
    elif isinstance(value, bytes):
        # Convert bytes to string, removing null bytes
        return value.decode("utf-8", errors="replace").replace("\x00", "")
    elif isinstance(value, list):
        return [_sanitise_for_json(v) for v in value]
    elif isinstance(value, dict):
        return {k: _sanitise_for_json(v) for k, v in value.items()}
    return value


@dataclass
class ScannedFile:
    """Result of scanning a single file."""

    path: Path
    filename: str
    format: str
    size_bytes: int
    checksum_md5: str
    checksum_sha256: str
    metadata: ExtractedMetadata


def find_library_files(root: Path) -> Iterator[Path]:
    """Find all supported files in a directory tree."""
    extensions = set(EXTENSION_MAP.keys())
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in extensions:
            yield path


def scan_file(file_path: Path) -> ScannedFile | None:
    """Scan a single file and extract all available information."""
    file_format = detect_format(file_path)
    if not file_format:
        return None

    try:
        size_bytes = file_path.stat().st_size
        md5, sha256 = calculate_checksums(file_path)
        metadata = extract_metadata(file_path, file_format)

        return ScannedFile(
            path=file_path,
            filename=file_path.name,
            format=file_format,
            size_bytes=size_bytes,
            checksum_md5=md5,
            checksum_sha256=sha256,
            metadata=metadata,
        )
    except Exception as e:
        console.print(f"[red]Error scanning {file_path}: {e}[/red]")
        return None


def scan_source_library(
    session: Session,
    source_root: Path,
    batch_size: int = 50,
) -> tuple[int, int, int]:
    """
    Scan source library and record files in the database.

    Returns: (total_files, new_files, skipped_files)
    """
    # First, count total files for progress bar
    console.print(f"[yellow]Counting files in {source_root}...[/yellow]")
    all_files = list(find_library_files(source_root))
    total_files = len(all_files)
    console.print(f"[green]Found {total_files} files to scan[/green]")

    new_files = 0
    skipped_files = 0
    batch: list[SourceFile] = []

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Scanning files", total=total_files)

        for file_path in all_files:
            progress.advance(task)

            # Check if already scanned
            existing = session.execute(
                select(SourceFile).where(SourceFile.source_path == str(file_path))
            ).scalar_one_or_none()

            if existing:
                skipped_files += 1
                continue

            # Scan the file
            scanned = scan_file(file_path)
            if not scanned:
                skipped_files += 1
                continue

            # Create database record with sanitised metadata
            metadata_dict = _sanitise_for_json({
                "title": scanned.metadata.title,
                "authors": scanned.metadata.authors,
                "isbns": scanned.metadata.isbns,  # All ISBNs found
                "isbn": scanned.metadata.isbn,  # First ISBN-10 (legacy)
                "isbn13": scanned.metadata.isbn13,  # First ISBN-13 (legacy)
                "description": scanned.metadata.description,
                "publisher": scanned.metadata.publisher,
                "publish_date": scanned.metadata.publish_date,
                "language": scanned.metadata.language,
                "subjects": scanned.metadata.subjects,
                "series": scanned.metadata.series,
                "series_index": scanned.metadata.series_index,
            })

            source_file = SourceFile(
                source_path=str(scanned.path),
                filename=scanned.filename,
                format=scanned.format,
                size_bytes=scanned.size_bytes,
                checksum_md5=scanned.checksum_md5,
                checksum_sha256=scanned.checksum_sha256,
                status="pending",
                extracted_metadata=metadata_dict,
                scanned_at=datetime.now(),
            )
            batch.append(source_file)
            new_files += 1

            # Commit in batches
            if len(batch) >= batch_size:
                session.add_all(batch)
                session.commit()
                batch = []

        # Commit remaining
        if batch:
            session.add_all(batch)
            session.commit()

    return total_files, new_files, skipped_files


def identify_duplicates(session: Session) -> int:
    """
    Identify duplicate files by checksum and mark them.

    Returns: number of duplicates marked
    """
    from sqlalchemy import func

    console.print("[yellow]Identifying duplicates by checksum...[/yellow]")

    # Find all checksums that appear more than once
    duplicate_checksums = (
        session.execute(
            select(SourceFile.checksum_md5)
            .where(SourceFile.status == "pending")
            .group_by(SourceFile.checksum_md5)
            .having(func.count(SourceFile.id) > 1)
        )
        .scalars()
        .all()
    )

    console.print(f"[blue]Found {len(duplicate_checksums)} checksums with duplicates[/blue]")

    duplicates_marked = 0

    # Process one checksum at a time to avoid parameter limits
    for checksum in duplicate_checksums:
        # Get all files with this checksum
        files = (
            session.execute(
                select(SourceFile)
                .where(SourceFile.checksum_md5 == checksum)
                .where(SourceFile.status == "pending")
                .order_by(SourceFile.id)
            )
            .scalars()
            .all()
        )

        if len(files) <= 1:
            continue

        # Keep the best one, mark rest as duplicates
        primary = _select_best_copy(files)

        for f in files:
            if f.id != primary.id:
                f.status = "duplicate"
                f.duplicate_of_id = primary.id
                duplicates_marked += 1

        # Commit each group to avoid building up too many changes
        session.commit()

    console.print(f"[green]Marked {duplicates_marked} files as duplicates[/green]")
    return duplicates_marked


def _select_best_copy(files: list[SourceFile]) -> SourceFile:
    """
    Select the best copy from a group of duplicates.

    Prefers files with:
    1. More extracted metadata (has title, authors)
    2. EPUB format over others
    3. Cleaner filename (shorter, no cruft)
    """

    def score(f: SourceFile) -> tuple[int, int, int]:
        meta = f.extracted_metadata or {}
        has_title = 1 if meta.get("title") else 0
        has_authors = 1 if meta.get("authors") else 0
        format_score = {"epub": 3, "pdf": 2, "mobi": 1}.get(f.format, 0)
        # Shorter filenames are often cleaner
        name_score = -len(f.filename)
        return (has_title + has_authors, format_score, name_score)

    return max(files, key=score)
