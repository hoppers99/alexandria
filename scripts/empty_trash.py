#!/usr/bin/env python3
"""
Empty the .trash directory in the library.

Use this after confirming trashed files are no longer needed.
"""

import argparse
import shutil
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from librarian.config import settings


def get_trash_stats(trash_dir: Path) -> tuple[int, int]:
    """Count files and total size in trash."""
    if not trash_dir.exists():
        return 0, 0

    file_count = 0
    total_bytes = 0

    for f in trash_dir.rglob("*"):
        if f.is_file():
            file_count += 1
            total_bytes += f.stat().st_size

    return file_count, total_bytes


def main():
    parser = argparse.ArgumentParser(description="Empty the library trash")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Skip confirmation prompt",
    )
    args = parser.parse_args()

    trash_dir = settings.trash_dir

    if not trash_dir.exists():
        print("Trash is empty (directory does not exist)")
        return

    file_count, total_bytes = get_trash_stats(trash_dir)

    if file_count == 0:
        print("Trash is empty")
        return

    size_mb = total_bytes / 1024 / 1024
    print(f"Trash contains {file_count} file(s), {total_bytes:,} bytes ({size_mb:.1f} MB)")

    if args.dry_run:
        print("[DRY RUN] Would delete all files in trash")
        # List some files
        for i, f in enumerate(trash_dir.rglob("*")):
            if f.is_file():
                print(f"  - {f.relative_to(trash_dir)}")
                if i >= 20:
                    remaining = file_count - i - 1
                    if remaining > 0:
                        print(f"  ... and {remaining} more files")
                    break
        return

    if not args.force:
        confirm = input("Are you sure you want to permanently delete these files? [y/N] ")
        if confirm.lower() != "y":
            print("Cancelled")
            return

    shutil.rmtree(trash_dir)
    print(f"Deleted {file_count} file(s), freed {total_bytes:,} bytes ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
