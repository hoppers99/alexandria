"""Review API endpoints for processing pending source files."""

from pathlib import Path
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from librarian.classifier import classify
from librarian.config import settings
from librarian.covers import extract_cover, process_cover
from librarian.db.models import Item, SourceFile
from librarian.enricher import EnrichedMetadata, enrich_by_isbn, enrich_by_title_author
from librarian.enricher.google_books import search_by_title_author as google_search
from librarian.enricher.openlibrary import search_by_title_author as ol_search
from librarian.filer import file_item
from web.database import get_db

router = APIRouter(prefix="/review", tags=["review"])


# =============================================================================
# Pydantic schemas
# =============================================================================


class SourceFileSchema(BaseModel):
    """Source file awaiting review."""

    id: int
    filename: str
    source_path: str
    format: str
    size_bytes: int
    status: str

    # Extracted metadata
    title: str | None
    authors: list[str]
    isbn: str | None
    series: str | None
    series_index: float | None

    # Enrichment data (if available)
    enriched_title: str | None
    enriched_authors: list[str]
    enriched_ddc: str | None
    enriched_subjects: list[str]

    # Classification (if available)
    classification_ddc: str | None
    classification_confidence: float | None

    class Config:
        from_attributes = True


class ReviewListResponse(BaseModel):
    """Paginated list of source files for review."""

    items: list[SourceFileSchema]
    total: int
    pending: int
    skip: int
    limit: int


class EnrichByIsbnRequest(BaseModel):
    """Request to enrich by ISBN."""

    isbn: str


class EnrichByTitleRequest(BaseModel):
    """Request to enrich by title/author."""

    title: str
    author: str | None = None


class EnrichedResultSchema(BaseModel):
    """Result of enrichment lookup."""

    found: bool
    title: str | None
    authors: list[str]
    ddc: str | None
    subjects: list[str]
    publisher: str | None
    publish_date: str | None
    description: str | None
    isbn: str | None
    isbn13: str | None
    cover_url: str | None
    series: str | None
    series_number: float | None


class FileSourceRequest(BaseModel):
    """Request to file a source file."""

    use_enrichment: bool = True
    force_ddc: str | None = None
    force_fiction: bool | None = None

    # Manually edited metadata fields (takes precedence if provided)
    edited_title: str | None = None
    edited_authors: list[str] | None = None
    edited_isbn: str | None = None
    edited_publisher: str | None = None
    edited_publish_date: str | None = None
    edited_series: str | None = None
    edited_series_index: float | None = None
    edited_description: str | None = None


class FileResultSchema(BaseModel):
    """Result of filing a source file."""

    success: bool
    item_id: int | None
    item_title: str | None
    error: str | None
    was_duplicate: bool = False
    duplicate_of_id: int | None = None
    duplicate_of_title: str | None = None


class SkipRequest(BaseModel):
    """Request to skip/mark a source file."""

    status: str = "skipped"  # "skipped" or "duplicate"


class PotentialDuplicate(BaseModel):
    """A potential duplicate item."""

    item_id: int
    title: str
    authors: list[str]
    match_reason: str  # "isbn", "title_author", "title"


class DuplicateCheckResponse(BaseModel):
    """Response from duplicate check."""

    has_potential_duplicates: bool
    duplicates: list[PotentialDuplicate]


class SearchCandidate(BaseModel):
    """A single search result candidate from external sources."""

    source: str  # "google_books" or "openlibrary"
    title: str | None
    authors: list[str]
    publisher: str | None
    publish_date: str | None
    description: str | None
    isbn: str | None
    isbn13: str | None
    cover_url: str | None
    ddc: str | None
    series: str | None
    series_number: float | None


class SearchCandidatesResponse(BaseModel):
    """Response containing multiple search candidates."""

    candidates: list[SearchCandidate]
    query_title: str
    query_author: str | None


# =============================================================================
# Helper functions
# =============================================================================


def source_file_to_schema(sf: SourceFile) -> SourceFileSchema:
    """Convert SourceFile to schema."""
    meta = sf.extracted_metadata or {}
    enriched = meta.get("_enriched", {})
    classif = meta.get("_classification", {})

    return SourceFileSchema(
        id=sf.id,
        filename=sf.filename,
        source_path=sf.source_path,
        format=sf.format,
        size_bytes=sf.size_bytes,
        status=sf.status,
        title=meta.get("title"),
        authors=meta.get("authors", []),
        isbn=meta.get("isbn") or meta.get("isbn13"),
        series=meta.get("series"),
        series_index=meta.get("series_index"),
        enriched_title=enriched.get("title"),
        enriched_authors=enriched.get("authors", []),
        enriched_ddc=enriched.get("ddc"),
        enriched_subjects=enriched.get("subjects", []),
        classification_ddc=classif.get("ddc"),
        classification_confidence=classif.get("confidence"),
    )


def find_potential_duplicates(
    db: Session,
    title: str | None,
    authors: list[str] | None,
    isbn: str | None,
) -> list[PotentialDuplicate]:
    """Find potential duplicate items based on ISBN or title/author match."""
    duplicates = []
    seen_ids = set()

    # 1. Check by ISBN (strongest match)
    if isbn:
        # Normalise ISBN - remove hyphens and spaces
        normalised_isbn = isbn.replace("-", "").replace(" ", "")
        items = db.execute(
            select(Item).where(
                (func.replace(Item.isbn, "-", "") == normalised_isbn)
                | (func.replace(Item.isbn13, "-", "") == normalised_isbn)
            )
        ).scalars().all()

        for item in items:
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                # Get authors for this item
                item_authors = [
                    ic.creator.name
                    for ic in item.creators
                    if ic.role == "author"
                ]
                duplicates.append(
                    PotentialDuplicate(
                        item_id=item.id,
                        title=item.title,
                        authors=item_authors,
                        match_reason="isbn",
                    )
                )

    # 2. Check by exact title + any author match
    if title and authors:
        # Case-insensitive title match
        title_lower = title.lower().strip()
        items = db.execute(
            select(Item).where(func.lower(Item.title) == title_lower)
        ).scalars().all()

        for item in items:
            if item.id not in seen_ids:
                item_authors = [
                    ic.creator.name
                    for ic in item.creators
                    if ic.role == "author"
                ]
                # Check if any author matches
                item_author_lower = {a.lower() for a in item_authors}
                source_author_lower = {a.lower() for a in authors}
                if item_author_lower & source_author_lower:
                    seen_ids.add(item.id)
                    duplicates.append(
                        PotentialDuplicate(
                            item_id=item.id,
                            title=item.title,
                            authors=item_authors,
                            match_reason="title_author",
                        )
                    )

    # 3. Check by title only (weaker match, only if we have title but no authors)
    if title and not authors and not duplicates:
        title_lower = title.lower().strip()
        items = db.execute(
            select(Item).where(func.lower(Item.title) == title_lower).limit(5)
        ).scalars().all()

        for item in items:
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                item_authors = [
                    ic.creator.name
                    for ic in item.creators
                    if ic.role == "author"
                ]
                duplicates.append(
                    PotentialDuplicate(
                        item_id=item.id,
                        title=item.title,
                        authors=item_authors,
                        match_reason="title",
                    )
                )

    return duplicates


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=ReviewListResponse)
async def list_review_queue(
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    format: str | None = Query(None, description="Filter by format"),
    status: str = Query("pending", description="Filter by status"),
):
    """List source files in the review queue."""
    # Build query
    query = select(SourceFile).where(SourceFile.status == status)

    if format:
        query = query.filter(SourceFile.format == format.lower())

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Count all pending (for display)
    pending_count = (
        db.execute(
            select(func.count()).where(SourceFile.status == "pending")
        ).scalar()
        or 0
    )

    # Get paginated results
    query = query.order_by(SourceFile.id).offset(skip).limit(limit)
    result = db.execute(query)
    items = result.scalars().all()

    return ReviewListResponse(
        items=[source_file_to_schema(sf) for sf in items],
        total=total,
        pending=pending_count,
        skip=skip,
        limit=limit,
    )


@router.get("/stats")
async def get_review_stats(db: Annotated[Session, Depends(get_db)]):
    """Get statistics about review queue."""
    # Count by status
    status_counts = {}
    for status in ["pending", "processing", "migrated", "duplicate", "failed", "skipped"]:
        count = db.execute(
            select(func.count()).where(SourceFile.status == status)
        ).scalar() or 0
        status_counts[status] = count

    # Count by format for pending
    format_counts = {}
    format_query = (
        select(SourceFile.format, func.count(SourceFile.id))
        .where(SourceFile.status == "pending")
        .group_by(SourceFile.format)
    )
    for row in db.execute(format_query):
        format_counts[row[0]] = row[1]

    return {
        "by_status": status_counts,
        "pending_by_format": format_counts,
    }


@router.get("/{source_file_id}", response_model=SourceFileSchema)
async def get_source_file(
    source_file_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """Get a single source file for review."""
    sf = db.execute(
        select(SourceFile).where(SourceFile.id == source_file_id)
    ).scalar_one_or_none()

    if not sf:
        raise HTTPException(status_code=404, detail="Source file not found")

    return source_file_to_schema(sf)


@router.get("/{source_file_id}/duplicates", response_model=DuplicateCheckResponse)
async def check_duplicates(
    source_file_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """Check if this source file may be a duplicate of an existing item."""
    sf = db.execute(
        select(SourceFile).where(SourceFile.id == source_file_id)
    ).scalar_one_or_none()

    if not sf:
        raise HTTPException(status_code=404, detail="Source file not found")

    meta = sf.extracted_metadata or {}
    enriched = meta.get("_enriched", {})

    # Use enriched data if available, fall back to extracted
    title = enriched.get("title") or meta.get("title")
    authors = enriched.get("authors") or meta.get("authors", [])
    isbn = enriched.get("isbn13") or enriched.get("isbn") or meta.get("isbn13") or meta.get("isbn")

    duplicates = find_potential_duplicates(db, title, authors, isbn)

    return DuplicateCheckResponse(
        has_potential_duplicates=len(duplicates) > 0,
        duplicates=duplicates,
    )


@router.post("/{source_file_id}/enrich/isbn", response_model=EnrichedResultSchema)
async def enrich_source_file_by_isbn(
    source_file_id: int,
    request: EnrichByIsbnRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Search for metadata by ISBN."""
    sf = db.execute(
        select(SourceFile).where(SourceFile.id == source_file_id)
    ).scalar_one_or_none()

    if not sf:
        raise HTTPException(status_code=404, detail="Source file not found")

    # Run enrichment
    enriched = await enrich_by_isbn(
        request.isbn,
        enable_oclc=settings.enable_oclc,
        enable_openlibrary=settings.enable_openlibrary,
        enable_google_books=settings.enable_google_books,
        enable_librarything=settings.enable_librarything,
        librarything_api_key=settings.librarything_api_key,
    )

    if enriched.title:
        # Store enrichment result in source file metadata
        meta = sf.extracted_metadata or {}
        meta["_enriched"] = {
            "title": enriched.title,
            "authors": enriched.authors or [],
            "ddc": enriched.ddc_normalised,
            "subjects": enriched.subjects or [],
            "isbn": enriched.isbn,
            "isbn13": enriched.isbn13,
            "publisher": enriched.publisher,
            "publish_date": str(enriched.publish_date) if enriched.publish_date else None,
            "description": enriched.description,
            "cover_url": enriched.cover_url,
            "series": enriched.series,
            "series_number": enriched.series_number,
        }
        sf.extracted_metadata = meta
        db.commit()

    return EnrichedResultSchema(
        found=bool(enriched.title),
        title=enriched.title,
        authors=enriched.authors or [],
        ddc=enriched.ddc_normalised,
        subjects=enriched.subjects or [],
        publisher=enriched.publisher,
        publish_date=str(enriched.publish_date) if enriched.publish_date else None,
        description=enriched.description,
        isbn=enriched.isbn,
        isbn13=enriched.isbn13,
        cover_url=enriched.cover_url,
        series=enriched.series,
        series_number=enriched.series_number,
    )


@router.post("/{source_file_id}/enrich/title", response_model=EnrichedResultSchema)
async def enrich_source_file_by_title(
    source_file_id: int,
    request: EnrichByTitleRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Search for metadata by title and author."""
    sf = db.execute(
        select(SourceFile).where(SourceFile.id == source_file_id)
    ).scalar_one_or_none()

    if not sf:
        raise HTTPException(status_code=404, detail="Source file not found")

    # Run enrichment
    enriched = await enrich_by_title_author(
        request.title,
        request.author,
        enable_oclc=settings.enable_oclc,
        enable_openlibrary=settings.enable_openlibrary,
        enable_google_books=settings.enable_google_books,
        enable_librarything=settings.enable_librarything,
        librarything_api_key=settings.librarything_api_key,
    )

    if enriched.title:
        # Store enrichment result in source file metadata
        meta = sf.extracted_metadata or {}
        meta["_enriched"] = {
            "title": enriched.title,
            "authors": enriched.authors or [],
            "ddc": enriched.ddc_normalised,
            "subjects": enriched.subjects or [],
            "isbn": enriched.isbn,
            "isbn13": enriched.isbn13,
            "publisher": enriched.publisher,
            "publish_date": str(enriched.publish_date) if enriched.publish_date else None,
            "description": enriched.description,
            "cover_url": enriched.cover_url,
            "series": enriched.series,
            "series_number": enriched.series_number,
        }
        sf.extracted_metadata = meta
        db.commit()

    return EnrichedResultSchema(
        found=bool(enriched.title),
        title=enriched.title,
        authors=enriched.authors or [],
        ddc=enriched.ddc_normalised,
        subjects=enriched.subjects or [],
        publisher=enriched.publisher,
        publish_date=str(enriched.publish_date) if enriched.publish_date else None,
        description=enriched.description,
        isbn=enriched.isbn,
        isbn13=enriched.isbn13,
        cover_url=enriched.cover_url,
        series=enriched.series,
        series_number=enriched.series_number,
    )


@router.post("/{source_file_id}/search/title", response_model=SearchCandidatesResponse)
async def search_by_title(
    source_file_id: int,
    request: EnrichByTitleRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Search for books by title/author, returning multiple candidates.

    Unlike enrich/title which merges sources and returns one result,
    this returns individual results from each source for user selection.
    """
    sf = db.execute(
        select(SourceFile).where(SourceFile.id == source_file_id)
    ).scalar_one_or_none()

    if not sf:
        raise HTTPException(status_code=404, detail="Source file not found")

    candidates: list[SearchCandidate] = []

    async with httpx.AsyncClient() as client:
        # Search Google Books
        if settings.enable_google_books:
            google_results = await google_search(
                request.title, request.author, client, max_results=5
            )
            for gr in google_results:
                if gr.title:  # Only include results with a title
                    candidates.append(
                        SearchCandidate(
                            source="google_books",
                            title=gr.title,
                            authors=gr.authors or [],
                            publisher=gr.publisher,
                            publish_date=gr.publish_date,
                            description=gr.description,
                            isbn=gr.isbn_10,
                            isbn13=gr.isbn_13,
                            cover_url=gr.cover_url,
                            ddc=None,  # Google Books doesn't have DDC
                            series=None,  # Would need LibraryThing for series
                            series_number=None,
                        )
                    )

        # Search Open Library
        if settings.enable_openlibrary:
            ol_results = await ol_search(
                request.title, request.author, client, max_results=5
            )
            for olr in ol_results:
                if olr.title:  # Only include results with a title
                    candidates.append(
                        SearchCandidate(
                            source="openlibrary",
                            title=olr.title,
                            authors=olr.authors or [],
                            publisher=olr.publishers[0] if olr.publishers else None,
                            publish_date=olr.publish_date,
                            description=olr.description,
                            isbn=olr.isbn_10[0] if olr.isbn_10 else None,
                            isbn13=None,  # OL search returns mixed ISBNs in isbn_10
                            cover_url=olr.cover_url,
                            ddc=olr.ddc[0] if olr.ddc else None,
                            series=None,
                            series_number=None,
                        )
                    )

    return SearchCandidatesResponse(
        candidates=candidates,
        query_title=request.title,
        query_author=request.author,
    )


@router.post("/{source_file_id}/file", response_model=FileResultSchema)
async def file_source_file(
    source_file_id: int,
    request: FileSourceRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """File a source file into the library."""
    sf = db.execute(
        select(SourceFile).where(SourceFile.id == source_file_id)
    ).scalar_one_or_none()

    if not sf:
        raise HTTPException(status_code=404, detail="Source file not found")

    if sf.status != "pending":
        raise HTTPException(
            status_code=400, detail=f"Cannot file source file with status '{sf.status}'"
        )

    meta = sf.extracted_metadata or {}
    enriched_data = meta.get("_enriched", {})

    # Check if we have manually edited fields
    has_edited = request.edited_title is not None

    if has_edited:
        # Use manually edited metadata (from the form)
        enriched = EnrichedMetadata(
            title=request.edited_title,
            authors=request.edited_authors or [],
            subjects=enriched_data.get("subjects", []),  # Keep subjects from enrichment
            ddc_normalised=request.force_ddc or enriched_data.get("ddc"),
            isbn=request.edited_isbn,
            publisher=request.edited_publisher,
            description=request.edited_description,
            series=request.edited_series,
            series_number=request.edited_series_index,
        )
    elif request.use_enrichment and enriched_data.get("title"):
        # Use stored enrichment data
        enriched = EnrichedMetadata(
            title=enriched_data.get("title"),
            authors=enriched_data.get("authors", []),
            subjects=enriched_data.get("subjects", []),
            ddc_normalised=enriched_data.get("ddc"),
            isbn=enriched_data.get("isbn"),
            isbn13=enriched_data.get("isbn13"),
            publisher=enriched_data.get("publisher"),
            description=enriched_data.get("description"),
        )
    else:
        # Use extracted metadata
        enriched = EnrichedMetadata(
            title=meta.get("title"),
            authors=meta.get("authors", []),
            subjects=[],
        )

    if not enriched.title:
        return FileResultSchema(
            success=False,
            item_id=None,
            item_title=None,
            error="No title available - cannot file",
        )

    # Override DDC if forced
    if request.force_ddc:
        enriched.ddc_normalised = request.force_ddc

    # Classify
    classification = classify(enriched)

    # Override fiction if forced
    if request.force_fiction is not None:
        classification.is_fiction = request.force_fiction

    # Force confidence for filing
    classification.confidence = 1.0
    classification.needs_review = False

    try:
        item, file_record = await file_item(
            session=db,
            source_file=sf,
            enriched=enriched,
            classification=classification,
        )

        if item:
            db.commit()
            return FileResultSchema(
                success=True,
                item_id=item.id,
                item_title=item.title,
                error=None,
            )
        else:
            return FileResultSchema(
                success=False,
                item_id=None,
                item_title=None,
                error="Filing failed - unknown error",
            )

    except Exception as e:
        db.rollback()
        return FileResultSchema(
            success=False,
            item_id=None,
            item_title=None,
            error=str(e),
        )


@router.post("/{source_file_id}/skip")
async def skip_source_file(
    source_file_id: int,
    request: SkipRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Skip or mark a source file as duplicate."""
    sf = db.execute(
        select(SourceFile).where(SourceFile.id == source_file_id)
    ).scalar_one_or_none()

    if not sf:
        raise HTTPException(status_code=404, detail="Source file not found")

    if request.status not in ["skipped", "duplicate"]:
        raise HTTPException(status_code=400, detail="Status must be 'skipped' or 'duplicate'")

    sf.status = request.status
    db.commit()

    return {"success": True, "status": sf.status}


@router.get("/{source_file_id}/cover")
async def get_source_file_cover(
    source_file_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """Extract and return the cover image from a source file."""
    sf = db.execute(
        select(SourceFile).where(SourceFile.id == source_file_id)
    ).scalar_one_or_none()

    if not sf:
        raise HTTPException(status_code=404, detail="Source file not found")

    # Build source path
    source_path = Path(settings.source_dir) / sf.source_path
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="Source file not found on disk")

    # Extract cover
    cover_data = extract_cover(source_path, sf.format)
    if not cover_data:
        raise HTTPException(status_code=404, detail="No cover found in source file")

    # Process (resize, convert to JPEG)
    processed = process_cover(cover_data)

    return Response(
        content=processed,
        media_type="image/jpeg",
        headers={"Cache-Control": "max-age=3600"},
    )
