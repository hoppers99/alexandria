"""File format detection."""

from pathlib import Path

# Mapping of file extensions to format names
EXTENSION_MAP = {
    # E-books
    ".epub": "epub",
    ".pdf": "pdf",
    ".mobi": "mobi",
    ".azw": "azw",
    ".azw3": "azw3",
    ".djvu": "djvu",
    # Comics
    ".cbz": "cbz",
    ".cbr": "cbr",
    # Audio
    ".mp3": "mp3",
    ".m4a": "m4a",
    ".m4b": "m4b",
    ".flac": "flac",
    ".ogg": "ogg",
    # Video
    ".mp4": "mp4",
    ".mkv": "mkv",
    ".avi": "avi",
}

# Formats we can extract metadata from
SUPPORTED_EBOOK_FORMATS = {"epub", "pdf", "mobi", "azw", "azw3"}
SUPPORTED_AUDIO_FORMATS = {"mp3", "m4a", "m4b", "flac", "ogg"}
SUPPORTED_VIDEO_FORMATS = {"mp4", "mkv", "avi"}


def detect_format(file_path: Path) -> str | None:
    """Detect file format from extension."""
    ext = file_path.suffix.lower()
    return EXTENSION_MAP.get(ext)


def is_ebook(format_name: str) -> bool:
    """Check if format is an e-book."""
    return format_name in SUPPORTED_EBOOK_FORMATS or format_name in {"djvu", "cbz", "cbr"}


def is_audio(format_name: str) -> bool:
    """Check if format is audio."""
    return format_name in SUPPORTED_AUDIO_FORMATS


def is_video(format_name: str) -> bool:
    """Check if format is video."""
    return format_name in SUPPORTED_VIDEO_FORMATS


def get_media_type(format_name: str) -> str:
    """Determine media type from format."""
    if format_name in SUPPORTED_EBOOK_FORMATS:
        return "book"
    if format_name in {"cbz", "cbr"}:
        return "book"  # Comics are books
    if format_name == "djvu":
        return "document"
    if format_name in {"m4b"}:
        return "audiobook"
    if format_name in SUPPORTED_AUDIO_FORMATS:
        return "audiobook"  # Assume audio files are audiobooks
    if format_name in SUPPORTED_VIDEO_FORMATS:
        return "video"
    return "document"
