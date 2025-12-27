"""FastAPI dependencies for authentication."""

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from librarian.db.models import User
from web.auth.service import get_user_from_session
from web.config import settings
from web.database import get_db

# Session cookie name
SESSION_COOKIE_NAME = "alexandria_session"


def get_current_user_optional(
    db: Annotated[DBSession, Depends(get_db)],
    session_id: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> User | None:
    """Get current user from session cookie (optional).

    Args:
        db: Database session
        session_id: Session ID from cookie

    Returns:
        User if authenticated, None otherwise
    """
    if not session_id:
        return None

    return get_user_from_session(db, session_id)


def get_current_user_or_guest(
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User | None:
    """Get current user or allow guest access if enabled.

    Args:
        user: Current user (if any)

    Returns:
        User if authenticated, None if guest access is enabled

    Raises:
        HTTPException: If no user and guest access disabled
    """
    if user:
        return user

    if settings.guest_access:
        return None

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


def get_current_user(
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    """Get current user (required).

    Args:
        user: Current user (if any)

    Returns:
        Current user

    Raises:
        HTTPException: If not authenticated
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    return user


def get_current_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current user (must be admin).

    Args:
        user: Current user

    Returns:
        Current user

    Raises:
        HTTPException: If not authenticated or not admin
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return user


# Type aliases for easier use in route handlers
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserOptional = Annotated[User | None, Depends(get_current_user_optional)]
CurrentUserOrGuest = Annotated[User | None, Depends(get_current_user_or_guest)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]
