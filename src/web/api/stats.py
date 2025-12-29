"""Statistics API endpoints."""

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from librarian.db.models import File, Item, ItemCreator, ReadingProgress, SourceFile
from web.auth.dependencies import CurrentUser
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
    user: CurrentUser,
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


# =============================================================================
# Reading Statistics
# =============================================================================


class ReadingStatsSchema(BaseModel):
    """Reading statistics for the user."""

    books_read: int
    books_in_progress: int
    books_not_started: int
    total_books: int
    read_this_year: int
    read_this_month: int
    reading_streak_days: int
    last_read_date: str | None
    monthly_reads: list[dict]  # [{"month": "2024-01", "count": 5}, ...]
    recent_finishes: list[dict]  # [{"item_id": 1, "title": "...", "finished_at": "..."}, ...]


@router.get("/reading", response_model=ReadingStatsSchema)
async def get_reading_stats(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
):
    """Get reading statistics for the user."""
    now = datetime.now()
    start_of_year = datetime(now.year, 1, 1)
    start_of_month = datetime(now.year, now.month, 1)

    # Books read (finished)
    books_read = db.execute(
        select(func.count(ReadingProgress.id)).where(
            ReadingProgress.finished_at.isnot(None)
        )
    ).scalar() or 0

    # Books in progress (started but not finished)
    books_in_progress = db.execute(
        select(func.count(ReadingProgress.id)).where(
            and_(
                ReadingProgress.finished_at.is_(None),
                ReadingProgress.progress > 0,
            )
        )
    ).scalar() or 0

    # Total books in library
    total_books = db.execute(select(func.count(Item.id))).scalar() or 0

    # Books not started
    books_not_started = total_books - books_read - books_in_progress

    # Read this year
    read_this_year = db.execute(
        select(func.count(ReadingProgress.id)).where(
            and_(
                ReadingProgress.finished_at.isnot(None),
                ReadingProgress.finished_at >= start_of_year,
            )
        )
    ).scalar() or 0

    # Read this month
    read_this_month = db.execute(
        select(func.count(ReadingProgress.id)).where(
            and_(
                ReadingProgress.finished_at.isnot(None),
                ReadingProgress.finished_at >= start_of_month,
            )
        )
    ).scalar() or 0

    # Last read date
    last_read = db.execute(
        select(func.max(ReadingProgress.last_read_at))
    ).scalar()

    # Reading streak (consecutive days with reading activity)
    streak_days = 0
    if last_read:
        check_date = now.date()
        # If last read was today or yesterday, start counting
        last_read_date = last_read.date() if isinstance(last_read, datetime) else last_read
        if (check_date - last_read_date).days <= 1:
            while True:
                # Check if there's any reading activity on this date
                start_of_day = datetime.combine(check_date, datetime.min.time())
                end_of_day = start_of_day + timedelta(days=1)
                activity = db.execute(
                    select(func.count(ReadingProgress.id)).where(
                        and_(
                            ReadingProgress.last_read_at >= start_of_day,
                            ReadingProgress.last_read_at < end_of_day,
                        )
                    )
                ).scalar() or 0
                if activity > 0:
                    streak_days += 1
                    check_date -= timedelta(days=1)
                else:
                    break

    # Monthly reads for the past 12 months
    monthly_reads = []
    for i in range(11, -1, -1):
        month_start = datetime(now.year, now.month, 1) - timedelta(days=i * 30)
        month_start = datetime(month_start.year, month_start.month, 1)
        if month_start.month == 12:
            month_end = datetime(month_start.year + 1, 1, 1)
        else:
            month_end = datetime(month_start.year, month_start.month + 1, 1)

        count = db.execute(
            select(func.count(ReadingProgress.id)).where(
                and_(
                    ReadingProgress.finished_at.isnot(None),
                    ReadingProgress.finished_at >= month_start,
                    ReadingProgress.finished_at < month_end,
                )
            )
        ).scalar() or 0

        monthly_reads.append({
            "month": month_start.strftime("%Y-%m"),
            "count": count,
        })

    # Recent finishes (last 5 books completed)
    recent_query = (
        select(ReadingProgress, Item)
        .join(Item, ReadingProgress.item_id == Item.id)
        .where(ReadingProgress.finished_at.isnot(None))
        .order_by(ReadingProgress.finished_at.desc())
        .limit(5)
    )
    recent_rows = db.execute(recent_query).all()
    recent_finishes = [
        {
            "item_id": row[1].id,
            "title": row[1].title,
            "finished_at": row[0].finished_at.isoformat() if row[0].finished_at else None,
        }
        for row in recent_rows
    ]

    return ReadingStatsSchema(
        books_read=books_read,
        books_in_progress=books_in_progress,
        books_not_started=books_not_started,
        total_books=total_books,
        read_this_year=read_this_year,
        read_this_month=read_this_month,
        reading_streak_days=streak_days,
        last_read_date=last_read.isoformat() if last_read else None,
        monthly_reads=monthly_reads,
        recent_finishes=recent_finishes,
    )
