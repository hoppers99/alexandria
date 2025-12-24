"""Safe file transfer utilities with verification."""

import hashlib
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def calculate_md5(file_path: Path) -> str:
    """Calculate MD5 checksum of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def copy_verify_remove(
    source: Path,
    destination: Path,
    expected_checksum: str | None = None,
    cleanup_parents_up_to: Path | None = None,
) -> bool:
    """
    Safely copy a file with verification, then remove the source.

    This implements a crash-safe file transfer:
    1. If destination exists with matching checksum, skip copy and remove source
    2. Copy source to destination
    3. Verify destination checksum matches source
    4. Remove source only after successful verification

    Args:
        source: Source file path
        destination: Destination file path
        expected_checksum: Optional MD5 checksum to verify against.
                          If not provided, source checksum is calculated.
        cleanup_parents_up_to: If provided, empty parent directories will be
                               removed up to (but not including) this path.

    Returns:
        True if successful, False if verification failed

    Raises:
        OSError: If file operations fail (other than verification)
        shutil.Error: If copy fails
    """
    # Calculate source checksum if not provided
    if expected_checksum is None:
        expected_checksum = calculate_md5(source)

    # Check if destination already exists and matches
    if destination.exists():
        dest_checksum = calculate_md5(destination)
        if dest_checksum == expected_checksum:
            # Destination already has the correct file - just clean up source
            logger.info(f"Destination already exists and verified: {destination}")
            _remove_and_cleanup(source, cleanup_parents_up_to)
            return True
        else:
            # Destination exists but doesn't match - this shouldn't happen
            # in normal operation, so we fail rather than overwrite
            logger.error(
                f"Destination exists with different checksum: {destination} "
                f"(expected {expected_checksum}, got {dest_checksum})"
            )
            return False

    # Copy the file (preserving metadata)
    shutil.copy2(source, destination)

    # Verify the copy
    dest_checksum = calculate_md5(destination)
    if dest_checksum != expected_checksum:
        logger.error(
            f"Copy verification failed for {destination}: "
            f"expected {expected_checksum}, got {dest_checksum}"
        )
        # Remove the bad copy
        destination.unlink()
        return False

    # Copy verified - now safe to remove source
    _remove_and_cleanup(source, cleanup_parents_up_to)
    return True


def _remove_and_cleanup(source: Path, cleanup_up_to: Path | None) -> None:
    """Remove source file and optionally clean up empty parent directories."""
    try:
        source.unlink()
        logger.debug(f"Removed source file: {source}")

        if cleanup_up_to:
            cleanup_empty_parents(source.parent, cleanup_up_to)
    except OSError as e:
        # Non-fatal - the file is already safely at destination
        logger.warning(f"Could not remove source file {source}: {e}")


def cleanup_empty_parents(directory: Path, stop_at: Path) -> None:
    """
    Remove empty parent directories up to (but not including) stop_at.

    Args:
        directory: Starting directory to check
        stop_at: Stop when reaching this directory (do not remove it)
    """
    try:
        current = directory
        while current != stop_at and current.is_relative_to(stop_at):
            if current.exists() and not any(current.iterdir()):
                current.rmdir()
                logger.debug(f"Removed empty directory: {current}")
                current = current.parent
            else:
                break
    except OSError:
        pass  # Non-fatal
