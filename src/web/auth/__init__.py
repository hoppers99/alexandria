"""Authentication module for Alexandria Web UI."""

from web.auth.dependencies import (
    CurrentAdmin,
    CurrentUser,
    CurrentUserOptional,
    CurrentUserOrGuest,
    SESSION_COOKIE_NAME,
)
from web.auth.password import hash_password, verify_password
from web.auth.service import (
    AuthenticationError,
    RegistrationError,
    authenticate_user,
    get_user_from_session,
    logout_user,
    register_user,
)
from web.auth.startup import create_initial_admin

__all__ = [
    "SESSION_COOKIE_NAME",
    "CurrentAdmin",
    "CurrentUser",
    "CurrentUserOptional",
    "CurrentUserOrGuest",
    "AuthenticationError",
    "RegistrationError",
    "authenticate_user",
    "create_initial_admin",
    "get_user_from_session",
    "hash_password",
    "logout_user",
    "register_user",
    "verify_password",
]
