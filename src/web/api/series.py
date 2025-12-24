"""Series API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from librarian.db.models import Item, ItemCreator
from web.api.items import ItemSummarySchema, get_authors
from web.database import get_db

router = APIRouter(prefix="/series", tags=["series"])


# =============================================================================
# Pydantic schemas
# =============================================================================


class SeriesSummarySchema(BaseModel):
    """Series summary for list views."""

    name: str
    book_count: int
    authors: list[str]
    first_cover_url: str | None


class SeriesDetailSchema(BaseModel):
    """Series with all books."""

    name: str
    books: list[ItemSummarySchema]
    authors: list[str]


class SeriesListResponse(BaseModel):
    """Paginated list of series."""

    series: list[SeriesSummarySchema]
    total: int
    page: int
    per_page: int
    pages: int


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=SeriesListResponse)
async def list_series(
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    q: str | None = Query(None, description="Search query"),
    sort: str = Query("name", regex="^(name|book_count)$"),
    order: str = Query("asc", regex="^(asc|desc)$"),
):
    """List all series with pagination."""
    # Get distinct series names with counts
    query = (
        select(
            Item.series_name,
            func.count(Item.id).label("book_count"),
            func.min(Item.id).label("first_item_id"),
        )
        .where(Item.series_name.isnot(None))
        .group_by(Item.series_name)
    )

    # Apply search filter
    if q:
        query = query.where(Item.series_name.ilike(f"%{q}%"))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Apply sorting
    if sort == "book_count":
        if order == "desc":
            query = query.order_by(func.count(Item.id).desc())
        else:
            query = query.order_by(func.count(Item.id).asc())
    else:
        if order == "desc":
            query = query.order_by(Item.series_name.desc())
        else:
            query = query.order_by(Item.series_name.asc())

    # Apply pagination
    query = query.offset((page - 1) * per_page).limit(per_page)

    # Execute
    result = db.execute(query)
    rows = result.all()

    # Get first item for each series to extract cover and authors
    series_list = []
    for row in rows:
        first_item = db.execute(
            select(Item)
            .options(joinedload(Item.item_creators).joinedload(ItemCreator.creator))
            .where(Item.id == row.first_item_id)
        ).unique().scalar_one_or_none()

        authors = get_authors(first_item) if first_item else []

        series_list.append(
            SeriesSummarySchema(
                name=row.series_name,
                book_count=row.book_count,
                authors=authors,
                first_cover_url=(
                    f"/api/items/{first_item.id}/cover"
                    if first_item and first_item.cover_path
                    else None
                ),
            )
        )

    return SeriesListResponse(
        series=series_list,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.get("/{series_name}", response_model=SeriesDetailSchema)
async def get_series(
    series_name: str,
    db: Annotated[Session, Depends(get_db)],
):
    """Get all books in a series."""
    query = (
        select(Item)
        .options(
            joinedload(Item.item_creators).joinedload(ItemCreator.creator),
            joinedload(Item.files),
        )
        .where(Item.series_name == series_name)
        .order_by(Item.series_index.asc().nullslast(), Item.title.asc())
    )

    result = db.execute(query)
    items = result.unique().scalars().all()

    if not items:
        raise HTTPException(status_code=404, detail="Series not found")

    # Import here to avoid circular import
    from web.api.items import item_to_summary

    # Collect unique authors across the series
    all_authors: set[str] = set()
    for item in items:
        all_authors.update(get_authors(item))

    return SeriesDetailSchema(
        name=series_name,
        books=[item_to_summary(item) for item in items],
        authors=sorted(all_authors),
    )
