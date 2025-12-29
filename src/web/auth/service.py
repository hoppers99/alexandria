"""Authentication service layer."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from librarian.db.models import Session, User
from web.auth.password import hash_password, verify_password
from web.auth.session import create_session, delete_session, get_session
from web.auth.validation import require_strong_password
from web.config import settings


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


class RegistrationError(Exception):
    """Raised when registration fails."""

    pass


def authenticate_user(
    db: DBSession,
    username: str,
    password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[User, Session]:
    """Authenticate a user with username and password.

    Args:
        db: Database session
        username: Username to authenticate
        password: Plain text password
        ip_address: IP address of the request
        user_agent: User agent string

    Returns:
        Tuple of (User, Session) on success

    Raises:
        AuthenticationError: If authentication fails
    """
    # Look up user
    stmt = select(User).where(User.username == username)
    user = db.scalar(stmt)

    if not user:
        # Prevent user enumeration with timing attack
        hash_password(password)  # Run hashing anyway
        raise AuthenticationError("Invalid username or password")

    # Verify password
    if not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid username or password")

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Create session
    session = create_session(
        db=db,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return user, session


def get_user_from_session(db: DBSession, session_id: str) -> User | None:
    """Get user from session ID.

    Args:
        db: Database session
        session_id: Session ID

    Returns:
        User if session is valid, None otherwise
    """
    session = get_session(db, session_id)
    if not session:
        return None

    return session.user


def logout_user(db: DBSession, session_id: str) -> None:
    """Log out a user by deleting their session.

    Args:
        db: Database session
        session_id: Session ID to delete
    """
    delete_session(db, session_id)


def register_user(
    db: DBSession,
    username: str,
    password: str,
    email: str | None = None,
    display_name: str | None = None,
    is_admin: bool = False,
) -> User:
    """Register a new user.

    Args:
        db: Database session
        username: Desired username
        password: Plain text password
        email: Optional email address
        display_name: Optional display name
        is_admin: Whether user should be an admin

    Returns:
        Created user

    Raises:
        RegistrationError: If registration fails
    """
    if not settings.enable_registration and not is_admin:
        raise RegistrationError("Registration is disabled")

    # Validate password strength
    try:
        require_strong_password(password)
    except ValueError as e:
        raise RegistrationError(str(e))

    # Check if username exists
    stmt = select(User).where(User.username == username)
    if db.scalar(stmt):
        raise RegistrationError("Username already exists")

    # Check if email exists (if provided)
    if email:
        stmt = select(User).where(User.email == email)
        if db.scalar(stmt):
            raise RegistrationError("Email already exists")

    # Create user
    user = User(
        username=username,
        password_hash=hash_password(password),
        email=email,
        display_name=display_name or username,
        is_admin=is_admin,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user
