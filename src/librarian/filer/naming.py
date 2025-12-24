"""Canonical filename generation."""

import re
import unicodedata
from pathlib import Path

# Characters that are unsafe for filenames on various filesystems
UNSAFE_CHARS = r'[<>:"/\\|?*\x00-\x1f]'

# Maximum filename length (leaving room for extension)
MAX_FILENAME_LENGTH = 200


def generate_filename(
    title: str,
    authors: list[str],
    series: str | None = None,
    series_index: float | None = None,
    extension: str = "epub",
    author_format: str = "first_last",
) -> str:
    """
    Generate a canonical filename for a library item.

    Format:
    - Standard: "Author - Title.ext"
    - Series: "Author - Series NN - Title.ext"
    - Multi-author: "Author1 & Author2 - Title.ext"

    Args:
        title: Book title
        authors: List of author names
        series: Series name (optional)
        series_index: Position in series (optional)
        extension: File extension without dot
        author_format: "first_last" or "last_first"

    Returns:
        Sanitised filename string
    """
    # Format author(s)
    if authors:
        formatted_authors = [_format_author(a, author_format) for a in authors[:2]]
        author_str = " & ".join(formatted_authors)
    else:
        author_str = "Unknown"

    # Clean title
    clean_title = _sanitise_component(title) if title else "Untitled"

    # Build filename
    if series and series_index is not None:
        clean_series = _sanitise_component(series)
        # Format series index as zero-padded integer
        index_str = f"{int(series_index):02d}"
        filename = f"{author_str} - {clean_series} {index_str} - {clean_title}"
    elif series:
        clean_series = _sanitise_component(series)
        filename = f"{author_str} - {clean_series} - {clean_title}"
    else:
        filename = f"{author_str} - {clean_title}"

    # Ensure extension doesn't have a leading dot
    ext = extension.lstrip(".")

    # Truncate if necessary
    max_base = MAX_FILENAME_LENGTH - len(ext) - 1  # -1 for the dot
    if len(filename) > max_base:
        filename = filename[:max_base].rstrip()

    return f"{filename}.{ext}"


def _format_author(name: str, format_style: str) -> str:
    """
    Format an author name according to style.

    Args:
        name: Author name as found in metadata
        format_style: "first_last" or "last_first"

    Returns:
        Formatted author name
    """
    if not name:
        return "Unknown"

    # Clean up the name
    name = name.strip()

    # If already in "Last, First" format and we want first_last, swap
    if ", " in name and format_style == "first_last":
        parts = name.split(", ", 1)
        if len(parts) == 2:
            name = f"{parts[1]} {parts[0]}"

    # If in "First Last" format and we want last_first, swap
    elif ", " not in name and format_style == "last_first":
        parts = name.rsplit(" ", 1)
        if len(parts) == 2:
            name = f"{parts[1]}, {parts[0]}"

    return _sanitise_component(name)


def _sanitise_component(text: str) -> str:
    """
    Sanitise a filename component (title, author, series).

    - Remove/replace unsafe characters
    - Normalise whitespace
    - Handle Unicode properly
    """
    if not text:
        return ""

    # Normalise Unicode to NFC form
    text = unicodedata.normalize("NFC", text)

    # Replace unsafe characters with safe alternatives
    text = re.sub(UNSAFE_CHARS, "", text)

    # Replace common problematic patterns
    replacements = [
        (":", " -"),
        (";", ","),
        ("...", "…"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)

    # Normalise whitespace
    text = " ".join(text.split())

    # Remove leading/trailing dots and spaces
    text = text.strip(". ")

    return text


def generate_folder_name(
    title: str,
    authors: list[str],
    series: str | None = None,
    series_index: float | None = None,
    author_format: str = "first_last",
) -> str:
    """
    Generate a canonical folder name for an item.

    Format matches filename but without extension:
    - Standard: "Author - Title"
    - Series: "Author - Series NN - Title"

    Args:
        title: Book title
        authors: List of author names
        series: Series name (optional)
        series_index: Position in series (optional)
        author_format: "first_last" or "last_first"

    Returns:
        Sanitised folder name string
    """
    # Format author(s)
    if authors:
        formatted_authors = [_format_author(a, author_format) for a in authors[:2]]
        author_str = " & ".join(formatted_authors)
    else:
        author_str = "Unknown"

    # Clean title
    clean_title = _sanitise_component(title) if title else "Untitled"

    # Build folder name
    if series and series_index is not None:
        clean_series = _sanitise_component(series)
        index_str = f"{int(series_index):02d}"
        folder_name = f"{author_str} - {clean_series} {index_str} - {clean_title}"
    elif series:
        clean_series = _sanitise_component(series)
        folder_name = f"{author_str} - {clean_series} - {clean_title}"
    else:
        folder_name = f"{author_str} - {clean_title}"

    # Truncate if necessary
    if len(folder_name) > MAX_FILENAME_LENGTH:
        folder_name = folder_name[:MAX_FILENAME_LENGTH].rstrip()

    return folder_name


# DDC top-level class names for folder labels
DDC_CLASS_NAMES = {
    "000": "Computer Science",
    "100": "Philosophy",
    "200": "Religion",
    "300": "Social Sciences",
    "400": "Language",
    "500": "Science",
    "600": "Technology",
    "700": "Arts",
    "800": "Literature",
    "900": "History",
}


def generate_path(
    ddc: str | None,
    folder_name: str,
    filename: str,
    library_root: Path,
    is_fiction: bool = False,
) -> Path:
    """
    Generate the full path for a file in the library.

    Structure:
    - Fiction: library_root/Fiction/FolderName/filename
    - Non-Fiction: library_root/Non-Fiction/DDD - ClassName/FolderName/filename

    Args:
        ddc: 3-digit DDC code (optional for fiction)
        folder_name: Item folder name (e.g., "Author - Title")
        filename: Generated filename with extension
        library_root: Root path of the library
        is_fiction: Whether this is a fiction item

    Returns:
        Full path for the file
    """
    if is_fiction:
        return library_root / "Fiction" / folder_name / filename
    else:
        # Build DDC folder name with human-readable label
        ddc_code = (ddc or "000").zfill(3)[:3]

        # Get top-level class (first digit)
        top_level = ddc_code[0] + "00"
        class_name = DDC_CLASS_NAMES.get(top_level, "General")

        ddc_folder = f"{ddc_code} - {class_name}"

        return library_root / "Non-Fiction" / ddc_folder / folder_name / filename


def ensure_unique_path(path: Path) -> Path:
    """
    Ensure a path is unique by adding a suffix if necessary.

    If "Author - Title.epub" exists, returns "Author - Title (2).epub"
    """
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent

    counter = 2
    while True:
        new_path = parent / f"{stem} ({counter}){suffix}"
        if not new_path.exists():
            return new_path
        counter += 1
        if counter > 100:  # Safety limit
            raise ValueError(f"Too many duplicates for {path}")
