"""Item (book) API endpoints."""

from typing import Annotated

import fastapi
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from librarian.config import settings as librarian_settings
from librarian.db.models import Collection, CollectionItem, Creator, File, Item, ItemCreator
from librarian.enricher import enrich_by_isbn, enrich_by_title_author
from librarian.enricher.google_books import search_by_title_author as google_search
from librarian.enricher.openlibrary import search_by_title_author as ol_search
from web.audit.service import log_audit_event, AuditEventType
from web.auth.dependencies import CurrentAdmin, CurrentUser
from web.config import settings
from web.database import get_db

router = APIRouter(prefix="/items", tags=["items"])


# =============================================================================
# Reading pile management helpers
# =============================================================================


def _move_item_to_system_pile(
    db: Session, user_id: int, item_id: int, target_key: str, remove_from_keys: list[str] | None = None
) -> None:
    """Move an item to a system pile, optionally removing from other system piles.

    Args:
        db: Database session
        user_id: User ID who owns the piles
        item_id: Item ID to move
        target_key: System pile key to add item to (e.g. "currently_reading")
        remove_from_keys: List of system pile keys to remove item from
    """
    # Get target pile
    target_pile = db.execute(
        select(Collection).where(
            Collection.user_id == user_id,
            Collection.system_key == target_key,
        )
    ).scalar_one_or_none()

    if not target_pile:
        return  # System pile doesn't exist yet

    # Check if item is already in target pile
    existing = db.execute(
        select(CollectionItem).where(
            CollectionItem.collection_id == target_pile.id,
            CollectionItem.item_id == item_id,
        )
    ).scalar_one_or_none()

    if not existing:
        db.add(CollectionItem(collection_id=target_pile.id, item_id=item_id))

    # Remove from other system piles if specified
    if remove_from_keys:
        for key in remove_from_keys:
            pile = db.execute(
                select(Collection).where(
                    Collection.user_id == user_id,
                    Collection.system_key == key,
                )
            ).scalar_one_or_none()

            if pile:
                item_in_pile = db.execute(
                    select(CollectionItem).where(
                        CollectionItem.collection_id == pile.id,
                        CollectionItem.item_id == item_id,
                    )
                ).scalar_one_or_none()

                if item_in_pile:
                    db.delete(item_in_pile)


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


class PileInfoSchema(BaseModel):
    """Minimal pile info for item summaries."""

    id: int
    name: str
    color: str | None
    is_system: bool
    system_key: str | None


class ItemSummarySchema(BaseModel):
    """Brief item info for list views."""

    id: int
    uuid: str
    title: str
    subtitle: str | None
    authors: list[str]
    cover_url: str | None
    backdrop_url: str | None
    series_name: str | None
    series_index: float | None
    media_type: str
    formats: list[str]
    piles: list[PileInfoSchema] | None = None

    class Config:
        from_attributes = True


class ItemWithProgressSchema(ItemSummarySchema):
    """Item summary with optional reading progress."""

    progress: float | None = None
    last_read_at: str | None = None


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
    backdrop_url: str | None
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


def get_piles_for_item(db: Session, item_id: int, user_id: int) -> list[PileInfoSchema]:
    """Get all piles that contain an item."""
    query = (
        select(Collection)
        .join(CollectionItem)
        .where(
            CollectionItem.item_id == item_id,
            Collection.user_id == user_id,
        )
    )
    collections = db.execute(query).scalars().all()
    return [
        PileInfoSchema(
            id=c.id,
            name=c.name,
            color=c.color,
            is_system=c.is_system,
            system_key=c.system_key,
        )
        for c in collections
    ]


def item_to_summary(
    item: Item, piles: list[PileInfoSchema] | None = None
) -> ItemSummarySchema:
    """Convert Item to summary schema."""
    formats = sorted({f.format for f in item.files}) if item.files else []
    return ItemSummarySchema(
        id=item.id,
        uuid=item.uuid,
        title=item.title,
        subtitle=item.subtitle,
        authors=get_authors(item),
        cover_url=f"/api/items/{item.id}/cover" if item.cover_path else None,
        backdrop_url=f"/api/items/{item.id}/backdrop" if item.backdrop_path else None,
        series_name=item.series_name,
        series_index=float(item.series_index) if item.series_index else None,
        media_type=item.media_type,
        formats=formats,
        piles=piles,
    )


def item_to_summary_with_progress(
    item: Item,
    progress: float | None = None,
    last_read_at: str | None = None,
    piles: list[PileInfoSchema] | None = None,
) -> ItemWithProgressSchema:
    """Convert Item to summary schema with optional reading progress."""
    formats = sorted({f.format for f in item.files}) if item.files else []
    return ItemWithProgressSchema(
        id=item.id,
        uuid=item.uuid,
        title=item.title,
        subtitle=item.subtitle,
        authors=get_authors(item),
        cover_url=f"/api/items/{item.id}/cover" if item.cover_path else None,
        backdrop_url=f"/api/items/{item.id}/backdrop" if item.backdrop_path else None,
        series_name=item.series_name,
        series_index=float(item.series_index) if item.series_index else None,
        media_type=item.media_type,
        formats=formats,
        progress=progress,
        last_read_at=last_read_at,
        piles=piles,
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
        backdrop_url=f"/api/items/{item.id}/backdrop" if item.backdrop_path else None,
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
    user: CurrentUser,
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
    include_piles: bool = Query(False, description="Include pile membership info"),
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
        # Search across title, description, series name, author names, and ISBN
        search_term = f"%{q}%"
        query = query.where(
            Item.title.ilike(search_term)
            | Item.description.ilike(search_term)
            | Item.series_name.ilike(search_term)
            | Item.isbn.ilike(search_term)
            | Item.isbn13.ilike(search_term)
            | Item.item_creators.any(
                ItemCreator.creator.has(Creator.name.ilike(search_term))
            )
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

    if include_piles:
        item_summaries = [
            item_to_summary(item, piles=get_piles_for_item(db, item.id, user.id))
            for item in items
        ]
    else:
        item_summaries = [item_to_summary(item) for item in items]

    return ItemListResponse(
        items=item_summaries,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.get("/recent", response_model=list[ItemSummarySchema])
async def recent_items(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    limit: int = Query(12, ge=1, le=50),
    include_piles: bool = Query(False, description="Include pile membership info"),
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

    if include_piles:
        return [
            item_to_summary(item, piles=get_piles_for_item(db, item.id, user.id))
            for item in items
        ]
    return [item_to_summary(item) for item in items]


@router.get("/reading/current")
async def get_currently_reading(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    limit: int = Query(20, ge=1, le=50),
    include_piles: bool = Query(False, description="Include pile membership info"),
):
    """Get items currently being read (started but not finished)."""
    from librarian.db.models import ReadingProgress

    # Query items with progress that aren't finished, ordered by last read
    progress_records = (
        db.query(ReadingProgress)
        .filter(
            ReadingProgress.user_id == user.id,
            ReadingProgress.finished_at.is_(None),
            ReadingProgress.progress > 0,
        )
        .order_by(ReadingProgress.last_read_at.desc())
        .limit(limit)
        .all()
    )

    items = []
    for progress in progress_records:
        item = db.get(Item, progress.item_id)
        if item:
            piles = get_piles_for_item(db, item.id, user.id) if include_piles else None
            items.append({
                "item": item_to_summary(item, piles=piles),
                "progress": float(progress.progress),
                "location_label": progress.location_label,
                "last_read_at": progress.last_read_at.isoformat(),
            })

    return {"items": items}


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


class SetCoverRequest(BaseModel):
    """Request to set cover from URL."""

    url: str


class SetCoverResponse(BaseModel):
    """Response after setting cover."""

    success: bool
    cover_url: str | None


@router.post("/{item_id}/cover", response_model=SetCoverResponse)
async def set_cover(
    item_id: int,
    request: SetCoverRequest,
    db: Annotated[Session, Depends(get_db)],
    admin: CurrentAdmin,
):
    """Set item cover from a URL."""
    from librarian.covers import download_cover, process_cover, save_cover

    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Download the cover
    cover_data = await download_cover(request.url)
    if not cover_data:
        raise HTTPException(status_code=400, detail="Failed to download cover from URL")

    # Process and save
    processed = process_cover(cover_data)
    save_cover(processed, item.uuid)

    # Update item's cover path
    item.cover_path = f".covers/{item.uuid}.jpg"
    db.commit()

    return SetCoverResponse(
        success=True,
        cover_url=f"/api/items/{item_id}/cover",
    )


@router.post("/{item_id}/cover/upload", response_model=SetCoverResponse)
async def upload_cover(
    item_id: int,
    file: Annotated[bytes, fastapi.File()],
    db: Annotated[Session, Depends(get_db)],
):
    """Upload a cover image file."""
    from librarian.covers import process_cover, save_cover

    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    # Process and save
    try:
        processed = process_cover(file)
        save_cover(processed, item.uuid)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process image: {e}") from None

    # Update item's cover path
    item.cover_path = f".covers/{item.uuid}.jpg"
    db.commit()

    return SetCoverResponse(
        success=True,
        cover_url=f"/api/items/{item_id}/cover",
    )


# =============================================================================
# Backdrop endpoints
# =============================================================================


class SetBackdropRequest(BaseModel):
    """Request to set backdrop from URL."""

    url: str


class SetBackdropResponse(BaseModel):
    """Response after setting backdrop."""

    success: bool
    backdrop_url: str | None


@router.get("/{item_id}/backdrop")
async def get_backdrop(
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """Get the backdrop image for an item."""
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if not item.backdrop_path:
        raise HTTPException(status_code=404, detail="No backdrop set")

    backdrop_path = settings.library_root / item.backdrop_path
    if not backdrop_path.exists():
        raise HTTPException(status_code=404, detail="Backdrop file not found")

    return FileResponse(
        backdrop_path,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.post("/{item_id}/backdrop", response_model=SetBackdropResponse)
async def set_backdrop(
    item_id: int,
    request: SetBackdropRequest,
    db: Annotated[Session, Depends(get_db)],
    admin: CurrentAdmin,
):
    """Set item backdrop from a URL."""
    from librarian.covers import download_cover, process_cover

    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Download the image
    image_data = await download_cover(request.url)
    if not image_data:
        raise HTTPException(status_code=400, detail="Failed to download image from URL")

    # Process (but allow larger size for backdrops)
    processed = process_cover(image_data, max_size=1920)

    # Save to backdrops directory
    backdrops_dir = librarian_settings.backdrops_dir
    backdrops_dir.mkdir(parents=True, exist_ok=True)
    backdrop_file = backdrops_dir / f"{item.uuid}.jpg"
    backdrop_file.write_bytes(processed)

    # Update item's backdrop path
    item.backdrop_path = f".backdrops/{item.uuid}.jpg"
    db.commit()

    return SetBackdropResponse(
        success=True,
        backdrop_url=f"/api/items/{item_id}/backdrop",
    )


@router.post("/{item_id}/backdrop/upload", response_model=SetBackdropResponse)
async def upload_backdrop(
    item_id: int,
    file: Annotated[bytes, fastapi.File()],
    db: Annotated[Session, Depends(get_db)],
):
    """Upload a backdrop image file."""
    from librarian.covers import process_cover

    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    # Process (allow larger size for backdrops)
    try:
        processed = process_cover(file, max_size=1920)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process image: {e}") from None

    # Save to backdrops directory
    backdrops_dir = librarian_settings.backdrops_dir
    backdrops_dir.mkdir(parents=True, exist_ok=True)
    backdrop_file = backdrops_dir / f"{item.uuid}.jpg"
    backdrop_file.write_bytes(processed)

    # Update item's backdrop path
    item.backdrop_path = f".backdrops/{item.uuid}.jpg"
    db.commit()

    return SetBackdropResponse(
        success=True,
        backdrop_url=f"/api/items/{item_id}/backdrop",
    )


@router.delete("/{item_id}/backdrop", response_model=SetBackdropResponse)
async def delete_backdrop(
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """Remove the backdrop image for an item."""
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item.backdrop_path:
        # Try to delete the file
        backdrop_file = settings.library_root / item.backdrop_path
        if backdrop_file.exists():
            backdrop_file.unlink()

        item.backdrop_path = None
        db.commit()

    return SetBackdropResponse(
        success=True,
        backdrop_url=None,
    )


@router.get("/{item_id}/files/{file_id}/download")
async def download_file(
    item_id: int,
    file_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
):
    """Download a file."""
    # Check download permission
    if not user.can_download:
        raise HTTPException(
            status_code=fastapi.status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to download files"
        )

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
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: CurrentAdmin,
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

    # Log metadata update
    log_audit_event(
        db=db,
        event_type=AuditEventType.METADATA_UPDATED,
        category="admin",
        user=admin,
        resource_type="item",
        resource_id=item_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        details={"fields_updated": list(update_data.keys()), "title": item.title}
    )

    return item_to_detail(item)


@router.post("/{item_id}/refile", response_model=EditRequestSchema)
async def request_refile(
    item_id: int,
    refile: RefileRequestSchema,
    db: Annotated[Session, Depends(get_db)],
    admin: CurrentAdmin,
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
    admin: CurrentAdmin,
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
    admin: CurrentAdmin,
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
    admin: CurrentAdmin,
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
    admin: CurrentAdmin,
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
    admin: CurrentAdmin,
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


# =============================================================================
# Reading progress endpoints
# =============================================================================

from librarian.db.models import ReadingProgress


class ReadingProgressSchema(BaseModel):
    """Reading progress for an item."""

    item_id: int
    file_id: int
    progress: float  # 0.0 to 1.0
    location: str | None
    location_label: str | None
    started_at: str
    last_read_at: str
    finished_at: str | None

    class Config:
        from_attributes = True


class UpdateProgressRequest(BaseModel):
    """Request to update reading progress."""

    file_id: int
    progress: float  # 0.0 to 1.0
    location: str | None = None
    location_label: str | None = None
    finished: bool = False


class ReadingProgressResponse(BaseModel):
    """Response with reading progress."""

    success: bool
    progress: ReadingProgressSchema | None


class CurrentlyReadingItem(BaseModel):
    """Item in the currently reading list."""

    item: ItemSummarySchema
    progress: float
    location_label: str | None
    last_read_at: str


class CurrentlyReadingResponse(BaseModel):
    """Response with currently reading items."""

    items: list[CurrentlyReadingItem]


@router.get("/{item_id}/progress", response_model=ReadingProgressResponse)
async def get_progress(
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
):
    """Get reading progress for an item."""
    progress = db.query(ReadingProgress).filter(
        ReadingProgress.user_id == user.id,
        ReadingProgress.item_id == item_id
    ).first()

    if not progress:
        return ReadingProgressResponse(success=True, progress=None)

    return ReadingProgressResponse(
        success=True,
        progress=ReadingProgressSchema(
            item_id=progress.item_id,
            file_id=progress.file_id,
            progress=float(progress.progress),
            location=progress.location,
            location_label=progress.location_label,
            started_at=progress.started_at.isoformat(),
            last_read_at=progress.last_read_at.isoformat(),
            finished_at=progress.finished_at.isoformat() if progress.finished_at else None,
        ),
    )


@router.post("/{item_id}/progress", response_model=ReadingProgressResponse)
async def update_progress(
    item_id: int,
    request: UpdateProgressRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
):
    """Update reading progress for an item."""
    from datetime import datetime

    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Verify file belongs to item
    file = db.get(File, request.file_id)
    if not file or file.item_id != item_id:
        raise HTTPException(status_code=400, detail="Invalid file ID")

    # Get or create progress record
    progress = db.query(ReadingProgress).filter(
        ReadingProgress.user_id == user.id,
        ReadingProgress.item_id == item_id
    ).first()

    is_new_progress = progress is None
    was_finished = progress.finished_at is not None if progress else False

    if not progress:
        progress = ReadingProgress(
            user_id=user.id,
            item_id=item_id,
            file_id=request.file_id,
        )
        db.add(progress)

    # Update progress
    progress.file_id = request.file_id
    progress.progress = request.progress
    if request.location:
        progress.location = request.location
    if request.location_label:
        progress.location_label = request.location_label

    # Mark as finished if requested
    if request.finished and not progress.finished_at:
        progress.finished_at = datetime.now()
        progress.progress = 1.0
    elif not request.finished:
        progress.finished_at = None

    db.commit()
    db.refresh(progress)

    # Handle pile transitions
    if request.finished and not was_finished:
        # Book finished - move to "Read" pile, remove from reading piles
        _move_item_to_system_pile(
            db, user.id, item_id, "read", remove_from_keys=["currently_reading", "to_read"]
        )
        db.commit()
    elif is_new_progress or request.progress > 0:
        # Started/continued reading - move to "Currently Reading", remove from "To Read" and "Read"
        # Only do this if not already finished
        if not progress.finished_at:
            _move_item_to_system_pile(
                db, user.id, item_id, "currently_reading", remove_from_keys=["to_read", "read"]
            )
            db.commit()

    return ReadingProgressResponse(
        success=True,
        progress=ReadingProgressSchema(
            item_id=progress.item_id,
            file_id=progress.file_id,
            progress=float(progress.progress),
            location=progress.location,
            location_label=progress.location_label,
            started_at=progress.started_at.isoformat(),
            last_read_at=progress.last_read_at.isoformat(),
            finished_at=progress.finished_at.isoformat() if progress.finished_at else None,
        ),
    )


@router.post("/{item_id}/progress/finish", response_model=ReadingProgressResponse)
async def mark_as_finished(
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
):
    """Mark an item as finished reading (without needing file ID).

    Creates progress record if none exists. Useful for physical books or
    manually marking items as read.
    """
    from datetime import datetime

    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Get or create progress record
    progress = db.query(ReadingProgress).filter(
        ReadingProgress.user_id == user.id,
        ReadingProgress.item_id == item_id
    ).first()

    was_finished = progress.finished_at is not None if progress else False

    if not progress:
        # Create a new progress record - use first file if available
        file_id = item.files[0].id if item.files else None
        progress = ReadingProgress(
            user_id=user.id,
            item_id=item_id,
            file_id=file_id,
            progress=1.0,
        )
        db.add(progress)

    # Mark as finished
    progress.progress = 1.0
    progress.finished_at = datetime.now()

    db.commit()
    db.refresh(progress)

    # Handle pile transition if not already finished
    if not was_finished:
        _move_item_to_system_pile(
            db, user.id, item_id, "read", remove_from_keys=["currently_reading", "to_read"]
        )
        db.commit()

    return ReadingProgressResponse(
        success=True,
        progress=ReadingProgressSchema(
            item_id=progress.item_id,
            file_id=progress.file_id,
            progress=float(progress.progress),
            location=progress.location,
            location_label=progress.location_label,
            started_at=progress.started_at.isoformat(),
            last_read_at=progress.last_read_at.isoformat(),
            finished_at=progress.finished_at.isoformat() if progress.finished_at else None,
        ),
    )


@router.post("/{item_id}/progress/unfinish", response_model=ReadingProgressResponse)
async def mark_as_unfinished(
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
):
    """Mark an item as not finished (resume reading).

    Clears the finished_at date and moves back to Currently Reading pile.
    """
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    progress = db.query(ReadingProgress).filter(
        ReadingProgress.user_id == user.id,
        ReadingProgress.item_id == item_id
    ).first()

    if not progress:
        raise HTTPException(status_code=404, detail="No reading progress found")

    # Clear finished status but keep progress
    progress.finished_at = None

    db.commit()
    db.refresh(progress)

    # Move back to Currently Reading
    _move_item_to_system_pile(
        db, user.id, item_id, "currently_reading", remove_from_keys=["read"]
    )
    db.commit()

    return ReadingProgressResponse(
        success=True,
        progress=ReadingProgressSchema(
            item_id=progress.item_id,
            file_id=progress.file_id,
            progress=float(progress.progress),
            location=progress.location,
            location_label=progress.location_label,
            started_at=progress.started_at.isoformat(),
            last_read_at=progress.last_read_at.isoformat(),
            finished_at=None,
        ),
    )


@router.delete("/{item_id}/progress")
async def delete_progress(
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
):
    """Delete reading progress for an item (mark as unread)."""
    progress = db.query(ReadingProgress).filter(
        ReadingProgress.user_id == user.id,
        ReadingProgress.item_id == item_id
    ).first()

    if progress:
        db.delete(progress)
        db.commit()

    return {"success": True}
