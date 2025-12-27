"""Authentication API endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
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
from web.config import settings
from web.database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


# =============================================================================
# Request/Response Models
# =============================================================================


class LoginRequest(BaseModel):
    """Request body for login."""

    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)


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
def login(
    request: LoginRequest,
    response: Response,
    db: Annotated[DBSession, Depends(get_db)],
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> LoginResponse:
    """Log in with username and password.

    Args:
        request: Login credentials
        response: FastAPI response object (for setting cookies)
        db: Database session
        ip_address: Client IP address
        user_agent: Client user agent

    Returns:
        Login response with user information

    Raises:
        HTTPException: If authentication fails
    """
    try:
        user, session = authenticate_user(
            db=db,
            username=request.username,
            password=request.password,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e

    # Set session cookie
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session.id,
        max_age=settings.session_expire_minutes * 60,
        httponly=True,
        secure=not settings.debug,  # HTTPS only in production
        samesite="lax",
    )

    return LoginResponse(user=UserResponse.model_validate(user))


@router.post("/logout")
def logout(
    response: Response,
    db: Annotated[DBSession, Depends(get_db)],
    user: CurrentUserOptional = None,
    session_id: str | None = None,
) -> dict[str, str]:
    """Log out the current user.

    Args:
        response: FastAPI response object (for clearing cookies)
        db: Database session
        user: Current user (optional)
        session_id: Session ID from cookie

    Returns:
        Success message
    """
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
def change_password(
    current_password: str,
    new_password: str,
    db: Annotated[DBSession, Depends(get_db)],
    user: CurrentUser = None,
) -> dict[str, str]:
    """Change the current user's password.

    Args:
        current_password: Current password for verification
        new_password: New password
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

    # Verify current password
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate new password
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters",
        )

    # Update password
    user.password_hash = hash_password(new_password)
    db.commit()

    return {"message": "Password changed successfully"}
