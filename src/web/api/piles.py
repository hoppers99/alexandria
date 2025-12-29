"""Piles (collections) API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from librarian.db.models import Collection, CollectionItem, Item, ItemCreator, ReadingProgress
from web.api.items import ItemWithProgressSchema, item_to_summary_with_progress
from web.auth.dependencies import CurrentUser
from web.database import get_db

router = APIRouter(prefix="/piles", tags=["piles"])


# =============================================================================
# System piles configuration
# =============================================================================

SYSTEM_PILES = {
    "to_read": {
        "name": "To Read",
        "description": "Books you want to read",
        "color": "#f59e0b",  # Amber
    },
    "currently_reading": {
        "name": "Currently Reading",
        "description": "Books you are currently reading",
        "color": "#3b82f6",  # Blue
    },
    "read": {
        "name": "Read",
        "description": "Books you have finished reading",
        "color": "#22c55e",  # Green
    },
}


def ensure_system_piles(db: Session, user_id: int) -> dict[str, Collection]:
    """Ensure system piles exist for a user, creating them if needed."""
    result = {}
    for key, config in SYSTEM_PILES.items():
        pile = db.execute(
            select(Collection).where(
                Collection.user_id == user_id,
                Collection.system_key == key,
            )
        ).scalar_one_or_none()

        if not pile:
            pile = Collection(
                user_id=user_id,
                name=config["name"],
                description=config["description"],
                color=config["color"],
                is_system=True,
                system_key=key,
                is_public=False,
            )
            db.add(pile)
        elif not pile.color:
            # Ensure existing system piles have a colour
            pile.color = config["color"]

        result[key] = pile

    db.commit()
    return result


def get_system_pile(db: Session, user_id: int, system_key: str) -> Collection | None:
    """Get a system pile by key."""
    return db.execute(
        select(Collection).where(
            Collection.user_id == user_id,
            Collection.system_key == system_key,
        )
    ).scalar_one_or_none()


# =============================================================================
# Pydantic schemas
# =============================================================================


class PileSummarySchema(BaseModel):
    """Brief pile info for list views."""

    id: int
    name: str
    description: str | None
    color: str | None
    item_count: int
    first_cover_url: str | None
    is_system: bool = False
    system_key: str | None = None

    class Config:
        from_attributes = True


class PileDetailSchema(BaseModel):
    """Full pile details with items."""

    id: int
    name: str
    description: str | None
    color: str | None
    items: list[ItemWithProgressSchema]
    is_system: bool = False
    system_key: str | None = None

    class Config:
        from_attributes = True


class PileCreateSchema(BaseModel):
    """Schema for creating a pile."""

    name: str
    description: str | None = None
    color: str | None = None


class PileUpdateSchema(BaseModel):
    """Schema for updating a pile."""

    name: str | None = None
    description: str | None = None
    color: str | None = None


class PileItemsSchema(BaseModel):
    """Schema for adding/removing items from a pile."""

    item_ids: list[int]


class PileListResponse(BaseModel):
    """List of piles."""

    piles: list[PileSummarySchema]
    total: int


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=PileListResponse)
async def list_piles(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
):
    """List all piles."""
    # Ensure system piles exist
    ensure_system_piles(db, user.id)

    # Get piles with item counts
    query = (
        select(
            Collection,
            func.count(CollectionItem.item_id).label("item_count"),
        )
        .outerjoin(CollectionItem)
        .where(Collection.user_id == user.id)
        .group_by(Collection.id)
        .order_by(Collection.is_system.desc(), Collection.name)  # System piles first
    )

    result = db.execute(query)
    rows = result.all()

    piles = []
    for collection, item_count in rows:
        # Get first item's cover for the pile thumbnail
        first_cover_url = None
        if item_count > 0:
            first_item = db.execute(
                select(Item)
                .join(CollectionItem)
                .where(CollectionItem.collection_id == collection.id)
                .where(Item.cover_path.isnot(None))
                .limit(1)
            ).scalar_one_or_none()
            if first_item:
                first_cover_url = f"/api/items/{first_item.id}/cover"

        piles.append(
            PileSummarySchema(
                id=collection.id,
                name=collection.name,
                description=collection.description,
                color=collection.color,
                item_count=item_count,
                first_cover_url=first_cover_url,
                is_system=collection.is_system,
                system_key=collection.system_key,
            )
        )

    return PileListResponse(piles=piles, total=len(piles))


@router.post("", response_model=PileSummarySchema, status_code=201)
async def create_pile(
    pile: PileCreateSchema,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
):
    """Create a new pile."""
    collection = Collection(
        user_id=user.id,
        name=pile.name,
        description=pile.description,
        color=pile.color,
        is_public=False,
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)

    return PileSummarySchema(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        color=collection.color,
        item_count=0,
        first_cover_url=None,
    )


@router.get("/{pile_id}", response_model=PileDetailSchema)
async def get_pile(
    pile_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
):
    """Get a pile with all its items."""
    collection = db.execute(
        select(Collection).where(
            Collection.id == pile_id, Collection.user_id == user.id
        )
    ).scalar_one_or_none()

    if not collection:
        raise HTTPException(status_code=404, detail="Pile not found")

    # Get items in the pile
    items_query = (
        select(Item)
        .join(CollectionItem)
        .options(
            joinedload(Item.item_creators).joinedload(ItemCreator.creator),
            joinedload(Item.files),
        )
        .where(CollectionItem.collection_id == pile_id)
        .order_by(CollectionItem.added_at.desc())
    )

    result = db.execute(items_query)
    items = result.unique().scalars().all()

    # Get reading progress for all items in the pile
    item_ids = [item.id for item in items]
    progress_records = {}
    if item_ids:
        progress_query = select(ReadingProgress).where(ReadingProgress.item_id.in_(item_ids))
        for progress in db.execute(progress_query).scalars().all():
            progress_records[progress.item_id] = progress

    # Build items with progress
    items_with_progress = []
    for item in items:
        progress = progress_records.get(item.id)
        items_with_progress.append(
            item_to_summary_with_progress(
                item,
                progress=float(progress.progress) if progress else None,
                last_read_at=progress.last_read_at.isoformat() if progress else None,
            )
        )

    return PileDetailSchema(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        color=collection.color,
        items=items_with_progress,
        is_system=collection.is_system,
        system_key=collection.system_key,
    )


@router.patch("/{pile_id}", response_model=PileSummarySchema)
async def update_pile(
    pile_id: int,
    updates: PileUpdateSchema,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
):
    """Update a pile's name, description, or color."""
    collection = db.execute(
        select(Collection).where(
            Collection.id == pile_id, Collection.user_id == user.id
        )
    ).scalar_one_or_none()

    if not collection:
        raise HTTPException(status_code=404, detail="Pile not found")

    if updates.name is not None:
        collection.name = updates.name
    if updates.description is not None:
        collection.description = updates.description
    if updates.color is not None:
        collection.color = updates.color

    db.commit()
    db.refresh(collection)

    # Get item count
    item_count = db.execute(
        select(func.count(CollectionItem.item_id)).where(
            CollectionItem.collection_id == pile_id
        )
    ).scalar() or 0

    return PileSummarySchema(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        color=collection.color,
        item_count=item_count,
        first_cover_url=None,  # Not critical for update response
        is_system=collection.is_system,
        system_key=collection.system_key,
    )


@router.delete("/{pile_id}", status_code=204)
async def delete_pile(
    pile_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
):
    """Delete a pile."""
    collection = db.execute(
        select(Collection).where(
            Collection.id == pile_id, Collection.user_id == user.id
        )
    ).scalar_one_or_none()

    if not collection:
        raise HTTPException(status_code=404, detail="Pile not found")

    if collection.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system piles")

    db.delete(collection)
    db.commit()


@router.post("/{pile_id}/items", status_code=201)
async def add_items_to_pile(
    pile_id: int,
    items: PileItemsSchema,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
):
    """Add items to a pile."""
    collection = db.execute(
        select(Collection).where(
            Collection.id == pile_id, Collection.user_id == user.id
        )
    ).scalar_one_or_none()

    if not collection:
        raise HTTPException(status_code=404, detail="Pile not found")

    added = 0
    for item_id in items.item_ids:
        # Check if item exists
        item = db.execute(select(Item).where(Item.id == item_id)).scalar_one_or_none()
        if not item:
            continue

        # Check if already in pile
        existing = db.execute(
            select(CollectionItem).where(
                CollectionItem.collection_id == pile_id,
                CollectionItem.item_id == item_id,
            )
        ).scalar_one_or_none()

        if not existing:
            db.add(CollectionItem(collection_id=pile_id, item_id=item_id))
            added += 1

    db.commit()

    return {"added": added}


@router.delete("/{pile_id}/items", status_code=200)
async def remove_items_from_pile(
    pile_id: int,
    items: PileItemsSchema,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
):
    """Remove items from a pile."""
    collection = db.execute(
        select(Collection).where(
            Collection.id == pile_id, Collection.user_id == user.id
        )
    ).scalar_one_or_none()

    if not collection:
        raise HTTPException(status_code=404, detail="Pile not found")

    removed = 0
    for item_id in items.item_ids:
        result = db.execute(
            select(CollectionItem).where(
                CollectionItem.collection_id == pile_id,
                CollectionItem.item_id == item_id,
            )
        ).scalar_one_or_none()

        if result:
            db.delete(result)
            removed += 1

    db.commit()

    return {"removed": removed}


@router.get("/for-item/{item_id}", response_model=list[PileSummarySchema])
async def get_piles_for_item(
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
):
    """Get all piles that contain a specific item."""
    # Get all piles containing this item
    query = (
        select(Collection)
        .join(CollectionItem)
        .where(
            CollectionItem.item_id == item_id,
            Collection.user_id == user.id,
        )
        .order_by(Collection.name)
    )

    result = db.execute(query)
    collections = result.scalars().all()

    piles = []
    for collection in collections:
        # Get item count for each pile
        item_count = db.execute(
            select(func.count(CollectionItem.item_id)).where(
                CollectionItem.collection_id == collection.id
            )
        ).scalar() or 0

        piles.append(
            PileSummarySchema(
                id=collection.id,
                name=collection.name,
                description=collection.description,
                color=collection.color,
                item_count=item_count,
                first_cover_url=None,
                is_system=collection.is_system,
                system_key=collection.system_key,
            )
        )

    return piles
