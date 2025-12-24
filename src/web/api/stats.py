"""Statistics API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from librarian.db.models import File, Item, ItemCreator, SourceFile
from web.database import get_db

router = APIRouter(prefix="/stats", tags=["stats"])


class LibraryStatsSchema(BaseModel):
    """Library statistics."""

    total_items: int
    total_files: int
    total_authors: int
    total_series: int
    total_size_bytes: int
    formats: dict[str, int]
    media_types: dict[str, int]
    migration_status: dict[str, int] | None


@router.get("", response_model=LibraryStatsSchema)
async def get_stats(
    db: Annotated[Session, Depends(get_db)],
):
    """Get library statistics."""
    # Total items
    total_items = db.execute(select(func.count(Item.id))).scalar() or 0

    # Total files
    total_files = db.execute(select(func.count(File.id))).scalar() or 0

    # Total authors
    total_authors = db.execute(
        select(func.count(func.distinct(ItemCreator.creator_id)))
        .where(ItemCreator.role == "author")
    ).scalar() or 0

    # Total series
    total_series = db.execute(
        select(func.count(func.distinct(Item.series_name)))
        .where(Item.series_name.isnot(None))
    ).scalar() or 0

    # Total size
    total_size = db.execute(
        select(func.sum(File.size_bytes))
    ).scalar() or 0

    # Format counts
    format_rows = db.execute(
        select(File.format, func.count(File.id))
        .group_by(File.format)
        .order_by(func.count(File.id).desc())
    ).all()
    formats = {row[0]: row[1] for row in format_rows}

    # Media type counts
    media_type_rows = db.execute(
        select(Item.media_type, func.count(Item.id))
        .group_by(Item.media_type)
        .order_by(func.count(Item.id).desc())
    ).all()
    media_types = {row[0]: row[1] for row in media_type_rows}

    # Migration status (if source files exist)
    migration_status = None
    source_count = db.execute(select(func.count(SourceFile.id))).scalar() or 0
    if source_count > 0:
        status_rows = db.execute(
            select(SourceFile.status, func.count(SourceFile.id))
            .group_by(SourceFile.status)
        ).all()
        migration_status = {row[0]: row[1] for row in status_rows}

    return LibraryStatsSchema(
        total_items=total_items,
        total_files=total_files,
        total_authors=total_authors,
        total_series=total_series,
        total_size_bytes=total_size,
        formats=formats,
        media_types=media_types,
        migration_status=migration_status,
    )
