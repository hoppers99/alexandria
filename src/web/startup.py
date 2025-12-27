"""Application startup tasks."""

import logging
import subprocess
from pathlib import Path

from sqlalchemy.orm import Session as DBSession

from librarian.db.seed import seed_classifications
from web.auth import create_initial_admin
from web.schema_version import log_schema_version_info

logger = logging.getLogger(__name__)


def run_database_migrations() -> bool:
    """Run Alembic migrations to ensure database schema is up to date.

    Returns:
        True if migrations ran successfully, False otherwise
    """
    try:
        logger.info("Checking database migrations...")

        # Find alembic.ini (should be in project root)
        alembic_ini = Path(__file__).parent.parent.parent / "alembic.ini"

        if not alembic_ini.exists():
            logger.error(f"alembic.ini not found at {alembic_ini}")
            return False

        # Run alembic upgrade head
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=alembic_ini.parent,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            logger.info("✓ Database migrations completed successfully")
            return True
        else:
            logger.error(f"Database migration failed: {result.stderr}")
            return False

    except FileNotFoundError:
        logger.error("alembic command not found - is it installed?")
        return False
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        return False


def seed_initial_data(db: DBSession) -> None:
    """Seed initial data like classification codes.

    Args:
        db: Database session
    """
    try:
        logger.info("Checking for initial data...")

        # Seed DDC classifications
        added = seed_classifications(db)

        if added > 0:
            logger.info(f"✓ Seeded {added} classification codes")
        else:
            logger.debug("Classifications already seeded")

    except Exception as e:
        logger.error(f"Error seeding initial data: {e}")


def run_startup_tasks(db: DBSession) -> None:
    """Run all startup tasks in order.

    Args:
        db: Database session
    """
    logger.info("Running startup tasks...")

    # 0. Log schema version information
    log_schema_version_info(db)

    # 1. Run database migrations
    migrations_ok = run_database_migrations()
    if not migrations_ok:
        logger.warning("Database migrations failed - some features may not work")

    # 2. Seed initial data (classifications, etc.)
    seed_initial_data(db)

    # 3. Create initial admin user if needed
    create_initial_admin(db)

    logger.info("Startup tasks completed")
