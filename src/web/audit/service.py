"""Audit logging service."""

from typing import Any

from sqlalchemy.orm import Session

from librarian.db.models import AuditLog, User


class AuditEventType:
    """Audit event types."""

    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"

    # Admin actions
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    METADATA_UPDATED = "metadata_updated"
    ITEM_DELETED = "item_deleted"
    COVER_CHANGED = "cover_changed"
    BACKDROP_CHANGED = "backdrop_changed"

    # Review queue actions
    SOURCE_FILE_PROCESSED = "source_file_processed"
    SOURCE_FILE_SKIPPED = "source_file_skipped"

    # Download actions
    FILE_DOWNLOADED = "file_downloaded"
    DOWNLOAD_DENIED = "download_denied"


class AuditCategory:
    """Audit event categories."""

    AUTH = "auth"
    ADMIN = "admin"
    USER = "user"


def log_audit_event(
    db: Session,
    event_type: str,
    category: str,
    user: User | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Log an audit event.

    Args:
        db: Database session
        event_type: Type of event (use AuditEventType constants)
        category: Event category (use AuditCategory constants)
        user: User performing the action (if applicable)
        resource_type: Type of resource affected (e.g., "item", "user")
        resource_id: ID of resource affected
        ip_address: IP address of request
        user_agent: User agent string
        details: Additional event details (JSON-serialisable dict)

    Returns:
        Created audit log entry
    """
    audit_log = AuditLog(
        user_id=user.id if user else None,
        event_type=event_type,
        event_category=category,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details,
    )

    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)

    return audit_log
