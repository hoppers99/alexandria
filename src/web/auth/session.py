"""Session management for user authentication."""

import secrets
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DBSession

from librarian.db.models import Session, User
from web.config import settings

if TYPE_CHECKING:
    pass


def create_session(
    db: DBSession,
    user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Session:
    """Create a new session for a user.

    Args:
        db: Database session
        user: User to create session for
        ip_address: IP address of the request
        user_agent: User agent string of the request

    Returns:
        Created session
    """
    # Generate secure random session ID
    session_id = secrets.token_urlsafe(48)  # 48 bytes = 64 chars base64

    # Calculate expiration
    expires_at = datetime.utcnow() + timedelta(
        minutes=settings.session_expire_minutes
    )

    session = Session(
        id=session_id,
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


def get_session(db: DBSession, session_id: str) -> Session | None:
    """Get a session by ID.

    Args:
        db: Database session
        session_id: Session ID to look up

    Returns:
        Session if found and not expired, None otherwise
    """
    stmt = (
        select(Session)
        .where(Session.id == session_id)
        .where(Session.expires_at > datetime.utcnow())
    )
    session = db.scalar(stmt)

    if session:
        # Update last accessed time
        session.last_accessed = datetime.utcnow()
        db.commit()

    return session


def delete_session(db: DBSession, session_id: str) -> None:
    """Delete a session (logout).

    Args:
        db: Database session
        session_id: Session ID to delete
    """
    stmt = delete(Session).where(Session.id == session_id)
    db.execute(stmt)
    db.commit()


def delete_user_sessions(db: DBSession, user_id: int) -> None:
    """Delete all sessions for a user (logout all devices).

    Args:
        db: Database session
        user_id: User ID
    """
    stmt = delete(Session).where(Session.user_id == user_id)
    db.execute(stmt)
    db.commit()


def cleanup_expired_sessions(db: DBSession) -> int:
    """Remove expired sessions from the database.

    Args:
        db: Database session

    Returns:
        Number of sessions deleted
    """
    stmt = delete(Session).where(Session.expires_at <= datetime.utcnow())
    result = db.execute(stmt)
    db.commit()
    return result.rowcount or 0
