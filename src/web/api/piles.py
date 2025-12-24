"""Piles (collections) API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from librarian.db.models import Collection, CollectionItem, Item, ItemCreator
from web.api.items import ItemSummarySchema, item_to_summary
from web.database import get_db

router = APIRouter(prefix="/piles", tags=["piles"])


# =============================================================================
# Pydantic schemas
# =============================================================================


class PileSummarySchema(BaseModel):
    """Brief pile info for list views."""

    id: int
    name: str
    description: str | None
    item_count: int
    first_cover_url: str | None

    class Config:
        from_attributes = True


class PileDetailSchema(BaseModel):
    """Full pile details with items."""

    id: int
    name: str
    description: str | None
    items: list[ItemSummarySchema]

    class Config:
        from_attributes = True


class PileCreateSchema(BaseModel):
    """Schema for creating a pile."""

    name: str
    description: str | None = None


class PileUpdateSchema(BaseModel):
    """Schema for updating a pile."""

    name: str | None = None
    description: str | None = None


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


# Default user ID for now (no auth yet)
DEFAULT_USER_ID = 1


@router.get("", response_model=PileListResponse)
async def list_piles(
    db: Annotated[Session, Depends(get_db)],
):
    """List all piles."""
    # Get piles with item counts
    query = (
        select(
            Collection,
            func.count(CollectionItem.item_id).label("item_count"),
        )
        .outerjoin(CollectionItem)
        .where(Collection.user_id == DEFAULT_USER_ID)
        .group_by(Collection.id)
        .order_by(Collection.name)
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
                item_count=item_count,
                first_cover_url=first_cover_url,
            )
        )

    return PileListResponse(piles=piles, total=len(piles))


@router.post("", response_model=PileSummarySchema, status_code=201)
async def create_pile(
    pile: PileCreateSchema,
    db: Annotated[Session, Depends(get_db)],
):
    """Create a new pile."""
    collection = Collection(
        user_id=DEFAULT_USER_ID,
        name=pile.name,
        description=pile.description,
        is_public=False,
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)

    return PileSummarySchema(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        item_count=0,
        first_cover_url=None,
    )


@router.get("/{pile_id}", response_model=PileDetailSchema)
async def get_pile(
    pile_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """Get a pile with all its items."""
    collection = db.execute(
        select(Collection).where(
            Collection.id == pile_id, Collection.user_id == DEFAULT_USER_ID
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

    return PileDetailSchema(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        items=[item_to_summary(item) for item in items],
    )


@router.patch("/{pile_id}", response_model=PileSummarySchema)
async def update_pile(
    pile_id: int,
    updates: PileUpdateSchema,
    db: Annotated[Session, Depends(get_db)],
):
    """Update a pile's name or description."""
    collection = db.execute(
        select(Collection).where(
            Collection.id == pile_id, Collection.user_id == DEFAULT_USER_ID
        )
    ).scalar_one_or_none()

    if not collection:
        raise HTTPException(status_code=404, detail="Pile not found")

    if updates.name is not None:
        collection.name = updates.name
    if updates.description is not None:
        collection.description = updates.description

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
        item_count=item_count,
        first_cover_url=None,  # Not critical for update response
    )


@router.delete("/{pile_id}", status_code=204)
async def delete_pile(
    pile_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """Delete a pile."""
    collection = db.execute(
        select(Collection).where(
            Collection.id == pile_id, Collection.user_id == DEFAULT_USER_ID
        )
    ).scalar_one_or_none()

    if not collection:
        raise HTTPException(status_code=404, detail="Pile not found")

    db.delete(collection)
    db.commit()


@router.post("/{pile_id}/items", status_code=201)
async def add_items_to_pile(
    pile_id: int,
    items: PileItemsSchema,
    db: Annotated[Session, Depends(get_db)],
):
    """Add items to a pile."""
    collection = db.execute(
        select(Collection).where(
            Collection.id == pile_id, Collection.user_id == DEFAULT_USER_ID
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
):
    """Remove items from a pile."""
    collection = db.execute(
        select(Collection).where(
            Collection.id == pile_id, Collection.user_id == DEFAULT_USER_ID
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
):
    """Get all piles that contain a specific item."""
    # Get all piles containing this item
    query = (
        select(Collection)
        .join(CollectionItem)
        .where(
            CollectionItem.item_id == item_id,
            Collection.user_id == DEFAULT_USER_ID,
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
                item_count=item_count,
                first_cover_url=None,
            )
        )

    return piles
