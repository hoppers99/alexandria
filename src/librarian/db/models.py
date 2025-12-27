"""SQLAlchemy models for Bibliotheca Alexandria."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    type_annotation_map = {
        dict[str, Any]: JSONB,
        list[str]: ARRAY(String),
    }


class MediaType(str, Enum):
    """Types of media in the library."""

    BOOK = "book"
    AUDIOBOOK = "audiobook"
    VIDEO = "video"
    PERIODICAL = "periodical"
    DOCUMENT = "document"


class FileFormat(str, Enum):
    """Supported file formats."""

    EPUB = "epub"
    PDF = "pdf"
    MOBI = "mobi"
    AZW = "azw"
    AZW3 = "azw3"
    DJVU = "djvu"
    CBZ = "cbz"
    CBR = "cbr"
    MP3 = "mp3"
    M4A = "m4a"
    M4B = "m4b"
    MP4 = "mp4"
    MKV = "mkv"


class MigrationStatus(str, Enum):
    """Status of a source file in the migration process."""

    PENDING = "pending"
    PROCESSING = "processing"
    MIGRATED = "migrated"
    DUPLICATE = "duplicate"
    FAILED = "failed"
    SKIPPED = "skipped"


class CreatorRole(str, Enum):
    """Roles a creator can have for an item."""

    AUTHOR = "author"
    NARRATOR = "narrator"
    EDITOR = "editor"
    TRANSLATOR = "translator"
    ILLUSTRATOR = "illustrator"
    DIRECTOR = "director"


# =============================================================================
# Classification
# =============================================================================


class Classification(Base):
    """DDC or other classification codes."""

    __tablename__ = "classifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_code: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("classifications.code")
    )
    system: Mapped[str] = mapped_column(String(50), default="ddc")

    # Relationships
    parent: Mapped["Classification | None"] = relationship(
        "Classification", remote_side=[code], back_populates="children"
    )
    children: Mapped[list["Classification"]] = relationship(
        "Classification", back_populates="parent"
    )
    items: Mapped[list["Item"]] = relationship("Item", back_populates="classification")

    __table_args__ = (
        Index("idx_classifications_parent", "parent_code"),
        Index("idx_classifications_system", "system"),
    )


# =============================================================================
# Creators
# =============================================================================


class Creator(Base):
    """Authors, narrators, editors, etc."""

    __tablename__ = "creators"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_name: Mapped[str | None] = mapped_column(String(255))
    identifiers: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    bio: Mapped[str | None] = mapped_column(Text)
    photo_path: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    item_creators: Mapped[list["ItemCreator"]] = relationship(
        "ItemCreator", back_populates="creator"
    )

    __table_args__ = (
        Index("idx_creators_name", "name"),
        Index("idx_creators_sort", "sort_name"),
    )


# =============================================================================
# Items (core catalogue)
# =============================================================================


class Item(Base):
    """Core catalogue item - a single work that may have multiple file formats."""

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(
        UUID(as_uuid=False), default=lambda: str(uuid4()), unique=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    sort_title: Mapped[str | None] = mapped_column(String(500))
    subtitle: Mapped[str | None] = mapped_column(String(500))

    # Classification
    classification_code: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("classifications.code")
    )

    # Type
    media_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Identifiers
    isbn: Mapped[str | None] = mapped_column(String(20))
    isbn13: Mapped[str | None] = mapped_column(String(20))
    asin: Mapped[str | None] = mapped_column(String(20))
    doi: Mapped[str | None] = mapped_column(String(100))
    identifiers: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Metadata
    description: Mapped[str | None] = mapped_column(Text)
    publisher: Mapped[str | None] = mapped_column(String(255))
    publish_date: Mapped[datetime | None] = mapped_column(DateTime)
    language: Mapped[str] = mapped_column(String(10), default="en")
    series_name: Mapped[str | None] = mapped_column(String(255))
    series_index: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    # Physical/technical
    page_count: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)

    # Cover and backdrop
    cover_path: Mapped[str | None] = mapped_column(String(500))
    backdrop_path: Mapped[str | None] = mapped_column(String(500))

    # Timestamps
    date_added: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    date_modified: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    # Full-text search vector (populated by trigger)
    search_vector: Mapped[Any | None] = mapped_column(TSVECTOR)

    # Relationships
    classification: Mapped["Classification | None"] = relationship(
        "Classification", back_populates="items"
    )
    files: Mapped[list["File"]] = relationship(
        "File", back_populates="item", cascade="all, delete-orphan"
    )
    item_creators: Mapped[list["ItemCreator"]] = relationship(
        "ItemCreator", back_populates="item", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_items_search", "search_vector", postgresql_using="gin"),
        Index("idx_items_classification", "classification_code"),
        Index("idx_items_media_type", "media_type"),
        Index("idx_items_isbn", "isbn"),
        Index("idx_items_isbn13", "isbn13"),
        Index("idx_items_series", "series_name"),
        Index("idx_items_tags", "tags", postgresql_using="gin"),
    )


# =============================================================================
# Files
# =============================================================================


class File(Base):
    """Physical files belonging to items. One item can have multiple formats."""

    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"))
    file_path: Mapped[str] = mapped_column(String(1000), unique=True, nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    checksum_md5: Mapped[str | None] = mapped_column(String(32))
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    date_added: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    metadata_extracted: Mapped[bool] = mapped_column(Boolean, default=False)
    extraction_error: Mapped[str | None] = mapped_column(Text)

    # Relationships
    item: Mapped["Item"] = relationship("Item", back_populates="files")

    __table_args__ = (
        Index("idx_files_item", "item_id"),
        Index("idx_files_format", "format"),
        Index("idx_files_checksum", "checksum_md5"),
    )


# =============================================================================
# Item-Creator relationship
# =============================================================================


class ItemCreator(Base):
    """Many-to-many relationship between items and creators with roles."""

    __tablename__ = "item_creators"

    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"), primary_key=True
    )
    creator_id: Mapped[int] = mapped_column(
        ForeignKey("creators.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(50), primary_key=True, default="author")
    position: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    item: Mapped["Item"] = relationship("Item", back_populates="item_creators")
    creator: Mapped["Creator"] = relationship("Creator", back_populates="item_creators")

    __table_args__ = (Index("idx_item_creators_creator", "creator_id"),)


# =============================================================================
# Reading progress
# =============================================================================


class ReadingProgress(Base):
    """Tracks reading progress for items."""

    __tablename__ = "reading_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )
    file_id: Mapped[int] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"), nullable=False
    )

    # Progress tracking
    progress: Mapped[float] = mapped_column(Numeric(5, 4), default=0)  # 0.0000 to 1.0000
    location: Mapped[str | None] = mapped_column(Text)  # CFI or other location marker
    location_label: Mapped[str | None] = mapped_column(String(500))  # Human-readable location

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    last_read_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    item: Mapped["Item"] = relationship("Item", backref="reading_progress")
    file: Mapped["File"] = relationship("File")

    __table_args__ = (
        Index("idx_reading_progress_item", "item_id"),
        Index("idx_reading_progress_last_read", "last_read_at"),
    )


# =============================================================================
# Migration tracking
# =============================================================================


class SourceFile(Base):
    """Tracks files from the source library during migration."""

    __tablename__ = "source_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_path: Mapped[str] = mapped_column(String(2000), unique=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_md5: Mapped[str] = mapped_column(String(32), nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))

    # Migration status
    status: Mapped[str] = mapped_column(String(20), default="pending")
    migrated_file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id"))
    duplicate_of_id: Mapped[int | None] = mapped_column(ForeignKey("source_files.id"))

    # Extracted metadata (before enrichment)
    extracted_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Processing info
    error_message: Mapped[str | None] = mapped_column(Text)
    scanned_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    migrated_file: Mapped["File | None"] = relationship("File")
    duplicate_of: Mapped["SourceFile | None"] = relationship(
        "SourceFile", remote_side=[id]
    )

    __table_args__ = (
        Index("idx_source_files_status", "status"),
        Index("idx_source_files_checksum", "checksum_md5"),
        Index("idx_source_files_format", "format"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'migrated', 'duplicate', 'failed', 'skipped')",
            name="valid_status",
        ),
    )


# =============================================================================
# Users (for future web UI)
# =============================================================================


class User(Base):
    """User accounts for authentication."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    can_download: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    last_login: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )


class Session(Base):
    """User sessions for authentication."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # Session token
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(String(45))  # IPv6 max length
    user_agent: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    last_accessed: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")

    __table_args__ = (
        Index("idx_sessions_user", "user_id"),
        Index("idx_sessions_expires", "expires_at"),
    )


# =============================================================================
# Collections
# =============================================================================


class Collection(Base):
    """User-created collections/shelves."""

    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str | None] = mapped_column(String(7))  # Hex colour e.g. "#3b82f6"
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    system_key: Mapped[str | None] = mapped_column(String(50))  # e.g. "currently_reading", "to_read"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    collection_items: Mapped[list["CollectionItem"]] = relationship(
        "CollectionItem", back_populates="collection", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_collections_user", "user_id"),
        Index(
            "idx_collections_public",
            "is_public",
            postgresql_where="is_public = true",
        ),
        Index("idx_collections_system_key", "user_id", "system_key"),
    )


class CollectionItem(Base):
    """Items within collections."""

    __tablename__ = "collection_items"

    collection_id: Mapped[int] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"), primary_key=True
    )
    added_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    collection: Mapped["Collection"] = relationship(
        "Collection", back_populates="collection_items"
    )
    item: Mapped["Item"] = relationship("Item")


# =============================================================================
# User progress tracking
# =============================================================================


class UserProgress(Base):
    """Tracks reading/viewing progress per user."""

    __tablename__ = "user_progress"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"), primary_key=True
    )
    file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id"))
    progress_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    position: Mapped[str | None] = mapped_column(String(100))
    last_accessed: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    user: Mapped["User"] = relationship("User")
    item: Mapped["Item"] = relationship("Item")
    file: Mapped["File | None"] = relationship("File")

    __table_args__ = (
        Index("idx_progress_user", "user_id"),
        Index("idx_progress_last", "last_accessed"),
    )


# =============================================================================
# Edit requests (for librarian to process)
# =============================================================================


class EditRequestType(str, Enum):
    """Types of edit requests."""

    REFILE_FICTION = "refile_fiction"  # Move to Fiction folder
    REFILE_NONFICTION = "refile_nonfiction"  # Move to Non-Fiction with DDC
    CHANGE_DDC = "change_ddc"  # Change DDC classification
    METADATA_UPDATE = "metadata_update"  # Update item metadata
    FIX_AUTHOR = "fix_author"  # Fix author name (rename creator, update folder names)


class EditRequest(Base):
    """Pending edit requests for the librarian to process."""

    __tablename__ = "edit_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"))
    request_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Request details stored as JSON
    # For refile: {"target_category": "fiction"} or {"target_ddc": "004"}
    # For metadata: {"field": "description", "value": "New description"}
    request_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Status tracking
    status: Mapped[str] = mapped_column(String(20), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Who requested (null = system/anonymous for now)
    requested_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    # Relationships
    item: Mapped["Item"] = relationship("Item")
    requested_by: Mapped["User | None"] = relationship("User")

    __table_args__ = (
        Index("idx_edit_requests_status", "status"),
        Index("idx_edit_requests_item", "item_id"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="valid_edit_request_status",
        ),
    )
