"""Processing pipeline for migrating source files to the library."""

import asyncio
from dataclasses import dataclass

from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn
from sqlalchemy import select
from sqlalchemy.orm import Session

from librarian.classifier import classify
from librarian.config import settings
from librarian.db.models import SourceFile
from librarian.enricher import enrich_by_isbn, enrich_by_title_author
from librarian.filer import file_item

console = Console()


@dataclass
class ProcessingStats:
    """Statistics from a processing run."""

    total: int = 0
    processed: int = 0
    migrated: int = 0
    failed: int = 0
    needs_review: int = 0
    skipped: int = 0


async def process_file(
    session: Session,
    source_file: SourceFile,
    dry_run: bool = False,
) -> str:
    """
    Process a single source file through the full pipeline.

    Returns status: "migrated", "needs_review", "failed"
    """
    extracted = source_file.extracted_metadata or {}

    # Prepare Calibre settings
    calibre_db_path = settings.calibre_library / "metadata.db" if settings.enable_calibre else None

    # Try to enrich by ISBN first
    isbn = extracted.get("isbn13") or extracted.get("isbn")

    if isbn:
        enriched = await enrich_by_isbn(
            isbn,
            enable_oclc=settings.enable_oclc,
            enable_openlibrary=settings.enable_openlibrary,
            enable_google_books=settings.enable_google_books,
            enable_librarything=settings.enable_librarything,
            librarything_api_key=settings.librarything_api_key,
            enable_calibre=settings.enable_calibre,
            calibre_db_path=calibre_db_path,
        )
    else:
        # Fall back to title/author search
        title = extracted.get("title")
        authors = extracted.get("authors", [])
        author = authors[0] if authors else None

        if title:
            enriched = await enrich_by_title_author(
                title,
                author,
                enable_oclc=settings.enable_oclc,
                enable_openlibrary=settings.enable_openlibrary,
                enable_google_books=settings.enable_google_books,
                enable_librarything=settings.enable_librarything,
                librarything_api_key=settings.librarything_api_key,
                enable_calibre=settings.enable_calibre,
                calibre_db_path=calibre_db_path,
                filename=source_file.filename,
            )
        else:
            # No ISBN or title - try Calibre by filename only
            from librarian.enricher import EnrichedMetadata
            from librarian.enricher.calibre import lookup_by_filename

            enriched = EnrichedMetadata(
                title=extracted.get("title"),
                authors=extracted.get("authors", []),
            )

            # Try Calibre filename lookup as last resort
            if settings.enable_calibre and calibre_db_path and calibre_db_path.exists():
                calibre_match = lookup_by_filename(calibre_db_path, source_file.filename)
                if calibre_match:
                    enriched.title = calibre_match.title
                    enriched.authors = calibre_match.authors
                    if calibre_match.isbn:
                        clean_isbn = calibre_match.isbn.replace("-", "").replace(" ", "")
                        if len(clean_isbn) == 13:
                            enriched.isbn13 = clean_isbn
                        elif len(clean_isbn) == 10:
                            enriched.isbn = clean_isbn
                    if calibre_match.series:
                        enriched.series = calibre_match.series
                        enriched.series_number = calibre_match.series_index
                    if calibre_match.tags:
                        enriched.subjects = calibre_match.tags
                    enriched.sources.append("calibre")

    # Classify
    classification = classify(enriched)

    # Check if we should auto-file or queue for review
    if classification.needs_review or classification.confidence < settings.confidence_threshold:
        source_file.status = "pending"  # Keep pending for review
        source_file.extracted_metadata = {
            **extracted,
            "_enriched": {
                "title": enriched.title,
                "authors": enriched.authors,
                "ddc": enriched.ddc,
                "subjects": enriched.subjects[:5] if enriched.subjects else [],
                "confidence": enriched.confidence,
            },
            "_classification": {
                "ddc": classification.ddc,
                "confidence": classification.confidence,
                "needs_review": True,
            },
        }
        return "needs_review"

    # File the item
    item, file_record = await file_item(
        session=session,
        source_file=source_file,
        enriched=enriched,
        classification=classification,
        dry_run=dry_run,
    )

    if item and file_record:
        return "migrated"
    else:
        return "failed"


def run_migration(
    session: Session,
    batch_size: int = 10,
    dry_run: bool = False,
    limit: int | None = None,
) -> ProcessingStats:
    """
    Run the migration pipeline on pending source files.

    Args:
        session: Database session
        batch_size: Number of files to process per batch
        dry_run: If True, don't actually copy files or update database
        limit: Maximum number of files to process (None for all)

    Returns:
        ProcessingStats with results
    """
    stats = ProcessingStats()

    # Get pending files
    query = (
        select(SourceFile)
        .where(SourceFile.status == "pending")
        .order_by(SourceFile.id)
    )

    if limit:
        query = query.limit(limit)

    pending_files = session.execute(query).scalars().all()
    stats.total = len(pending_files)

    if stats.total == 0:
        console.print("[yellow]No pending files to process[/yellow]")
        return stats

    console.print(f"[blue]Processing {stats.total} files...[/blue]")

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Processing", total=stats.total)

        for i in range(0, len(pending_files), batch_size):
            batch = pending_files[i:i + batch_size]

            # Process batch asynchronously
            results = asyncio.run(_process_batch(session, batch, dry_run))

            for result in results:
                stats.processed += 1
                if result == "migrated":
                    stats.migrated += 1
                elif result == "needs_review":
                    stats.needs_review += 1
                elif result == "failed":
                    stats.failed += 1
                else:
                    stats.skipped += 1

                progress.advance(task)

            # Commit after each batch
            if not dry_run:
                session.commit()

    return stats


async def _process_batch(
    session: Session,
    files: list[SourceFile],
    dry_run: bool,
) -> list[str]:
    """Process a batch of files concurrently."""
    tasks = [process_file(session, f, dry_run) for f in files]
    return await asyncio.gather(*tasks, return_exceptions=False)
