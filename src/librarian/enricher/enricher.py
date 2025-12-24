"""Main enricher module that combines results from multiple sources."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from librarian.enricher.calibre import CalibreBook
from librarian.enricher.calibre import lookup_by_filename as calibre_lookup_filename
from librarian.enricher.calibre import lookup_by_isbn as calibre_lookup_isbn
from librarian.enricher.calibre import lookup_by_title_author as calibre_lookup_title
from librarian.enricher.google_books import GoogleBooksResult
from librarian.enricher.google_books import lookup_by_isbn as google_lookup_isbn
from librarian.enricher.google_books import lookup_by_title_author as google_lookup_title
from librarian.enricher.librarything import LibraryThingResult
from librarian.enricher.librarything import lookup_by_isbn as lt_lookup_isbn
from librarian.enricher.oclc import OCLCResult, normalise_ddc
from librarian.enricher.oclc import lookup_by_isbn as oclc_lookup_isbn
from librarian.enricher.oclc import lookup_by_title_author as oclc_lookup_title
from librarian.enricher.openlibrary import OpenLibraryResult
from librarian.enricher.openlibrary import lookup_by_isbn as ol_lookup_isbn
from librarian.enricher.openlibrary import lookup_by_title_author as ol_lookup_title


@dataclass
class EnrichedMetadata:
    """Combined metadata from all enrichment sources."""

    # Core metadata
    title: str | None = None
    subtitle: str | None = None
    authors: list[str] = field(default_factory=list)
    description: str | None = None
    publisher: str | None = None
    publish_date: str | None = None
    language: str | None = None

    # Series info (LibraryThing is particularly good at this)
    series: str | None = None
    series_number: float | None = None

    # Identifiers
    isbn: str | None = None
    isbn13: str | None = None
    related_isbns: list[str] = field(default_factory=list)  # Other editions

    # Classification
    ddc: str | None = None
    ddc_normalised: str | None = None
    lcc: str | None = None
    subjects: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)  # User tags from LibraryThing

    # Physical
    page_count: int | None = None

    # Cover
    cover_url: str | None = None

    # External identifiers
    openlibrary_key: str | None = None
    google_books_id: str | None = None
    oclc_owi: str | None = None
    librarything_work_id: str | None = None

    # Source tracking
    sources: list[str] = field(default_factory=list)

    # Confidence score (0.0 - 1.0)
    confidence: float = 0.0

    # Raw results for debugging
    raw: dict[str, Any] = field(default_factory=dict)


async def enrich_by_isbn(
    isbn: str,
    enable_oclc: bool = True,
    enable_openlibrary: bool = True,
    enable_google_books: bool = True,
    enable_librarything: bool = True,
    librarything_api_key: str | None = None,
    enable_calibre: bool = False,
    calibre_db_path: Path | None = None,
) -> EnrichedMetadata:
    """
    Enrich metadata by looking up ISBN across multiple sources.

    Args:
        isbn: ISBN-10 or ISBN-13
        enable_oclc: Whether to query OCLC Classify
        enable_openlibrary: Whether to query Open Library
        enable_google_books: Whether to query Google Books
        enable_librarything: Whether to query LibraryThing
        librarything_api_key: Optional API key for extended LibraryThing access
        enable_calibre: Whether to query local Calibre database
        calibre_db_path: Path to Calibre's metadata.db

    Returns:
        EnrichedMetadata with combined results
    """
    result = EnrichedMetadata()
    clean_isbn = isbn.replace("-", "").replace(" ", "")

    # Store the original ISBN
    if len(clean_isbn) == 13:
        result.isbn13 = clean_isbn
    elif len(clean_isbn) == 10:
        result.isbn = clean_isbn

    # Query Calibre first (local, fast)
    calibre_result: CalibreBook | None = None
    if enable_calibre and calibre_db_path:
        calibre_result = calibre_lookup_isbn(calibre_db_path, isbn)
        if calibre_result:
            result.sources.append("calibre")
            result.raw["calibre"] = {
                "id": calibre_result.id,
                "title": calibre_result.title,
                "isbn": calibre_result.isbn,
            }

    async with httpx.AsyncClient() as client:
        # Query all enabled sources
        oclc_result: OCLCResult | None = None
        ol_result: OpenLibraryResult | None = None
        google_result: GoogleBooksResult | None = None
        lt_result: LibraryThingResult | None = None

        if enable_oclc:
            oclc_result = await oclc_lookup_isbn(isbn, client)
            if oclc_result:
                result.sources.append("oclc")
                result.raw["oclc"] = {"ddc": oclc_result.ddc, "lcc": oclc_result.lcc}

        if enable_openlibrary:
            ol_result = await ol_lookup_isbn(isbn, client)
            if ol_result:
                result.sources.append("openlibrary")
                result.raw["openlibrary"] = {
                    "title": ol_result.title,
                    "authors": ol_result.authors,
                }

        if enable_google_books:
            google_result = await google_lookup_isbn(isbn, client)
            if google_result:
                result.sources.append("google_books")
                result.raw["google_books"] = {
                    "title": google_result.title,
                    "authors": google_result.authors,
                }

        if enable_librarything:
            lt_result = await lt_lookup_isbn(isbn, client, librarything_api_key)
            if lt_result:
                result.sources.append("librarything")
                result.raw["librarything"] = {
                    "work_id": lt_result.work_id,
                    "related_isbns": lt_result.related_isbns,
                    "tags": lt_result.tags,
                    "series": lt_result.series,
                }

    # Merge results with priority order
    _merge_results(result, oclc_result, ol_result, google_result, lt_result, calibre_result)

    # Calculate confidence
    result.confidence = _calculate_confidence(result)

    return result


async def enrich_by_title_author(
    title: str,
    author: str | None = None,
    enable_oclc: bool = True,
    enable_openlibrary: bool = True,
    enable_google_books: bool = True,
    enable_librarything: bool = True,
    librarything_api_key: str | None = None,
    enable_calibre: bool = False,
    calibre_db_path: Path | None = None,
    filename: str | None = None,
) -> EnrichedMetadata:
    """
    Enrich metadata by searching title and author across multiple sources.

    Note: LibraryThing doesn't support title/author search without an ISBN,
    but we keep the parameter for API consistency.

    Args:
        title: Book title
        author: Author name (optional)
        enable_oclc: Whether to query OCLC Classify
        enable_openlibrary: Whether to query Open Library
        enable_google_books: Whether to query Google Books
        enable_librarything: Whether to query LibraryThing (requires ISBN from other sources)
        librarything_api_key: Optional API key for extended LibraryThing access
        enable_calibre: Whether to query local Calibre database
        calibre_db_path: Path to Calibre's metadata.db
        filename: Optional filename to match against Calibre library

    Returns:
        EnrichedMetadata with combined results
    """
    result = EnrichedMetadata()

    # Query Calibre first (local, fast) - try filename first, then title/author
    calibre_result: CalibreBook | None = None
    if enable_calibre and calibre_db_path:
        # Try filename match first (most specific)
        if filename:
            calibre_result = calibre_lookup_filename(calibre_db_path, filename)

        # Fall back to title/author match
        if not calibre_result:
            calibre_result = calibre_lookup_title(calibre_db_path, title, author)

        if calibre_result:
            result.sources.append("calibre")
            result.raw["calibre"] = {
                "id": calibre_result.id,
                "title": calibre_result.title,
                "isbn": calibre_result.isbn,
            }

    async with httpx.AsyncClient() as client:
        oclc_result: OCLCResult | None = None
        ol_result: OpenLibraryResult | None = None
        google_result: GoogleBooksResult | None = None
        lt_result: LibraryThingResult | None = None

        if enable_oclc:
            oclc_result = await oclc_lookup_title(title, author, client)
            if oclc_result:
                result.sources.append("oclc")

        if enable_openlibrary:
            ol_result = await ol_lookup_title(title, author, client)
            if ol_result:
                result.sources.append("openlibrary")

        if enable_google_books:
            google_result = await google_lookup_title(title, author, client)
            if google_result:
                result.sources.append("google_books")

        # LibraryThing requires ISBN - try to get one from Calibre or other sources
        if enable_librarything:
            isbn_to_lookup = None
            # Try Calibre first
            if calibre_result and calibre_result.isbn:
                isbn_to_lookup = calibre_result.isbn
            elif ol_result and ol_result.isbn_13:
                isbn_to_lookup = ol_result.isbn_13[0]
            elif ol_result and ol_result.isbn_10:
                isbn_to_lookup = ol_result.isbn_10[0]
            elif google_result and google_result.isbn_13:
                isbn_to_lookup = google_result.isbn_13
            elif google_result and google_result.isbn_10:
                isbn_to_lookup = google_result.isbn_10

            if isbn_to_lookup:
                lt_result = await lt_lookup_isbn(isbn_to_lookup, client, librarything_api_key)
                if lt_result:
                    result.sources.append("librarything")

    _merge_results(result, oclc_result, ol_result, google_result, lt_result, calibre_result)
    result.confidence = _calculate_confidence(result)

    return result


def _merge_results(
    result: EnrichedMetadata,
    oclc: OCLCResult | None,
    ol: OpenLibraryResult | None,
    google: GoogleBooksResult | None,
    lt: LibraryThingResult | None = None,
    calibre: CalibreBook | None = None,
) -> None:
    """
    Merge results from all sources into a single EnrichedMetadata.

    Priority:
    - DDC/LCC: OCLC > Open Library
    - Title/Authors: Open Library > Google Books > OCLC > LibraryThing > Calibre
    - Description: Google Books > Open Library > Calibre
    - Cover: Open Library > Google Books
    - Series: LibraryThing > Calibre (best sources for series info)
    - Tags: LibraryThing (user-generated tags) + Calibre tags as subjects
    - Related ISBNs: LibraryThing (ThingISBN)
    - ISBN: Any source (Calibre can provide ISBNs not in the file)
    """
    # Classification (OCLC is most authoritative)
    if oclc and oclc.ddc:
        result.ddc = oclc.ddc
        result.ddc_normalised = normalise_ddc(oclc.ddc)
        result.oclc_owi = oclc.owi
    elif ol and ol.ddc:
        result.ddc = ol.ddc[0] if ol.ddc else None
        result.ddc_normalised = normalise_ddc(ol.ddc[0]) if ol.ddc else None

    if oclc and oclc.lcc:
        result.lcc = oclc.lcc
    elif ol and ol.lcc:
        result.lcc = ol.lcc[0] if ol.lcc else None

    # Title (prefer Open Library, then Google, then OCLC, then LibraryThing, then Calibre)
    if ol and ol.title:
        result.title = ol.title
    elif google and google.title:
        result.title = google.title
        result.subtitle = google.subtitle
    elif oclc and oclc.title:
        result.title = oclc.title
    elif lt and lt.title:
        result.title = lt.title
    elif calibre and calibre.title:
        result.title = calibre.title

    # Authors (prefer Open Library, then Google, then OCLC, then LibraryThing, then Calibre)
    if ol and ol.authors:
        result.authors = ol.authors
    elif google and google.authors:
        result.authors = google.authors
    elif oclc and oclc.authors:
        result.authors = oclc.authors
    elif lt and lt.authors:
        result.authors = lt.authors
    elif calibre and calibre.authors:
        result.authors = calibre.authors

    # Description (Google tends to have better descriptions)
    if google and google.description:
        result.description = google.description
    elif ol and ol.description:
        result.description = ol.description
    elif calibre and calibre.description:
        result.description = calibre.description

    # Publisher and date
    if ol and ol.publishers:
        result.publisher = ol.publishers[0]
    elif google and google.publisher:
        result.publisher = google.publisher
    elif calibre and calibre.publisher:
        result.publisher = calibre.publisher

    if ol and ol.publish_date:
        result.publish_date = ol.publish_date
    elif google and google.publish_date:
        result.publish_date = google.publish_date

    # Subjects (add Calibre tags as subjects if nothing else available)
    if ol and ol.subjects:
        result.subjects = ol.subjects[:10]
    elif google and google.categories:
        result.subjects = google.categories
    elif calibre and calibre.tags:
        result.subjects = calibre.tags[:10]

    # Page count
    if google and google.page_count:
        result.page_count = google.page_count

    # Language
    if google and google.language:
        result.language = google.language
    elif calibre and calibre.language:
        result.language = calibre.language

    # ISBNs (fill in any we're missing - Calibre is a key source)
    if calibre and calibre.isbn:
        # Clean the ISBN from Calibre
        calibre_isbn = calibre.isbn.replace("-", "").replace(" ", "").upper()
        if len(calibre_isbn) == 13 and not result.isbn13:
            result.isbn13 = calibre_isbn
        elif len(calibre_isbn) == 10 and not result.isbn:
            result.isbn = calibre_isbn
    if ol:
        if ol.isbn_10 and not result.isbn:
            result.isbn = ol.isbn_10[0]
        if ol.isbn_13 and not result.isbn13:
            result.isbn13 = ol.isbn_13[0]
    if google:
        if google.isbn_10 and not result.isbn:
            result.isbn = google.isbn_10
        if google.isbn_13 and not result.isbn13:
            result.isbn13 = google.isbn_13

    # Cover URL (prefer Open Library)
    if ol and ol.cover_url:
        result.cover_url = ol.cover_url
    elif google and google.cover_url:
        result.cover_url = google.cover_url

    # External IDs
    if ol and ol.openlibrary_key:
        result.openlibrary_key = ol.openlibrary_key
    if google and google.google_books_id:
        result.google_books_id = google.google_books_id

    # LibraryThing-specific data
    if lt:
        # Work ID
        if lt.work_id:
            result.librarything_work_id = lt.work_id

        # Series info (LibraryThing is the best source for this)
        if lt.series:
            result.series = lt.series
            result.series_number = lt.series_number

        # Related ISBNs (useful for finding alternative editions)
        if lt.related_isbns:
            result.related_isbns = lt.related_isbns

        # User tags (can help with classification and discovery)
        if lt.tags:
            result.tags = lt.tags

    # Calibre series info (fallback if LibraryThing doesn't have it)
    if calibre and not result.series:
        if calibre.series:
            result.series = calibre.series
            result.series_number = calibre.series_index


def _calculate_confidence(result: EnrichedMetadata) -> float:
    """
    Calculate a confidence score for the enriched metadata.

    Returns a score between 0.0 and 1.0.
    """
    score = 0.0
    max_score = 0.0

    # Title (required)
    max_score += 0.2
    if result.title:
        score += 0.2

    # Authors
    max_score += 0.15
    if result.authors:
        score += 0.15

    # DDC classification (very important)
    max_score += 0.25
    if result.ddc:
        score += 0.25

    # Description
    max_score += 0.1
    if result.description:
        score += 0.1

    # Multiple sources agreeing increases confidence
    max_score += 0.15
    if len(result.sources) >= 2:
        score += 0.15
    elif len(result.sources) == 1:
        score += 0.07

    # ISBN
    max_score += 0.1
    if result.isbn or result.isbn13:
        score += 0.1

    # Cover
    max_score += 0.05
    if result.cover_url:
        score += 0.05

    return score / max_score if max_score > 0 else 0.0
