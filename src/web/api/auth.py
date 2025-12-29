"""Authentication API endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session as DBSession

from librarian.db.models import User
from web.auth import (
    SESSION_COOKIE_NAME,
    AuthenticationError,
    CurrentUser,
    CurrentUserOptional,
    RegistrationError,
    authenticate_user,
    logout_user,
    register_user,
)
from web.audit.service import log_audit_event, AuditEventType
from web.auth.validation import require_strong_password
from web.config import settings
from web.database import get_db
from web.middleware.rate_limit import limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])


# =============================================================================
# Request/Response Models
# =============================================================================


class LoginRequest(BaseModel):
    """Request body for login."""

    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)
    remember_me: bool = False  # If true, extend session to 30 days


class RegisterRequest(BaseModel):
    """Request body for registration."""

    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    email: EmailStr | None = None
    display_name: str | None = Field(None, max_length=255)


class UserResponse(BaseModel):
    """User information response."""

    id: int
    username: str
    email: str | None
    display_name: str | None
    is_admin: bool
    can_download: bool
    created_at: datetime
    last_login: datetime | None

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    """Response for successful login."""

    user: UserResponse
    message: str = "Login successful"


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")  # Rate limit: 5 login attempts per minute
def login(
    credentials: LoginRequest,
    response: Response,
    request: Request,  # Required by slowapi rate limiter
    db: Annotated[DBSession, Depends(get_db)],
) -> LoginResponse:
    """Log in with username and password.

    Args:
        credentials: Login credentials
        response: FastAPI response object (for setting cookies)
        request: FastAPI request object (for IP and user agent)
        db: Database session

    Returns:
        Login response with user information

    Raises:
        HTTPException: If authentication fails
    """
    # Get IP and user agent from request
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        user, session = authenticate_user(
            db=db,
            username=credentials.username,
            password=credentials.password,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Log successful login
        log_audit_event(
            db=db,
            event_type=AuditEventType.LOGIN_SUCCESS,
            category="auth",
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"username": user.username}
        )
    except AuthenticationError as e:
        # Log failed login attempt
        log_audit_event(
            db=db,
            event_type=AuditEventType.LOGIN_FAILED,
            category="auth",
            ip_address=ip_address,
            user_agent=user_agent,
            details={"username": credentials.username, "reason": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e

    # Set session cookie
    # If "remember me" is checked, extend session to 30 days, otherwise 7 days default
    session_duration_minutes = 43200 if credentials.remember_me else settings.session_expire_minutes  # 30 days vs 7 days

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session.id,
        max_age=session_duration_minutes * 60,
        httponly=True,
        secure=not settings.debug,  # HTTPS only in production
        samesite="lax",
        path="/",  # Ensure cookie is sent on all paths
    )

    return LoginResponse(user=UserResponse.model_validate(user))


@router.post("/logout")
def logout(
    response: Response,
    request: Request,
    db: Annotated[DBSession, Depends(get_db)],
    user: CurrentUserOptional = None,
    session_id: str | None = None,
) -> dict[str, str]:
    """Log out the current user.

    Args:
        response: FastAPI response object (for clearing cookies)
        request: FastAPI request object (for IP and user agent)
        db: Database session
        user: Current user (optional)
        session_id: Session ID from cookie

    Returns:
        Success message
    """
    # Get IP and user agent
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Log logout event
    if user:
        log_audit_event(
            db=db,
            event_type=AuditEventType.LOGOUT,
            category="auth",
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    # Delete session from database
    if session_id:
        logout_user(db, session_id)

    # Clear session cookie
    response.delete_cookie(key=SESSION_COOKIE_NAME)

    return {"message": "Logout successful"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(user: CurrentUser) -> UserResponse:
    """Get information about the current authenticated user.

    Args:
        user: Current authenticated user

    Returns:
        User information
    """
    return UserResponse.model_validate(user)


@router.post("/register", response_model=UserResponse)
@limiter.limit("3/hour")  # Rate limit: 3 registrations per hour
def register(
    request: RegisterRequest,
    db: Annotated[DBSession, Depends(get_db)],
) -> UserResponse:
    """Register a new user account.

    Args:
        request: Registration information
        db: Database session

    Returns:
        Created user information

    Raises:
        HTTPException: If registration fails
    """
    try:
        user = register_user(
            db=db,
            username=request.username,
            password=request.password,
            email=request.email,
            display_name=request.display_name,
        )
    except RegistrationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return UserResponse.model_validate(user)


@router.post("/change-password")
@limiter.limit("10/hour")  # Rate limit: 10 password changes per hour
def change_password(
    current_password: str,
    new_password: str,
    request: Request,
    db: Annotated[DBSession, Depends(get_db)],
    user: CurrentUser = None,
) -> dict[str, str]:
    """Change the current user's password.

    Args:
        current_password: Current password for verification
        new_password: New password
        fastapi_request: FastAPI request object (for IP and user agent)
        db: Database session
        user: Current authenticated user

    Returns:
        Success message

    Raises:
        HTTPException: If password change fails
    """
    from web.auth import hash_password, verify_password

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Get IP and user agent
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Verify current password
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate new password strength
    try:
        require_strong_password(new_password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Update password
    user.password_hash = hash_password(new_password)
    db.commit()

    # Log password change
    log_audit_event(
        db=db,
        event_type=AuditEventType.PASSWORD_CHANGE,
        category="auth",
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return {"message": "Password changed successfully"}
