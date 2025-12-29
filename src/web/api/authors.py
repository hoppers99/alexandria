"""Author (creator) API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from librarian.db.models import Creator, ItemCreator
from web.auth.dependencies import CurrentUser
from web.database import get_db

router = APIRouter(prefix="/authors", tags=["authors"])


# =============================================================================
# Pydantic schemas
# =============================================================================


class AuthorSummarySchema(BaseModel):
    """Author summary for list views."""

    id: int
    name: str
    sort_name: str | None
    book_count: int

    class Config:
        from_attributes = True


class AuthorDetailSchema(BaseModel):
    """Full author details."""

    id: int
    name: str
    sort_name: str | None
    bio: str | None
    photo_url: str | None

    class Config:
        from_attributes = True


class AuthorListResponse(BaseModel):
    """Paginated list of authors."""

    authors: list[AuthorSummarySchema]
    total: int
    page: int
    per_page: int
    pages: int


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=AuthorListResponse)
async def list_authors(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    q: str | None = Query(None, description="Search query"),
    sort: str = Query("name", regex="^(name|book_count)$"),
    order: str = Query("asc", regex="^(asc|desc)$"),
):
    """List authors with pagination."""
    # Build query with book count
    book_count = (
        select(func.count(ItemCreator.item_id))
        .where(ItemCreator.creator_id == Creator.id)
        .where(ItemCreator.role == "author")
        .correlate(Creator)
        .scalar_subquery()
    )

    query = select(
        Creator.id,
        Creator.name,
        Creator.sort_name,
        book_count.label("book_count"),
    ).where(
        # Only include creators who are authors of at least one item
        Creator.id.in_(
            select(ItemCreator.creator_id).where(ItemCreator.role == "author")
        )
    )

    # Apply search filter
    if q:
        query = query.where(Creator.name.ilike(f"%{q}%"))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Apply sorting
    if sort == "book_count":
        if order == "desc":
            query = query.order_by(book_count.desc())
        else:
            query = query.order_by(book_count.asc())
    else:
        sort_col = Creator.sort_name if Creator.sort_name else Creator.name
        if order == "desc":
            query = query.order_by(sort_col.desc())
        else:
            query = query.order_by(sort_col.asc())

    # Apply pagination
    query = query.offset((page - 1) * per_page).limit(per_page)

    # Execute
    result = db.execute(query)
    rows = result.all()

    authors = [
        AuthorSummarySchema(
            id=row.id,
            name=row.name,
            sort_name=row.sort_name,
            book_count=row.book_count,
        )
        for row in rows
    ]

    return AuthorListResponse(
        authors=authors,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.get("/{author_id}", response_model=AuthorDetailSchema)
async def get_author(
    author_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
):
    """Get author details."""
    author = db.get(Creator, author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    return AuthorDetailSchema(
        id=author.id,
        name=author.name,
        sort_name=author.sort_name,
        bio=author.bio,
        photo_url=f"/api/authors/{author.id}/photo" if author.photo_path else None,
    )
