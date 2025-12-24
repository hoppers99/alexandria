"""Command-line interface for The Librarian."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from sqlalchemy import func, select

from librarian import __version__

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="librarian")
def main() -> None:
    """The Librarian - Cataloguing engine for Bibliotheca Alexandria."""
    pass


@main.command()
def process() -> None:
    """Process all items in the Returns folder."""
    console.print("[yellow]Processing Returns folder...[/yellow]")
    # TODO: Implement
    console.print("[red]Not yet implemented[/red]")


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--isbn", help="ISBN hint to speed up identification")
@click.option("--title", help="Title hint")
@click.option("--author", help="Author hint")
def add(path: str, isbn: str | None, title: str | None, author: str | None) -> None:
    """Add a specific file to the library."""
    console.print(f"[yellow]Adding: {path}[/yellow]")
    if isbn:
        console.print(f"  ISBN hint: {isbn}")
    if title:
        console.print(f"  Title hint: {title}")
    if author:
        console.print(f"  Author hint: {author}")
    # TODO: Implement
    console.print("[red]Not yet implemented[/red]")


@main.command()
@click.argument("path", type=click.Path(exists=True))
def identify(path: str) -> None:
    """Identify a file without filing it."""
    console.print(f"[yellow]Identifying: {path}[/yellow]")
    # TODO: Implement
    console.print("[red]Not yet implemented[/red]")


@main.command()
@click.option("--isbn", help="Look up by ISBN")
@click.option("--title", help="Look up by title")
@click.option("--author", help="Look up by author")
def lookup(isbn: str | None, title: str | None, author: str | None) -> None:
    """Search for metadata manually."""
    if isbn:
        console.print(f"[yellow]Looking up ISBN: {isbn}[/yellow]")
    elif title or author:
        console.print(f"[yellow]Looking up: {title or ''} by {author or ''}[/yellow]")
    else:
        console.print("[red]Please provide --isbn, --title, or --author[/red]")
        return
    # TODO: Implement
    console.print("[red]Not yet implemented[/red]")


@main.command()
def seed() -> None:
    """Seed the database with initial classification data."""
    from librarian.db.seed import seed_classifications
    from librarian.db.session import get_session

    console.print("[yellow]Seeding classifications...[/yellow]")

    with get_session() as session:
        added = seed_classifications(session)

    if added > 0:
        console.print(f"[green]Added {added} classifications[/green]")
    else:
        console.print("[blue]Classifications already seeded[/blue]")


@main.command()
def check() -> None:
    """Verify library integrity (missing files, orphan records)."""
    console.print("[yellow]Checking library integrity...[/yellow]")
    # TODO: Implement
    console.print("[red]Not yet implemented[/red]")


@main.command()
def duplicates() -> None:
    """Find and report duplicate files."""
    console.print("[yellow]Scanning for duplicates...[/yellow]")
    # TODO: Implement
    console.print("[red]Not yet implemented[/red]")


@main.command()
@click.option("--limit", default=20, type=int, help="Number of items to show")
@click.option("--skip", default=0, type=int, help="Number of items to skip")
@click.option("--format", "file_format", default=None, help="Filter by format (epub, pdf, mobi)")
def review(limit: int, skip: int, file_format: str | None) -> None:
    """Review items that need manual classification."""
    import asyncio

    from librarian.classifier import classify
    from librarian.config import settings
    from librarian.db.models import SourceFile
    from librarian.db.session import get_session
    from librarian.enricher import enrich_by_isbn, enrich_by_title_author
    from librarian.filer import file_item

    with get_session() as session:
        # Count total pending
        query = session.query(SourceFile).filter(SourceFile.status == "pending")
        if file_format:
            query = query.filter(SourceFile.format == file_format.lower())

        total_pending = query.count()

        if total_pending == 0:
            console.print("[green]No files pending review![/green]")
            return

        console.print(f"[bold blue]Review Queue[/bold blue] ({total_pending} files pending)")
        console.print()

        # Get batch of pending files
        pending_files = query.order_by(SourceFile.id).offset(skip).limit(limit).all()

        for idx, sf in enumerate(pending_files, start=skip + 1):
            meta = sf.extracted_metadata or {}
            enriched_data = meta.get("_enriched", {})
            classif_data = meta.get("_classification", {})

            # Display file info
            console.print(f"[bold cyan]━━━ {idx}/{total_pending} ━━━[/bold cyan]")
            console.print()
            console.print(f"[bold]Filename:[/bold] {sf.filename}")
            # Use file:// URL with proper encoding for clickable path
            from urllib.parse import quote
            file_url = f"file://{quote(sf.source_path)}"
            console.print(f"[bold]Path:[/bold] [link={file_url}]{sf.source_path}[/link]")
            console.print(f"[bold]Format:[/bold] {sf.format.upper()}  [bold]Size:[/bold] {sf.size_bytes / 1024 / 1024:.1f} MB")
            console.print()

            # Extracted metadata
            console.print("[yellow]Extracted metadata:[/yellow]")
            console.print(f"  Title: {meta.get('title', '[none]')}")
            console.print(f"  Authors: {', '.join(meta.get('authors', [])) or '[none]'}")
            console.print(f"  ISBN: {meta.get('isbn') or meta.get('isbn13') or '[none]'}")
            if meta.get("series"):
                console.print(f"  Series: {meta.get('series')} #{meta.get('series_index', '?')}")

            # Enrichment attempt results
            if enriched_data:
                console.print()
                console.print("[yellow]Enrichment attempt:[/yellow]")
                console.print(f"  Title: {enriched_data.get('title', '[not found]')}")
                console.print(f"  Authors: {', '.join(enriched_data.get('authors', [])) or '[not found]'}")
                console.print(f"  DDC: {enriched_data.get('ddc', '[none]')}")
                console.print(f"  Subjects: {', '.join(enriched_data.get('subjects', []))[:80] or '[none]'}")

            # Classification result
            if classif_data:
                console.print()
                console.print("[yellow]Classification:[/yellow]")
                console.print(f"  DDC: {classif_data.get('ddc', '[none]')}")
                console.print(f"  Confidence: {classif_data.get('confidence', 0):.0%}")

            console.print()

            # Interactive prompt
            while True:
                console.print("[bold]Actions:[/bold]")
                console.print("  [bold cyan]s[/bold cyan] Skip to next")
                console.print("  [bold cyan]i[/bold cyan] Search by ISBN")
                console.print("  [bold cyan]t[/bold cyan] Search by title/author")
                console.print("  [bold cyan]f[/bold cyan] File with current metadata (force)")
                console.print("  [bold cyan]d[/bold cyan] Mark as duplicate/skip permanently")
                console.print("  [bold cyan]o[/bold cyan] Open file location")
                console.print("  [bold cyan]q[/bold cyan] Quit review")
                console.print()

                action = click.prompt("Action", type=str, default="s").strip().lower()

                if action == "q":
                    console.print("[yellow]Exiting review.[/yellow]")
                    return

                elif action == "s":
                    break  # Next file

                elif action == "o":
                    # Open file location in Finder/file manager
                    import subprocess
                    import sys

                    file_path = Path(sf.source_path)
                    if sys.platform == "darwin":
                        subprocess.run(["open", "-R", str(file_path)])
                    elif sys.platform == "linux":
                        subprocess.run(["xdg-open", str(file_path.parent)])
                    else:
                        console.print(f"[dim]Path: {file_path}[/dim]")
                    continue

                elif action == "i":
                    isbn = click.prompt("Enter ISBN", type=str)
                    console.print(f"[yellow]Searching for ISBN: {isbn}...[/yellow]")

                    enriched = asyncio.run(enrich_by_isbn(
                        isbn,
                        enable_oclc=settings.enable_oclc,
                        enable_openlibrary=settings.enable_openlibrary,
                        enable_google_books=settings.enable_google_books,
                        enable_librarything=settings.enable_librarything,
                        librarything_api_key=settings.librarything_api_key,
                    ))

                    if enriched.title:
                        console.print(f"[green]Found: {enriched.title}[/green]")
                        console.print(f"  Authors: {', '.join(enriched.authors or [])}")
                        console.print(f"  DDC: {enriched.ddc_normalised or '[none]'}")

                        if click.confirm("File with this metadata?", default=True):
                            classification = classify(enriched)
                            item, file_record = asyncio.run(file_item(
                                session=session,
                                source_file=sf,
                                enriched=enriched,
                                classification=classification,
                            ))
                            if item:
                                session.commit()
                                console.print(f"[green]Filed as: {item.title}[/green]")
                                break
                            else:
                                console.print("[red]Filing failed[/red]")
                    else:
                        console.print("[red]No results found for that ISBN[/red]")
                    continue

                elif action == "t":
                    title = click.prompt("Enter title", type=str)
                    author = click.prompt("Enter author (optional)", type=str, default="")

                    console.print(f"[yellow]Searching for: {title}...[/yellow]")

                    enriched = asyncio.run(enrich_by_title_author(
                        title,
                        author if author else None,
                        enable_oclc=settings.enable_oclc,
                        enable_openlibrary=settings.enable_openlibrary,
                        enable_google_books=settings.enable_google_books,
                        enable_librarything=settings.enable_librarything,
                        librarything_api_key=settings.librarything_api_key,
                    ))

                    if enriched.title:
                        console.print(f"[green]Found: {enriched.title}[/green]")
                        console.print(f"  Authors: {', '.join(enriched.authors or [])}")
                        console.print(f"  DDC: {enriched.ddc_normalised or '[none]'}")

                        if click.confirm("File with this metadata?", default=True):
                            classification = classify(enriched)
                            item, file_record = asyncio.run(file_item(
                                session=session,
                                source_file=sf,
                                enriched=enriched,
                                classification=classification,
                            ))
                            if item:
                                session.commit()
                                console.print(f"[green]Filed as: {item.title}[/green]")
                                break
                            else:
                                console.print("[red]Filing failed[/red]")
                    else:
                        console.print("[red]No results found[/red]")
                    continue

                elif action == "f":
                    # Force file with whatever metadata we have
                    from librarian.enricher import EnrichedMetadata

                    enriched = EnrichedMetadata(
                        title=meta.get("title") or enriched_data.get("title"),
                        authors=meta.get("authors") or enriched_data.get("authors", []),
                        subjects=enriched_data.get("subjects", []),
                    )

                    if not enriched.title:
                        console.print("[red]No title available - cannot file[/red]")
                        continue

                    classification = classify(enriched)
                    # Force confidence for filing
                    classification.confidence = 1.0
                    classification.needs_review = False

                    console.print(f"[yellow]Filing as: {enriched.title}[/yellow]")
                    console.print(f"  Fiction: {classification.is_fiction}")
                    console.print(f"  DDC: {classification.ddc or '[none - will use 000]'}")

                    if click.confirm("Proceed?", default=True):
                        item, file_record = asyncio.run(file_item(
                            session=session,
                            source_file=sf,
                            enriched=enriched,
                            classification=classification,
                        ))
                        if item:
                            session.commit()
                            console.print("[green]Filed![/green]")
                            break
                        else:
                            console.print("[red]Filing failed[/red]")
                    continue

                elif action == "d":
                    sf.status = "skipped"
                    session.commit()
                    console.print("[yellow]Marked as skipped[/yellow]")
                    break

                else:
                    console.print("[red]Unknown action[/red]")
                    continue

        console.print()
        console.print(f"[blue]Reviewed {len(pending_files)} files. {total_pending - len(pending_files) - skip} remaining.[/blue]")


@main.group()
def migrate() -> None:
    """Migration commands for importing existing library."""
    pass


@migrate.command(name="scan")
@click.argument("source", type=click.Path(exists=True))
@click.option("--identify-duplicates/--no-identify-duplicates", default=True,
              help="Identify and mark duplicate files after scanning")
def migrate_scan(source: str, identify_duplicates: bool) -> None:
    """Scan source library and build migration manifest.

    SOURCE is the path to the library folder to scan for files to migrate.
    """
    from librarian.db.session import get_session
    from librarian.inspector.scanner import (
        identify_duplicates as do_identify_duplicates,
    )
    from librarian.inspector.scanner import (
        scan_source_library,
    )

    source_path = Path(source)

    console.print(f"[bold blue]Scanning source library: {source_path}[/bold blue]")

    with get_session() as session:
        total, new, skipped = scan_source_library(session, source_path)

        console.print()
        console.print("[green]Scan complete![/green]")
        console.print(f"  Total files found: {total}")
        console.print(f"  New files added: {new}")
        console.print(f"  Skipped (already scanned): {skipped}")

        if identify_duplicates and new > 0:
            console.print()
            duplicates_found = do_identify_duplicates(session)
            console.print(f"  Duplicates identified: {duplicates_found}")


@migrate.command(name="rescan")
@click.option("--status", default="pending", help="Status of files to rescan (pending, failed, all)")
@click.option("--format", "file_format", default=None, help="Filter by format (epub, pdf, mobi)")
@click.option("--limit", default=None, type=int, help="Maximum number of files to rescan")
@click.option("--batch-size", default=50, type=int, help="Commit to database every N files")
def migrate_rescan(status: str, file_format: str | None, limit: int | None, batch_size: int) -> None:
    """Re-extract metadata for files that need it (uses improved extraction)."""

    from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn

    from librarian.db.models import SourceFile
    from librarian.db.session import get_session
    from librarian.inspector.metadata import extract_metadata
    from librarian.inspector.scanner import _sanitise_for_json

    filters = []
    if status != "all":
        filters.append(f"status={status}")
    if file_format:
        filters.append(f"format={file_format}")
    filter_str = f" ({', '.join(filters)})" if filters else ""

    console.print(f"[bold blue]Rescanning files with improved metadata extraction{filter_str}[/bold blue]")

    with get_session() as session:
        if status == "all":
            query = session.query(SourceFile)
        else:
            query = session.query(SourceFile).filter(SourceFile.status == status)

        if file_format:
            query = query.filter(SourceFile.format == file_format.lower())

        if limit:
            query = query.limit(limit)

        files = query.all()
        total = len(files)

        if total == 0:
            console.print(f"[yellow]No {status} files to rescan[/yellow]")
            return

        console.print(f"[blue]Found {total} files to rescan (committing every {batch_size} files)[/blue]")

        updated = 0
        errors = 0
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Rescanning", total=total)

            for idx, sf in enumerate(files):
                try:
                    file_path = Path(sf.source_path)
                    if file_path.exists():
                        metadata = extract_metadata(file_path, sf.format)

                        # Update extracted metadata (sanitise to remove null bytes)
                        old_meta = sf.extracted_metadata or {}
                        new_meta = _sanitise_for_json({
                            "title": metadata.title,
                            "authors": metadata.authors,
                            "isbns": metadata.isbns,
                            "isbn": metadata.isbn,
                            "isbn13": metadata.isbn13,
                            "description": metadata.description,
                            "publisher": metadata.publisher,
                            "publish_date": metadata.publish_date,
                            "language": metadata.language,
                            "subjects": metadata.subjects,
                            "series": metadata.series,
                            "series_index": metadata.series_index,
                        })

                        # Preserve enrichment data if any
                        if "_enriched" in old_meta:
                            new_meta["_enriched"] = old_meta["_enriched"]
                        if "_classification" in old_meta:
                            new_meta["_classification"] = old_meta["_classification"]

                        sf.extracted_metadata = new_meta
                        updated += 1
                except Exception as e:
                    console.print(f"[red]Error rescanning {sf.filename}: {e}[/red]")
                    errors += 1

                progress.advance(task)

                # Commit in batches to avoid losing all progress on error
                if (idx + 1) % batch_size == 0:
                    session.commit()

            # Commit any remaining changes
            session.commit()

        console.print()
        console.print("[green]Rescan complete![/green]")
        console.print(f"  Files updated: {updated}/{total}")
        if errors > 0:
            console.print(f"  [yellow]Errors: {errors}[/yellow]")


@migrate.command(name="calibre")
@click.option("--limit", default=None, type=int, help="Maximum number of files to process")
def migrate_calibre(limit: int | None) -> None:
    """Enrich pending files with metadata from Calibre database."""
    from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn

    from librarian.config import settings
    from librarian.db.models import SourceFile
    from librarian.db.session import get_session
    from librarian.enricher.calibre import lookup_by_path, lookup_by_title_author

    calibre_db = settings.calibre_library / "metadata.db"

    if not calibre_db.exists():
        console.print(f"[red]Calibre database not found: {calibre_db}[/red]")
        return

    console.print("[bold blue]Enriching pending files from Calibre[/bold blue]")
    console.print(f"  Calibre DB: {calibre_db}")

    with get_session() as session:
        query = session.query(SourceFile).filter(SourceFile.status == "pending")
        if limit:
            query = query.limit(limit)

        files = query.all()
        total = len(files)

        if total == 0:
            console.print("[yellow]No pending files to enrich[/yellow]")
            return

        console.print(f"[blue]Found {total} pending files[/blue]")

        enriched_count = 0
        isbn_count = 0

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Enriching", total=total)

            for sf in files:
                file_path = Path(sf.source_path)
                calibre_book = None

                # Try path-based lookup first (if file is in Calibre library)
                if str(file_path).startswith(str(settings.calibre_library)):
                    calibre_book = lookup_by_path(
                        calibre_db, file_path, settings.calibre_library
                    )

                # Fall back to title/author lookup
                if not calibre_book:
                    meta = sf.extracted_metadata or {}
                    title = meta.get("title")
                    authors = meta.get("authors", [])

                    if title:
                        calibre_book = lookup_by_title_author(
                            calibre_db, title, authors[0] if authors else None
                        )

                if calibre_book:
                    # Update metadata with Calibre data
                    meta = sf.extracted_metadata or {}

                    # Add Calibre data (prefer existing if present)
                    if not meta.get("title") and calibre_book.title:
                        meta["title"] = calibre_book.title
                    if not meta.get("authors") and calibre_book.authors:
                        meta["authors"] = calibre_book.authors
                    if not meta.get("series") and calibre_book.series:
                        meta["series"] = calibre_book.series
                        meta["series_index"] = calibre_book.series_index
                    if not meta.get("publisher") and calibre_book.publisher:
                        meta["publisher"] = calibre_book.publisher
                    if not meta.get("description") and calibre_book.description:
                        meta["description"] = calibre_book.description
                    if not meta.get("language") and calibre_book.language:
                        meta["language"] = calibre_book.language

                    # Add ISBNs from Calibre
                    isbns = meta.get("isbns", [])
                    if calibre_book.isbn and calibre_book.isbn not in isbns:
                        isbns.append(calibre_book.isbn)
                        isbn_count += 1
                    for id_type, id_val in calibre_book.identifiers.items():
                        if id_type == "isbn" and id_val not in isbns:
                            isbns.append(id_val)
                            isbn_count += 1
                    if isbns:
                        meta["isbns"] = isbns
                        meta["isbn"] = next((i for i in isbns if len(i) == 10), None)
                        meta["isbn13"] = next((i for i in isbns if len(i) == 13), None)

                    # Add tags as subjects if not present
                    if not meta.get("subjects") and calibre_book.tags:
                        meta["subjects"] = calibre_book.tags

                    # Store Calibre source info
                    meta["_calibre"] = {
                        "id": calibre_book.id,
                        "path": calibre_book.path,
                    }

                    sf.extracted_metadata = meta
                    enriched_count += 1

                progress.advance(task)

            session.commit()

        console.print()
        console.print("[green]Calibre enrichment complete![/green]")
        console.print(f"  Files enriched: {enriched_count}/{total}")
        console.print(f"  ISBNs added: {isbn_count}")


@migrate.command(name="run")
@click.option("--batch-size", default=10, help="Number of items to process per batch")
@click.option("--limit", default=None, type=int, help="Maximum number of files to process")
@click.option("--dry-run", is_flag=True, help="Show what would be done without doing it")
def migrate_run(batch_size: int, limit: int | None, dry_run: bool) -> None:
    """Run migration from source library to new structure."""
    from librarian.db.session import get_session
    from librarian.pipeline import run_migration

    console.print("[bold blue]Running migration[/bold blue]")
    console.print(f"  Batch size: {batch_size}")
    if limit:
        console.print(f"  Limit: {limit} files")
    if dry_run:
        console.print("[yellow]  Dry run mode - no files will be copied[/yellow]")
    console.print()

    with get_session() as session:
        stats = run_migration(
            session=session,
            batch_size=batch_size,
            dry_run=dry_run,
            limit=limit,
        )

    console.print()
    console.print("[bold green]Migration complete![/bold green]")
    console.print(f"  Total processed: {stats.processed}")
    console.print(f"  Successfully migrated: {stats.migrated}")
    console.print(f"  Needs review: {stats.needs_review}")
    console.print(f"  Failed: {stats.failed}")
    console.print(f"  Skipped: {stats.skipped}")


@migrate.command(name="status")
def migrate_status() -> None:
    """Show migration progress."""
    from librarian.db.models import SourceFile
    from librarian.db.session import get_session

    with get_session() as session:
        # Get counts by status
        status_counts = dict(
            session.execute(
                select(SourceFile.status, func.count(SourceFile.id))
                .group_by(SourceFile.status)
            ).all()
        )

        # Get counts by format
        format_counts = dict(
            session.execute(
                select(SourceFile.format, func.count(SourceFile.id))
                .group_by(SourceFile.format)
                .order_by(func.count(SourceFile.id).desc())
            ).all()
        )

        # Get total size
        total_size = session.execute(
            select(func.sum(SourceFile.size_bytes))
        ).scalar() or 0

        # Display status table
        console.print()
        console.print("[bold blue]Migration Status[/bold blue]")
        console.print()

        status_table = Table(title="Files by Status")
        status_table.add_column("Status", style="cyan")
        status_table.add_column("Count", justify="right", style="green")

        total_files = 0
        for status in ["pending", "processing", "migrated", "duplicate", "failed", "skipped"]:
            count = status_counts.get(status, 0)
            total_files += count
            if count > 0:
                status_table.add_row(status.capitalize(), str(count))

        status_table.add_row("─" * 15, "─" * 8)
        status_table.add_row("Total", str(total_files))

        console.print(status_table)
        console.print()

        # Display format table
        format_table = Table(title="Files by Format")
        format_table.add_column("Format", style="cyan")
        format_table.add_column("Count", justify="right", style="green")

        for fmt, count in format_counts.items():
            format_table.add_row(fmt.upper(), str(count))

        console.print(format_table)
        console.print()

        # Display total size
        size_gb = total_size / (1024 ** 3)
        console.print(f"[bold]Total size:[/bold] {size_gb:.2f} GB")

        if total_files == 0:
            console.print()
            console.print("[yellow]No files scanned yet. Run 'librarian migrate scan' first.[/yellow]")


@main.command(name="process-edits")
@click.option("--dry-run", is_flag=True, help="Show what would be done without doing it")
@click.option("--limit", default=None, type=int, help="Maximum number of requests to process")
def process_edits(dry_run: bool, limit: int | None) -> None:
    """Process pending edit requests from the web UI."""
    from datetime import datetime

    from librarian.config import settings
    from librarian.db.models import EditRequest, Item
    from librarian.db.session import get_session

    console.print("[bold blue]Processing edit requests[/bold blue]")
    if dry_run:
        console.print("[yellow]  Dry run mode - no changes will be made[/yellow]")
    console.print()

    with get_session() as session:
        # Get pending requests
        query = session.query(EditRequest).filter(EditRequest.status == "pending")
        if limit:
            query = query.limit(limit)

        pending_requests = query.all()

        if not pending_requests:
            console.print("[green]No pending edit requests![/green]")
            return

        console.print(f"[blue]Found {len(pending_requests)} pending request(s)[/blue]")
        console.print()

        processed = 0
        succeeded = 0
        failed = 0

        for req in pending_requests:
            processed += 1
            console.print(f"[cyan]━━━ Request #{req.id} ({req.request_type}) ━━━[/cyan]")

            try:
                item = session.query(Item).filter(Item.id == req.item_id).first()
                if not item:
                    raise ValueError(f"Item {req.item_id} not found")

                console.print(f"  Item: {item.title}")

                if req.request_type in ("refile_fiction", "refile_nonfiction", "change_ddc"):
                    # Handle refile requests
                    success = _process_refile_request(
                        session=session,
                        req=req,
                        item=item,
                        library_root=settings.library_root,
                        author_format=settings.author_format,
                        dry_run=dry_run,
                    )
                elif req.request_type == "fix_author":
                    # Handle author fix requests
                    success = _process_author_fix_request(
                        session=session,
                        req=req,
                        item=item,
                        library_root=settings.library_root,
                        author_format=settings.author_format,
                        dry_run=dry_run,
                    )
                else:
                    console.print(f"  [yellow]Unknown request type: {req.request_type}[/yellow]")
                    success = False

                if success:
                    if not dry_run:
                        req.status = "completed"
                        req.processed_at = datetime.now()
                        session.commit()
                    console.print("  [green]✓ Completed[/green]")
                    succeeded += 1
                else:
                    failed += 1

            except Exception as e:
                console.print(f"  [red]✗ Error: {e}[/red]")
                if not dry_run:
                    req.status = "failed"
                    req.error_message = str(e)
                    req.processed_at = datetime.now()
                    session.commit()
                failed += 1

            console.print()

        console.print("[bold]Summary:[/bold]")
        console.print(f"  Processed: {processed}")
        console.print(f"  Succeeded: {succeeded}")
        console.print(f"  Failed: {failed}")


def _process_refile_request(
    session,
    req,
    item,
    library_root: Path,
    author_format: str,
    dry_run: bool,
) -> bool:
    """Process a refile request (move files to new location)."""
    from librarian.db.models import File
    from librarian.filer.naming import (
        DDC_CLASS_NAMES,
        ensure_unique_path,
        generate_filename,
        generate_folder_name,
    )
    from librarian.filer.transfer import copy_verify_remove

    request_data = req.request_data

    # Determine target location
    target_category = request_data.get("target_category")
    target_ddc = request_data.get("target_ddc")

    if target_category == "fiction":
        is_fiction = True
        ddc_code = None
        console.print("  Target: Fiction")
    elif target_category == "non-fiction" or target_ddc:
        is_fiction = False
        ddc_code = (target_ddc or item.classification_code or "000").zfill(3)[:3]
        top_level = ddc_code[0] + "00"
        class_name = DDC_CLASS_NAMES.get(top_level, "General")
        console.print(f"  Target: Non-Fiction/{ddc_code} - {class_name}")
    else:
        console.print("  [red]No target specified[/red]")
        return False

    # Get all files for this item
    files = session.query(File).filter(File.item_id == item.id).all()
    if not files:
        console.print("  [yellow]No files to move[/yellow]")
        return True

    # Get authors for path generation
    from librarian.db.models import Creator, ItemCreator
    creators = (
        session.query(Creator)
        .join(ItemCreator)
        .filter(ItemCreator.item_id == item.id, ItemCreator.role == "author")
        .order_by(ItemCreator.position)
        .all()
    )
    authors = [c.name for c in creators]

    # Generate folder name
    folder_name = generate_folder_name(
        title=item.title,
        authors=authors,
        series=item.series_name,
        series_index=float(item.series_index) if item.series_index else None,
        author_format=author_format,
    )

    # Determine target base path
    if is_fiction:
        target_base = library_root / "Fiction" / folder_name
    else:
        ddc_folder = f"{ddc_code} - {DDC_CLASS_NAMES.get(ddc_code[0] + '00', 'General')}"
        target_base = library_root / "Non-Fiction" / ddc_folder / folder_name

    console.print(f"  New location: {target_base.relative_to(library_root)}")

    # Move each file
    moved_files = []
    for file_record in files:
        old_path = library_root / file_record.file_path
        if not old_path.exists():
            console.print(f"  [yellow]File not found: {file_record.file_path}[/yellow]")
            continue

        # Generate new filename
        new_filename = generate_filename(
            title=item.title,
            authors=authors,
            series=item.series_name,
            series_index=float(item.series_index) if item.series_index else None,
            extension=file_record.format,
            author_format=author_format,
        )

        new_path = target_base / new_filename
        new_path = ensure_unique_path(new_path)

        console.print(f"  Moving: {old_path.name} -> {new_path.relative_to(library_root)}")

        if not dry_run:
            # Create target directory
            new_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy, verify, and remove (crash-safe move)
            success = copy_verify_remove(
                source=old_path,
                destination=new_path,
                expected_checksum=file_record.checksum_md5,
                cleanup_parents_up_to=library_root,
            )
            if not success:
                console.print(f"  [red]Failed to move {old_path.name}[/red]")
                return False

            # Update database record
            file_record.file_path = str(new_path.relative_to(library_root))
            moved_files.append((old_path, new_path))

    # Move cover if it exists
    if item.cover_path:
        old_cover = library_root / item.cover_path
        if old_cover.exists():
            new_cover = target_base / "cover.jpg"
            console.print(f"  Moving cover: {old_cover.name}")

            if not dry_run:
                new_cover.parent.mkdir(parents=True, exist_ok=True)
                # Covers don't have checksums, so calculate from source
                success = copy_verify_remove(
                    source=old_cover,
                    destination=new_cover,
                    cleanup_parents_up_to=library_root,
                )
                if success:
                    item.cover_path = str(new_cover.relative_to(library_root))
                else:
                    console.print("  [yellow]Warning: Cover move failed[/yellow]")

    # Update item classification
    if not dry_run:
        if is_fiction:
            # Store fiction status in identifiers
            identifiers = item.identifiers or {}
            identifiers["is_fiction"] = True
            item.identifiers = identifiers
            item.classification_code = None
        else:
            identifiers = item.identifiers or {}
            identifiers["is_fiction"] = False
            item.identifiers = identifiers
            item.classification_code = ddc_code

    return True


def _process_author_fix_request(
    session,
    req,
    item,
    library_root: Path,
    author_format: str,
    dry_run: bool,
) -> bool:
    """Process an author fix request (rename creator and optionally folders)."""
    from librarian.db.models import Creator, File, Item, ItemCreator
    from librarian.filer.naming import (
        DDC_CLASS_NAMES,
        ensure_unique_path,
        generate_filename,
        generate_folder_name,
    )
    from librarian.filer.transfer import copy_verify_remove

    request_data = req.request_data
    creator_id = request_data.get("creator_id")
    corrected_name = request_data.get("corrected_name")

    if not creator_id or not corrected_name:
        console.print("  [red]Missing creator_id or corrected_name[/red]")
        return False

    # Find the creator
    creator = session.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        console.print(f"  [red]Creator {creator_id} not found[/red]")
        return False

    old_name = creator.name
    console.print(f"  Renaming: '{old_name}' -> '{corrected_name}'")

    # Update creator record
    if not dry_run:
        creator.name = corrected_name
        # Update sort name
        parts = corrected_name.rsplit(" ", 1)
        if len(parts) == 2:
            creator.sort_name = f"{parts[1]}, {parts[0]}"
        else:
            creator.sort_name = corrected_name

    # Find all items by this creator that need folder renaming
    items_to_update = (
        session.query(Item)
        .join(ItemCreator)
        .filter(ItemCreator.creator_id == creator_id)
        .all()
    )

    console.print(f"  Found {len(items_to_update)} item(s) by this creator")

    for affected_item in items_to_update:
        # Get all authors for this item
        item_creators = (
            session.query(Creator)
            .join(ItemCreator)
            .filter(ItemCreator.item_id == affected_item.id, ItemCreator.role == "author")
            .order_by(ItemCreator.position)
            .all()
        )

        # Build author list with corrected name
        authors = []
        for c in item_creators:
            if c.id == creator_id:
                authors.append(corrected_name)
            else:
                authors.append(c.name)

        # Get files for this item
        files = session.query(File).filter(File.item_id == affected_item.id).all()
        if not files:
            continue

        # Check if any files have the old author name in the path
        needs_rename = False
        for f in files:
            if old_name.replace(" ", "_") in f.file_path or old_name in f.file_path:
                needs_rename = True
                break

        if not needs_rename:
            continue

        # Determine if fiction or non-fiction from file path
        first_file_path = files[0].file_path
        is_fiction = first_file_path.startswith("Fiction/")
        ddc_code = affected_item.classification_code

        # Generate new folder name
        new_folder_name = generate_folder_name(
            title=affected_item.title,
            authors=authors,
            series=affected_item.series_name,
            series_index=float(affected_item.series_index) if affected_item.series_index else None,
            author_format=author_format,
        )

        # Determine target base path
        if is_fiction:
            target_base = library_root / "Fiction" / new_folder_name
        else:
            ddc = (ddc_code or "000").zfill(3)[:3]
            ddc_folder = f"{ddc} - {DDC_CLASS_NAMES.get(ddc[0] + '00', 'General')}"
            target_base = library_root / "Non-Fiction" / ddc_folder / new_folder_name

        console.print(f"    Updating: {affected_item.title[:50]}")
        console.print(f"      -> {target_base.relative_to(library_root)}")

        # Move each file
        for file_record in files:
            old_path = library_root / file_record.file_path
            if not old_path.exists():
                continue

            new_filename = generate_filename(
                title=affected_item.title,
                authors=authors,
                series=affected_item.series_name,
                series_index=float(affected_item.series_index) if affected_item.series_index else None,
                extension=file_record.format,
                author_format=author_format,
            )

            new_path = target_base / new_filename
            new_path = ensure_unique_path(new_path)

            if not dry_run:
                new_path.parent.mkdir(parents=True, exist_ok=True)
                # Copy, verify, and remove (crash-safe move)
                success = copy_verify_remove(
                    source=old_path,
                    destination=new_path,
                    expected_checksum=file_record.checksum_md5,
                    cleanup_parents_up_to=library_root,
                )
                if success:
                    file_record.file_path = str(new_path.relative_to(library_root))
                else:
                    console.print(f"      [red]Failed to move {old_path.name}[/red]")

        # Move cover if it exists
        if affected_item.cover_path:
            old_cover = library_root / affected_item.cover_path
            if old_cover.exists():
                new_cover = target_base / "cover.jpg"
                if not dry_run:
                    new_cover.parent.mkdir(parents=True, exist_ok=True)
                    # Covers don't have checksums, so calculate from source
                    success = copy_verify_remove(
                        source=old_cover,
                        destination=new_cover,
                        cleanup_parents_up_to=library_root,
                    )
                    if success:
                        affected_item.cover_path = str(new_cover.relative_to(library_root))

    return True


def _cleanup_empty_dirs(path: Path, stop_at: Path) -> None:
    """Remove empty directories up to (but not including) stop_at."""
    while path != stop_at and path.is_dir():
        try:
            # Only remove if empty
            if not any(path.iterdir()):
                path.rmdir()
                path = path.parent
            else:
                break
        except OSError:
            break


@main.command(name="merge-duplicates")
@click.option("--dry-run", is_flag=True, help="Show what would be done without doing it")
@click.option("--limit", default=None, type=int, help="Maximum number of merges to perform")
def merge_duplicates(dry_run: bool, limit: int | None) -> None:
    """Find and merge duplicate items (same book in different formats)."""
    from sqlalchemy import func

    from librarian.config import settings
    from librarian.db.models import Creator, File, Item, ItemCreator
    from librarian.db.session import get_session
    from librarian.filer.naming import ensure_unique_path
    from librarian.filer.transfer import copy_verify_remove

    console.print("[bold blue]Finding duplicate items[/bold blue]")
    if dry_run:
        console.print("[yellow]  Dry run mode - no changes will be made[/yellow]")
    console.print()

    with get_session() as session:
        # Find items with duplicate titles
        duplicates = (
            session.query(Item.title, func.count(Item.id).label("count"))
            .group_by(Item.title)
            .having(func.count(Item.id) > 1)
            .all()
        )

        if not duplicates:
            console.print("[green]No duplicate items found![/green]")
            return

        console.print(f"[blue]Found {len(duplicates)} titles with potential duplicates[/blue]")
        console.print()

        merged_count = 0
        skipped_count = 0

        for title, _count in duplicates:
            if limit and merged_count >= limit:
                break

            # Get all items with this title
            items = session.query(Item).filter(Item.title == title).all()

            # Group by first author to avoid merging different books with same title
            author_groups: dict[str, list[Item]] = {}
            for item in items:
                creators = (
                    session.query(Creator)
                    .join(ItemCreator)
                    .filter(
                        ItemCreator.item_id == item.id,
                        ItemCreator.role == "author",
                    )
                    .order_by(ItemCreator.position)
                    .all()
                )
                first_author = creators[0].name.lower() if creators else ""
                if first_author not in author_groups:
                    author_groups[first_author] = []
                author_groups[first_author].append(item)

            # Merge each group that has duplicates
            for _author, group_items in author_groups.items():
                if len(group_items) < 2:
                    continue

                if limit and merged_count >= limit:
                    break

                # Choose the primary item (prefer one with cover, then most files, then lowest ID)
                group_items.sort(
                    key=lambda i: (
                        i.cover_path is None,  # Items with covers first
                        -len(session.query(File).filter(File.item_id == i.id).all()),  # Most files
                        i.id,  # Lowest ID
                    )
                )

                primary = group_items[0]
                to_merge = group_items[1:]

                # Check if they have different formats (otherwise might be true duplicates)
                primary_files = session.query(File).filter(File.item_id == primary.id).all()
                primary_formats = {f.format for f in primary_files}

                merge_candidates = []
                for item in to_merge:
                    item_files = session.query(File).filter(File.item_id == item.id).all()
                    item_formats = {f.format for f in item_files}

                    # Only merge if different formats
                    if item_formats and not item_formats.intersection(primary_formats):
                        merge_candidates.append((item, item_files))
                    else:
                        skipped_count += 1

                if not merge_candidates:
                    continue

                console.print(f"[cyan]━━━ {title[:60]} ━━━[/cyan]")
                console.print(f"  Primary: ID {primary.id} ({', '.join(primary_formats)})")
                if primary.cover_path:
                    console.print(f"  Has cover: {primary.cover_path}")

                for item, files in merge_candidates:
                    formats = {f.format for f in files}
                    console.print(f"  Merging: ID {item.id} ({', '.join(formats)})")

                    # Move files to primary item's folder
                    primary_folder = None
                    if primary_files:
                        primary_folder = (settings.library_root / primary_files[0].file_path).parent

                    old_folders = set()
                    for file_record in files:
                        old_path = settings.library_root / file_record.file_path
                        old_folders.add(old_path.parent)

                        if primary_folder and old_path.exists():
                            new_path = primary_folder / old_path.name
                            new_path = ensure_unique_path(new_path)

                            console.print(f"    Moving: {old_path.name}")

                            if not dry_run:
                                # Copy, verify, and remove (crash-safe move)
                                success = copy_verify_remove(
                                    source=old_path,
                                    destination=new_path,
                                    expected_checksum=file_record.checksum_md5,
                                    cleanup_parents_up_to=settings.library_root,
                                )
                                if success:
                                    file_record.file_path = str(new_path.relative_to(settings.library_root))
                                else:
                                    console.print(f"    [red]Failed to move {old_path.name}[/red]")

                        # Reassign file to primary item
                        if not dry_run:
                            file_record.item_id = primary.id

                    # Flush file changes before deleting item
                    if not dry_run:
                        session.flush()

                    # Copy cover if primary doesn't have one
                    if not primary.cover_path and item.cover_path:
                        console.print("    Taking cover from merged item")
                        if not dry_run:
                            primary.cover_path = item.cover_path
                    elif item.cover_path and not dry_run:
                        # Delete the duplicate cover
                        old_cover = settings.library_root / item.cover_path
                        if old_cover.exists():
                            old_cover.unlink()

                    # Delete the merged item
                    if not dry_run:
                        # Remove item-creator links
                        session.query(ItemCreator).filter(ItemCreator.item_id == item.id).delete()

                        # Update source file references
                        from librarian.db.models import SourceFile
                        for file_record in files:
                            session.query(SourceFile).filter(
                                SourceFile.migrated_file_id == file_record.id
                            ).update({SourceFile.migrated_file_id: None})

                        session.delete(item)
                        session.commit()

                    # Clean up empty directories
                    if not dry_run:
                        for old_folder in old_folders:
                            if old_folder != primary_folder:
                                _cleanup_empty_dirs(old_folder, settings.library_root)

                    merged_count += 1

                console.print()

        console.print("[bold]Summary:[/bold]")
        console.print(f"  Merged: {merged_count} items")
        console.print(f"  Skipped (same format): {skipped_count}")


if __name__ == "__main__":
    main()
