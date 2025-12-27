"""Database schema version compatibility checking."""

import logging
from typing import NamedTuple

from sqlalchemy import text
from sqlalchemy.orm import Session as DBSession

from web import __version__

logger = logging.getLogger(__name__)


class SchemaVersion(NamedTuple):
    """Schema version information."""

    revision: str
    description: str


# Mapping of app versions to required minimum schema versions
# Update this when releasing new versions with schema changes
SCHEMA_VERSION_MAP = {
    "0.1.0": SchemaVersion("75b0e362b398", "Initial schema"),
    "1.0.0": SchemaVersion("b2640a924996", "Add sessions and auth"),
    # Add new versions here as you release
}


def get_current_schema_version(db: DBSession) -> str | None:
    """Get the current database schema version from alembic_version table.

    Args:
        db: Database session

    Returns:
        Current schema revision ID, or None if not initialized
    """
    try:
        result = db.execute(text("SELECT version_num FROM alembic_version"))
        row = result.fetchone()
        return row[0] if row else None
    except Exception:
        # Table doesn't exist - database not initialized
        return None


def get_required_schema_version() -> SchemaVersion:
    """Get the minimum required schema version for the current app version.

    Returns:
        Required schema version for this app version
    """
    # Find the highest version that's <= current app version
    current_version = __version__

    # For development versions (like "0.1.0+dev"), use the base version
    base_version = current_version.split("+")[0].split("-")[0]

    # Get the required schema for this version or fall back to latest
    if base_version in SCHEMA_VERSION_MAP:
        return SCHEMA_VERSION_MAP[base_version]

    # If exact version not found, use the latest defined version
    # (this handles development versions between releases)
    if SCHEMA_VERSION_MAP:
        latest_version = max(SCHEMA_VERSION_MAP.keys())
        return SCHEMA_VERSION_MAP[latest_version]

    # Fallback (shouldn't happen)
    return SchemaVersion("unknown", "Unknown schema version")


def check_schema_compatibility(db: DBSession) -> tuple[bool, str]:
    """Check if database schema is compatible with current app version.

    Args:
        db: Database session

    Returns:
        Tuple of (is_compatible, message)
    """
    current_schema = get_current_schema_version(db)
    required_schema = get_required_schema_version()

    if current_schema is None:
        return (
            False,
            "Database schema not initialized. Migrations will be run automatically.",
        )

    if current_schema == required_schema.revision:
        return (
            True,
            f"Schema version {current_schema} matches app version {__version__}",
        )

    # Schema exists but might be outdated or ahead
    # This is okay - migrations will handle it
    return (
        True,
        f"Schema version {current_schema} will be upgraded if needed (app requires {required_schema.revision})",
    )


def log_schema_version_info(db: DBSession) -> None:
    """Log schema version information for debugging.

    Args:
        db: Database session
    """
    try:
        current = get_current_schema_version(db)
        required = get_required_schema_version()

        logger.info(f"App version: {__version__}")
        logger.info(f"Current schema version: {current or 'Not initialized'}")
        logger.info(
            f"Required schema version: {required.revision} ({required.description})"
        )

        compatible, message = check_schema_compatibility(db)
        if compatible:
            logger.info(f"Schema compatibility: ✓ {message}")
        else:
            logger.warning(f"Schema compatibility: ⚠ {message}")

    except Exception as e:
        logger.warning(f"Could not check schema version: {e}")
