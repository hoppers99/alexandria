"""Item (book) API endpoints."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from librarian.config import settings as librarian_settings
from librarian.db.models import Creator, File, Item, ItemCreator
from librarian.enricher import enrich_by_isbn, enrich_by_title_author
from librarian.enricher.google_books import search_by_title_author as google_search
from librarian.enricher.openlibrary import search_by_title_author as ol_search
from web.config import settings
from web.database import get_db

router = APIRouter(prefix="/items", tags=["items"])


# =============================================================================
# Pydantic schemas
# =============================================================================


class CreatorSchema(BaseModel):
    """Creator in API responses."""

    id: int
    name: str
    role: str

    class Config:
        from_attributes = True


class FileSchema(BaseModel):
    """File in API responses."""

    id: int
    format: str
    size_bytes: int | None

    class Config:
        from_attributes = True


class ItemSummarySchema(BaseModel):
    """Brief item info for list views."""

    id: int
    uuid: str
    title: str
    subtitle: str | None
    authors: list[str]
    cover_url: str | None
    series_name: str | None
    series_index: float | None
    media_type: str
    formats: list[str]

    class Config:
        from_attributes = True


class ItemDetailSchema(BaseModel):
    """Full item details."""

    id: int
    uuid: str
    title: str
    subtitle: str | None
    sort_title: str | None
    description: str | None
    publisher: str | None
    publish_date: str | None
    language: str
    isbn: str | None
    isbn13: str | None
    series_name: str | None
    series_index: float | None
    tags: list[str] | None
    media_type: str
    classification_code: str | None
    page_count: int | None
    cover_url: str | None
    creators: list[CreatorSchema]
    files: list[FileSchema]
    date_added: str

    class Config:
        from_attributes = True


class ItemListResponse(BaseModel):
    """Paginated list of items."""

    items: list[ItemSummarySchema]
    total: int
    page: int
    per_page: int
    pages: int


# =============================================================================
# Helper functions
# =============================================================================


def get_authors(item: Item) -> list[str]:
    """Get author names for an item."""
    return [
        ic.creator.name
        for ic in sorted(item.item_creators, key=lambda x: x.position)
        if ic.role == "author"
    ]


def item_to_summary(item: Item) -> ItemSummarySchema:
    """Convert Item to summary schema."""
    formats = sorted({f.format for f in item.files}) if item.files else []
    return ItemSummarySchema(
        id=item.id,
        uuid=item.uuid,
        title=item.title,
        subtitle=item.subtitle,
        authors=get_authors(item),
        cover_url=f"/api/items/{item.id}/cover" if item.cover_path else None,
        series_name=item.series_name,
        series_index=float(item.series_index) if item.series_index else None,
        media_type=item.media_type,
        formats=formats,
    )


def item_to_detail(item: Item) -> ItemDetailSchema:
    """Convert Item to detail schema."""
    creators = [
        CreatorSchema(id=ic.creator.id, name=ic.creator.name, role=ic.role)
        for ic in sorted(item.item_creators, key=lambda x: x.position)
    ]
    files = [
        FileSchema(id=f.id, format=f.format, size_bytes=f.size_bytes)
        for f in item.files
    ]
    return ItemDetailSchema(
        id=item.id,
        uuid=item.uuid,
        title=item.title,
        subtitle=item.subtitle,
        sort_title=item.sort_title,
        description=item.description,
        publisher=item.publisher,
        publish_date=item.publish_date.isoformat() if item.publish_date else None,
        language=item.language,
        isbn=item.isbn,
        isbn13=item.isbn13,
        series_name=item.series_name,
        series_index=float(item.series_index) if item.series_index else None,
        tags=item.tags,
        media_type=item.media_type,
        classification_code=item.classification_code,
        page_count=item.page_count,
        cover_url=f"/api/items/{item.id}/cover" if item.cover_path else None,
        creators=creators,
        files=files,
        date_added=item.date_added.isoformat(),
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=ItemListResponse)
async def list_items(
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1),
    per_page: int = Query(24, ge=1, le=100),
    sort: str = Query("date_added", regex="^(title|date_added|series_name)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    q: str | None = Query(None, description="Search query"),
    author_id: int | None = Query(None),
    series: str | None = Query(None),
    tag: str | None = Query(None),
    media_type: str | None = Query(None, description="Filter by category: fiction or non-fiction"),
    format: str | None = Query(None),
):
    """List items with pagination and filtering."""
    query = (
        select(Item)
        .options(
            joinedload(Item.item_creators).joinedload(ItemCreator.creator),
            joinedload(Item.files),
        )
    )

    # Apply filters
    if q:
        # Simple ILIKE search for now, can use full-text search later
        search_term = f"%{q}%"
        query = query.where(
            Item.title.ilike(search_term)
            | Item.description.ilike(search_term)
        )

    if author_id:
        query = query.where(
            Item.item_creators.any(ItemCreator.creator_id == author_id)
        )

    if series:
        query = query.where(Item.series_name == series)

    if tag:
        query = query.where(Item.tags.contains([tag]))

    # Filter by fiction/non-fiction based on folder structure
    # Fiction is stored in Fiction/, Non-Fiction in Non-Fiction/ (DDC organised)
    if media_type == "fiction":
        query = query.where(Item.files.any(File.file_path.like("Fiction/%")))
    elif media_type == "non-fiction":
        query = query.where(Item.files.any(File.file_path.like("Non-Fiction/%")))

    if format:
        query = query.where(Item.files.any(File.format == format))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Apply sorting
    sort_col = getattr(Item, sort, Item.date_added)
    if order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    # Apply pagination
    query = query.offset((page - 1) * per_page).limit(per_page)

    # Execute
    result = db.execute(query)
    items = result.unique().scalars().all()

    return ItemListResponse(
        items=[item_to_summary(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.get("/recent", response_model=list[ItemSummarySchema])
async def recent_items(
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(12, ge=1, le=50),
):
    """Get recently added items."""
    query = (
        select(Item)
        .options(
            joinedload(Item.item_creators).joinedload(ItemCreator.creator),
            joinedload(Item.files),
        )
        .order_by(Item.date_added.desc())
        .limit(limit)
    )
    result = db.execute(query)
    items = result.unique().scalars().all()
    return [item_to_summary(item) for item in items]


@router.get("/{item_id}", response_model=ItemDetailSchema)
async def get_item(
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """Get item details."""
    query = (
        select(Item)
        .options(
            joinedload(Item.item_creators).joinedload(ItemCreator.creator),
            joinedload(Item.files),
            joinedload(Item.classification),
        )
        .where(Item.id == item_id)
    )
    result = db.execute(query)
    item = result.unique().scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    return item_to_detail(item)


@router.get("/{item_id}/cover")
async def get_cover(
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """Get item cover image."""
    item = db.get(Item, item_id)
    if not item or not item.cover_path:
        raise HTTPException(status_code=404, detail="Cover not found")

    # Paths in DB are relative to library root
    cover_path = settings.library_root / item.cover_path
    if not cover_path.exists():
        raise HTTPException(status_code=404, detail="Cover file not found")

    # Determine media type from extension
    suffix = cover_path.suffix.lower()
    media_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(suffix, "image/jpeg")

    return FileResponse(
        cover_path,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/{item_id}/files/{file_id}/download")
async def download_file(
    item_id: int,
    file_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """Download a file."""
    file = db.get(File, file_id)
    if not file or file.item_id != item_id:
        raise HTTPException(status_code=404, detail="File not found")

    # Paths in DB are relative to library root
    file_path = settings.library_root / file.file_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Set appropriate media type based on format
    media_types = {
        "epub": "application/epub+zip",
        "pdf": "application/pdf",
        "mobi": "application/x-mobipocket-ebook",
        "azw": "application/vnd.amazon.ebook",
        "azw3": "application/vnd.amazon.ebook",
    }
    media_type = media_types.get(file.format, "application/octet-stream")

    return FileResponse(
        file_path,
        filename=file_path.name,
        media_type=media_type,
    )


# =============================================================================
# Item editing endpoints
# =============================================================================


class ItemUpdateSchema(BaseModel):
    """Schema for updating item metadata."""

    title: str | None = None
    subtitle: str | None = None
    description: str | None = None
    publisher: str | None = None
    isbn: str | None = None
    isbn13: str | None = None
    series_name: str | None = None
    series_index: float | None = None
    classification_code: str | None = None
    tags: list[str] | None = None


class RefileRequestSchema(BaseModel):
    """Schema for requesting a refile operation."""

    target_category: str | None = None  # "fiction" or "non-fiction"
    target_ddc: str | None = None  # DDC code like "004" for non-fiction


class AuthorFixSchema(BaseModel):
    """Schema for fixing author names."""

    creator_id: int  # The creator to fix
    corrected_name: str  # The corrected name (e.g., "Terry Goodkind" instead of "Goodkind|Terry")


class EditRequestSchema(BaseModel):
    """Schema for edit request response."""

    id: int
    item_id: int
    request_type: str
    request_data: dict
    status: str
    error_message: str | None
    created_at: str
    processed_at: str | None

    class Config:
        from_attributes = True


class EditRequestListSchema(BaseModel):
    """List of pending edit requests."""

    requests: list[EditRequestSchema]
    total: int


@router.patch("/{item_id}", response_model=ItemDetailSchema)
async def update_item(
    item_id: int,
    updates: ItemUpdateSchema,
    db: Annotated[Session, Depends(get_db)],
):
    """Update item metadata directly."""
    from sqlalchemy.orm import joinedload

    query = (
        select(Item)
        .options(
            joinedload(Item.item_creators).joinedload(ItemCreator.creator),
            joinedload(Item.files),
            joinedload(Item.classification),
        )
        .where(Item.id == item_id)
    )
    result = db.execute(query)
    item = result.unique().scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Apply updates
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)

    return item_to_detail(item)


@router.post("/{item_id}/refile", response_model=EditRequestSchema)
async def request_refile(
    item_id: int,
    refile: RefileRequestSchema,
    db: Annotated[Session, Depends(get_db)],
):
    """Request a refile operation (moves files, processed by librarian)."""
    from librarian.db.models import EditRequest

    # Validate item exists
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Validate request
    if not refile.target_category and not refile.target_ddc:
        raise HTTPException(
            status_code=400,
            detail="Must specify either target_category or target_ddc",
        )

    if refile.target_category and refile.target_category not in ("fiction", "non-fiction"):
        raise HTTPException(
            status_code=400,
            detail="target_category must be 'fiction' or 'non-fiction'",
        )

    # Determine request type
    if refile.target_category == "fiction":
        request_type = "refile_fiction"
        request_data = {"target_category": "fiction"}
    elif refile.target_ddc:
        request_type = "change_ddc"
        request_data = {"target_ddc": refile.target_ddc}
    else:
        request_type = "refile_nonfiction"
        request_data = {"target_category": "non-fiction"}

    # Create edit request
    edit_request = EditRequest(
        item_id=item_id,
        request_type=request_type,
        request_data=request_data,
        status="pending",
    )
    db.add(edit_request)
    db.commit()
    db.refresh(edit_request)

    return EditRequestSchema(
        id=edit_request.id,
        item_id=edit_request.item_id,
        request_type=edit_request.request_type,
        request_data=edit_request.request_data,
        status=edit_request.status,
        error_message=edit_request.error_message,
        created_at=edit_request.created_at.isoformat(),
        processed_at=edit_request.processed_at.isoformat() if edit_request.processed_at else None,
    )


@router.get("/{item_id}/edit-requests", response_model=EditRequestListSchema)
async def get_item_edit_requests(
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """Get pending edit requests for an item."""
    from librarian.db.models import EditRequest

    # Validate item exists
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Get requests
    query = (
        select(EditRequest)
        .where(EditRequest.item_id == item_id)
        .order_by(EditRequest.created_at.desc())
    )
    result = db.execute(query)
    requests = result.scalars().all()

    return EditRequestListSchema(
        requests=[
            EditRequestSchema(
                id=r.id,
                item_id=r.item_id,
                request_type=r.request_type,
                request_data=r.request_data,
                status=r.status,
                error_message=r.error_message,
                created_at=r.created_at.isoformat(),
                processed_at=r.processed_at.isoformat() if r.processed_at else None,
            )
            for r in requests
        ],
        total=len(requests),
    )


@router.delete("/{item_id}/creators/{creator_id}", response_model=ItemDetailSchema)
async def remove_creator(
    item_id: int,
    creator_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """Remove a creator from an item."""
    # Get the item with all relationships
    query = (
        select(Item)
        .options(
            joinedload(Item.item_creators).joinedload(ItemCreator.creator),
            joinedload(Item.files),
            joinedload(Item.classification),
        )
        .where(Item.id == item_id)
    )
    result = db.execute(query)
    item = result.unique().scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Find and remove the item-creator link
    item_creator = db.execute(
        select(ItemCreator).where(
            ItemCreator.item_id == item_id,
            ItemCreator.creator_id == creator_id,
        )
    ).scalar_one_or_none()

    if not item_creator:
        raise HTTPException(
            status_code=404,
            detail="Creator is not linked to this item",
        )

    db.delete(item_creator)
    db.commit()

    # Refresh the item to get updated creators list
    db.refresh(item)

    return item_to_detail(item)


@router.post("/{item_id}/fix-author", response_model=EditRequestSchema)
async def request_author_fix(
    item_id: int,
    fix: AuthorFixSchema,
    db: Annotated[Session, Depends(get_db)],
):
    """Request an author name fix (processed by librarian to update folders)."""
    from librarian.db.models import EditRequest

    # Validate item exists
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Validate creator exists and is linked to this item
    creator = db.get(Creator, fix.creator_id)
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    # Check creator is linked to this item
    item_creator = db.execute(
        select(ItemCreator).where(
            ItemCreator.item_id == item_id,
            ItemCreator.creator_id == fix.creator_id,
        )
    ).scalar_one_or_none()

    if not item_creator:
        raise HTTPException(
            status_code=400,
            detail="Creator is not linked to this item",
        )

    # Create edit request
    edit_request = EditRequest(
        item_id=item_id,
        request_type="fix_author",
        request_data={
            "creator_id": fix.creator_id,
            "original_name": creator.name,
            "corrected_name": fix.corrected_name,
        },
        status="pending",
    )
    db.add(edit_request)
    db.commit()
    db.refresh(edit_request)

    return EditRequestSchema(
        id=edit_request.id,
        item_id=edit_request.item_id,
        request_type=edit_request.request_type,
        request_data=edit_request.request_data,
        status=edit_request.status,
        error_message=edit_request.error_message,
        created_at=edit_request.created_at.isoformat(),
        processed_at=edit_request.processed_at.isoformat() if edit_request.processed_at else None,
    )


# =============================================================================
# Enrichment endpoints (for improving existing item metadata)
# =============================================================================


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


@router.post("/{item_id}/enrich/isbn", response_model=EnrichedResultSchema)
async def enrich_item_by_isbn(
    item_id: int,
    request: EnrichByIsbnRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Search for metadata by ISBN to enrich an existing item."""
    # Validate item exists
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Run enrichment
    enriched = await enrich_by_isbn(
        request.isbn,
        enable_oclc=librarian_settings.enable_oclc,
        enable_openlibrary=librarian_settings.enable_openlibrary,
        enable_google_books=librarian_settings.enable_google_books,
        enable_librarything=librarian_settings.enable_librarything,
        librarything_api_key=librarian_settings.librarything_api_key,
    )

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


@router.post("/{item_id}/enrich/title", response_model=EnrichedResultSchema)
async def enrich_item_by_title(
    item_id: int,
    request: EnrichByTitleRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Search for metadata by title and author to enrich an existing item."""
    # Validate item exists
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Run enrichment
    enriched = await enrich_by_title_author(
        request.title,
        request.author,
        enable_oclc=librarian_settings.enable_oclc,
        enable_openlibrary=librarian_settings.enable_openlibrary,
        enable_google_books=librarian_settings.enable_google_books,
        enable_librarything=librarian_settings.enable_librarything,
        librarything_api_key=librarian_settings.librarything_api_key,
    )

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


@router.post("/{item_id}/search/title", response_model=SearchCandidatesResponse)
async def search_item_by_title(
    item_id: int,
    request: EnrichByTitleRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Search for books by title/author, returning multiple candidates.

    Unlike enrich/title which merges sources and returns one result,
    this returns individual results from each source for user selection.
    """
    # Validate item exists
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    candidates: list[SearchCandidate] = []

    async with httpx.AsyncClient() as client:
        # Search Google Books
        if librarian_settings.enable_google_books:
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
                            series=None,
                            series_number=None,
                        )
                    )

        # Search Open Library
        if librarian_settings.enable_openlibrary:
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
                            isbn13=None,
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
