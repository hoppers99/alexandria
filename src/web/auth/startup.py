"""Startup tasks for authentication system."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from librarian.db.models import User
from web.auth.service import RegistrationError, register_user
from web.config import settings

logger = logging.getLogger(__name__)


def create_initial_admin(db: DBSession) -> None:
    """Create initial admin user if none exists and env vars are set.

    This is called on application startup to ensure there's always an admin
    user when deploying in Docker/Unraid environments.

    Args:
        db: Database session
    """
    # Check if any users exist
    stmt = select(User).limit(1)
    existing_user = db.scalar(stmt)

    if existing_user:
        # Users already exist, skip auto-creation
        logger.debug("Users already exist, skipping auto-admin creation")
        return

    # No users exist - check if we should create admin from env vars
    if not settings.admin_username or not settings.admin_password:
        logger.warning(
            "No users exist and ALEXANDRIA_ADMIN_USERNAME/ALEXANDRIA_ADMIN_PASSWORD "
            "not set. You'll need to create an admin user manually with: "
            "docker exec alexandria-backend uv run librarian create-admin"
        )
        return

    # Create admin user
    try:
        user = register_user(
            db=db,
            username=settings.admin_username,
            password=settings.admin_password,
            email=settings.admin_email,
            display_name=settings.admin_username,
            is_admin=True,
        )
        logger.info(
            f"✓ Created initial admin user: {user.username} (ID: {user.id})"
        )
    except RegistrationError as e:
        logger.error(f"Failed to create initial admin user: {e}")
    except Exception as e:
        logger.error(f"Unexpected error creating initial admin user: {e}")
