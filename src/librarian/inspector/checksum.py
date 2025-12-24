"""Checksum calculation for file deduplication."""

import hashlib
from pathlib import Path


def calculate_md5(file_path: Path, chunk_size: int = 8192) -> str:
    """Calculate MD5 checksum of a file."""
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            md5.update(chunk)
    return md5.hexdigest()


def calculate_sha256(file_path: Path, chunk_size: int = 8192) -> str:
    """Calculate SHA-256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()


def calculate_checksums(file_path: Path) -> tuple[str, str]:
    """Calculate both MD5 and SHA-256 checksums in a single pass."""
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            md5.update(chunk)
            sha256.update(chunk)

    return md5.hexdigest(), sha256.hexdigest()
