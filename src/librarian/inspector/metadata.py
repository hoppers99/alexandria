"""Metadata extraction from various file formats."""

import io
import logging
import re
import signal
import sys
import warnings
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ebooklib import epub
from mobi import Mobi
from pypdf import PdfReader


@contextmanager
def suppress_stderr() -> Iterator[None]:
    """Temporarily suppress stderr output (for noisy libraries)."""
    # Save the real stderr
    old_stderr = sys.stderr
    # Redirect stderr to devnull
    sys.stderr = io.StringIO()
    try:
        yield
    finally:
        # Restore stderr
        sys.stderr = old_stderr


class ExtractionTimeout(Exception):
    """Raised when metadata extraction times out."""

    pass


def _timeout_handler(signum: int, frame: Any) -> None:
    raise ExtractionTimeout("Metadata extraction timed out")


# ISBN patterns - separate for ISBN-13 and ISBN-10
ISBN13_PATTERN = re.compile(
    r"(?:ISBN[-: ]?(?:13)?[-: ]?)?"  # Optional ISBN-13 prefix
    r"(97[89][-\s]?(?:\d[-\s]?){9}\d)",  # ISBN-13: 978/979 + 10 more digits
    re.IGNORECASE
)

ISBN10_PATTERN = re.compile(
    r"(?:ISBN[-: ]?(?:10)?[-: ]?)?"  # Optional ISBN-10 prefix
    r"(\d[-\s]?(?:\d[-\s]?){8}[\dX])",  # ISBN-10: 10 digits (last can be X)
    re.IGNORECASE
)


def extract_isbns_from_text(text: str) -> list[str]:
    """Extract all valid ISBNs from text."""
    isbns = []

    # Find ISBN-13s first (they're more specific)
    for match in ISBN13_PATTERN.finditer(text):
        isbn = re.sub(r"[-\s]", "", match.group(1)).upper()
        if len(isbn) == 13 and isbn not in isbns:
            isbns.append(isbn)

    # Find ISBN-10s, but exclude any that are substrings of found ISBN-13s
    for match in ISBN10_PATTERN.finditer(text):
        isbn = re.sub(r"[-\s]", "", match.group(1)).upper()
        if len(isbn) == 10 and isbn not in isbns:
            # Check it's not part of an ISBN-13 we already found
            is_substring = any(isbn in isbn13 for isbn13 in isbns if len(isbn13) == 13)
            if not is_substring:
                isbns.append(isbn)

    return isbns


@dataclass
class ExtractedMetadata:
    """Metadata extracted from a file."""

    title: str | None = None
    authors: list[str] = field(default_factory=list)
    isbns: list[str] = field(default_factory=list)  # All ISBNs found (10 or 13 digit)
    description: str | None = None
    publisher: str | None = None
    publish_date: str | None = None
    language: str | None = None
    subjects: list[str] = field(default_factory=list)
    series: str | None = None
    series_index: float | None = None
    cover_data: bytes | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    # Legacy accessors for backward compatibility
    @property
    def isbn(self) -> str | None:
        """Return first ISBN-10 found, or None."""
        for isbn in self.isbns:
            if len(isbn) == 10:
                return isbn
        return None

    @property
    def isbn13(self) -> str | None:
        """Return first ISBN-13 found, or None."""
        for isbn in self.isbns:
            if len(isbn) == 13:
                return isbn
        return None


def extract_epub_metadata(file_path: Path) -> ExtractedMetadata:
    """Extract metadata from an EPUB file."""
    metadata = ExtractedMetadata()

    try:
        book = epub.read_epub(str(file_path), options={"ignore_ncx": True})

        # Title
        title_list = book.get_metadata("DC", "title")
        if title_list:
            metadata.title = title_list[0][0]

        # Authors
        creators = book.get_metadata("DC", "creator")
        for creator in creators:
            if creator[0]:
                metadata.authors.append(creator[0])

        # ISBN - check identifiers
        identifiers = book.get_metadata("DC", "identifier")
        for identifier in identifiers:
            value = identifier[0] if identifier else None
            if value:
                # Check if it's an ISBN
                cleaned = re.sub(r"[^0-9X]", "", value.upper())
                if len(cleaned) == 13 and cleaned.startswith("978"):
                    if cleaned not in metadata.isbns:
                        metadata.isbns.append(cleaned)
                elif len(cleaned) == 10:
                    if cleaned not in metadata.isbns:
                        metadata.isbns.append(cleaned)
                # Also check for urn:isbn: prefix
                if value.lower().startswith("urn:isbn:"):
                    isbn_val = value[9:]
                    cleaned = re.sub(r"[^0-9X]", "", isbn_val.upper())
                    if len(cleaned) in (10, 13) and cleaned not in metadata.isbns:
                        metadata.isbns.append(cleaned)

        # Description
        descriptions = book.get_metadata("DC", "description")
        if descriptions:
            metadata.description = descriptions[0][0]

        # Publisher
        publishers = book.get_metadata("DC", "publisher")
        if publishers:
            metadata.publisher = publishers[0][0]

        # Date
        dates = book.get_metadata("DC", "date")
        if dates:
            metadata.publish_date = dates[0][0]

        # Language
        languages = book.get_metadata("DC", "language")
        if languages:
            metadata.language = languages[0][0]

        # Subjects
        subjects = book.get_metadata("DC", "subject")
        for subject in subjects:
            if subject[0]:
                metadata.subjects.append(subject[0])

        # Try to extract series from calibre metadata
        calibre_series = book.get_metadata("OPF", "meta")
        for meta in calibre_series:
            attrs = meta[1] if len(meta) > 1 else {}
            if attrs.get("name") == "calibre:series":
                metadata.series = attrs.get("content")
            if attrs.get("name") == "calibre:series_index":
                try:
                    metadata.series_index = float(attrs.get("content", 0))
                except ValueError:
                    pass

        # Try to extract cover
        for item in book.get_items():
            if item.get_type() == epub.ITEM_COVER:
                metadata.cover_data = item.get_content()
                break
            # Fallback: look for cover image by name
            if "cover" in item.get_name().lower() and item.media_type.startswith(
                "image/"
            ):
                metadata.cover_data = item.get_content()

    except Exception as e:
        metadata.raw["extraction_error"] = str(e)

    return metadata


def extract_pdf_metadata(file_path: Path, timeout_seconds: int = 30) -> ExtractedMetadata:
    """Extract metadata from a PDF file with timeout protection."""
    metadata = ExtractedMetadata()

    # Set up timeout
    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(timeout_seconds)

    # Suppress pypdf warnings about malformed PDFs (e.g., "Ignoring wrong pointing object")
    # These are common in scanned/converted PDFs and don't prevent extraction
    pypdf_logger = logging.getLogger("pypdf")
    original_level = pypdf_logger.level
    pypdf_logger.setLevel(logging.ERROR)

    # Also suppress pypdf._reader logger which prints directly
    pypdf_reader_logger = logging.getLogger("pypdf._reader")
    reader_original_level = pypdf_reader_logger.level
    pypdf_reader_logger.setLevel(logging.ERROR)

    try:
        with warnings.catch_warnings(), suppress_stderr():
            warnings.filterwarnings("ignore", category=UserWarning, module="pypdf")
            warnings.filterwarnings("ignore", category=DeprecationWarning, module="pypdf")

            # Use strict=False to be more lenient with malformed PDFs
            reader = PdfReader(str(file_path), strict=False)
            info = reader.metadata

            if info:
                metadata.title = info.title
                if info.author:
                    # Split on common separators
                    authors = re.split(r"[,;&]|\band\b", info.author)
                    metadata.authors = [a.strip() for a in authors if a.strip()]
                metadata.raw = {k: str(v) for k, v in info.items() if v}

            # Extract ISBNs from first and last few pages
            num_pages = len(reader.pages)
            pages_to_check = []

            # First 5 pages (title page, copyright page, etc.)
            pages_to_check.extend(range(min(5, num_pages)))

            # Last 5 pages (often have publisher info)
            if num_pages > 5:
                pages_to_check.extend(range(max(5, num_pages - 5), num_pages))

            for page_num in pages_to_check:
                try:
                    page = reader.pages[page_num]
                    text = page.extract_text() or ""
                    found_isbns = extract_isbns_from_text(text)
                    for isbn in found_isbns:
                        if isbn not in metadata.isbns:
                            metadata.isbns.append(isbn)
                except Exception:
                    # Skip problematic pages
                    continue

    except ExtractionTimeout:
        metadata.raw["extraction_error"] = "Timeout: PDF took too long to parse"
    except Exception as e:
        metadata.raw["extraction_error"] = str(e)
    finally:
        # Cancel the alarm and restore old handler
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
        # Restore original logging levels
        pypdf_logger.setLevel(original_level)
        pypdf_reader_logger.setLevel(reader_original_level)

    return metadata


def extract_mobi_metadata(file_path: Path) -> ExtractedMetadata:
    """Extract metadata from a MOBI file."""
    metadata = ExtractedMetadata()

    try:
        book = Mobi(str(file_path))
        book.parse()

        # Title (returns bytes)
        title = book.title()
        if title:
            metadata.title = title.decode("utf-8", errors="replace") if isinstance(title, bytes) else title

        # Author (returns bytes, often in "Last, First" format)
        author = book.author()
        if author:
            author_str = author.decode("utf-8", errors="replace") if isinstance(author, bytes) else author
            # Handle "Last, First" format
            if ", " in author_str:
                parts = author_str.split(", ", 1)
                if len(parts) == 2:
                    author_str = f"{parts[1]} {parts[0]}"
            metadata.authors = [author_str]

        # Try to get publisher
        try:
            publisher = book.publisher()
            if publisher:
                metadata.publisher = publisher.decode("utf-8", errors="replace") if isinstance(publisher, bytes) else publisher
        except (AttributeError, TypeError):
            pass

        # Try to get ISBN from EXTH records
        try:
            # EXTH records are stored in book.config['exth']['records'] as a dict
            # Record types: 104 = ASIN (often ISBN-10), 172 = ISBN
            exth_records = book.config.get("exth", {}).get("records", {})

            for record_type in (104, 172):  # Check both ASIN and ISBN fields
                if record_type in exth_records:
                    value = exth_records[record_type]
                    isbn_val = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)
                    cleaned = re.sub(r"[^0-9X]", "", isbn_val.upper())
                    if len(cleaned) in (10, 13) and cleaned not in metadata.isbns:
                        metadata.isbns.append(cleaned)
        except (AttributeError, TypeError, KeyError):
            pass

    except Exception as e:
        metadata.raw["extraction_error"] = str(e)

    return metadata


def parse_opf_file(opf_path: Path) -> ExtractedMetadata:
    """
    Parse metadata from an OPF (Open Packaging Format) file.

    These are XML files created by Calibre and other ebook managers
    containing Dublin Core metadata.

    Args:
        opf_path: Path to the .opf file

    Returns:
        ExtractedMetadata with parsed information
    """
    metadata = ExtractedMetadata()

    try:
        tree = ET.parse(opf_path)
        root = tree.getroot()

        # Handle namespaces
        ns = {
            "opf": "http://www.idpf.org/2007/opf",
            "dc": "http://purl.org/dc/elements/1.1/",
        }

        # Find metadata element (might be namespaced or not)
        meta_elem = root.find("opf:metadata", ns) or root.find("metadata")
        if meta_elem is None:
            return metadata

        # Title
        title_elem = meta_elem.find("dc:title", ns)
        if title_elem is not None and title_elem.text:
            metadata.title = title_elem.text.strip()

        # Authors/creators
        for creator in meta_elem.findall("dc:creator", ns):
            if creator.text:
                author = creator.text.strip()
                # Check for file-as attribute which might have "Last, First"
                file_as = creator.get(f"{{{ns['opf']}}}file-as")
                if file_as and ", " in file_as:
                    # Use the display name from element text
                    pass
                metadata.authors.append(author)

        # Publisher
        pub_elem = meta_elem.find("dc:publisher", ns)
        if pub_elem is not None and pub_elem.text:
            metadata.publisher = pub_elem.text.strip()

        # Language
        lang_elem = meta_elem.find("dc:language", ns)
        if lang_elem is not None and lang_elem.text:
            metadata.language = lang_elem.text.strip()

        # Description
        desc_elem = meta_elem.find("dc:description", ns)
        if desc_elem is not None and desc_elem.text:
            metadata.description = desc_elem.text.strip()

        # Identifiers (ISBN, etc.)
        for identifier in meta_elem.findall("dc:identifier", ns):
            if identifier.text:
                val = identifier.text.strip()
                scheme = identifier.get(f"{{{ns['opf']}}}scheme", "").lower()

                # Check for ISBN
                if scheme == "isbn" or val.lower().startswith("isbn"):
                    cleaned = re.sub(r"[^0-9X]", "", val.upper())
                    if len(cleaned) in (10, 13) and cleaned not in metadata.isbns:
                        metadata.isbns.append(cleaned)
                else:
                    # Try to extract ISBN from any identifier
                    cleaned = re.sub(r"[^0-9X]", "", val.upper())
                    if len(cleaned) == 13 and cleaned.startswith(("978", "979")):
                        if cleaned not in metadata.isbns:
                            metadata.isbns.append(cleaned)
                    elif len(cleaned) == 10:
                        if cleaned not in metadata.isbns:
                            metadata.isbns.append(cleaned)

        # Calibre-specific metadata (series info)
        for meta in meta_elem.findall("opf:meta", ns) or meta_elem.findall("meta"):
            name = meta.get("name", "")
            content = meta.get("content", "")

            if name == "calibre:series" and content:
                metadata.series = content
            elif name == "calibre:series_index" and content:
                try:
                    metadata.series_index = float(content)
                except ValueError:
                    pass

        # Subjects
        for subject in meta_elem.findall("dc:subject", ns):
            if subject.text:
                metadata.subjects.append(subject.text.strip())

    except Exception as e:
        metadata.raw["opf_error"] = str(e)

    return metadata


def find_opf_in_directory(file_path: Path) -> Path | None:
    """Find an OPF file in the same directory as the ebook."""
    directory = file_path.parent
    for opf_file in directory.glob("*.opf"):
        return opf_file
    return None


def parse_filename(filepath: Path) -> ExtractedMetadata:
    """
    Parse metadata from filename and path structure.

    Handles common patterns:
    - "Author - Title.ext"
    - "Author - Series NN - Title.ext"
    - "Title by Author/filename.ext" (folder structure)
    - "Series NN - Title.ext"

    Args:
        filepath: Full path to the file

    Returns:
        ExtractedMetadata with parsed information
    """
    metadata = ExtractedMetadata()
    filename = filepath.stem  # Without extension
    parent_folder = filepath.parent.name

    # Try to extract from parent folder first (e.g., "Last to Die by Tess Gerritsen")
    folder_by_match = re.match(r"(.+?)\s+by\s+(.+)", parent_folder, re.IGNORECASE)
    if folder_by_match:
        metadata.title = folder_by_match.group(1).strip()
        metadata.authors = [folder_by_match.group(2).strip()]

    # Now parse the filename for more details
    # Pattern: "Series NN - Title" (from filename like "Rizzoli & Isles 10 - Last to Die")
    series_title_match = re.match(r"(.+?)\s+(\d+)\s*[-–]\s*(.+)", filename)
    if series_title_match:
        metadata.series = series_title_match.group(1).strip()
        try:
            metadata.series_index = float(series_title_match.group(2))
        except ValueError:
            pass
        # Only override title if we didn't get one from folder
        if not metadata.title:
            metadata.title = series_title_match.group(3).strip()
    else:
        # Pattern: "Author - Title" or "Author - Series NN - Title"
        parts = re.split(r"\s*[-–]\s*", filename)

        if len(parts) >= 2:
            # First part is usually author
            potential_author = parts[0].strip()

            # Check if it looks like an author (not a series number)
            if not re.match(r"^\d+$", potential_author):
                if not metadata.authors:
                    metadata.authors = [potential_author]

                # Check if middle part is "Series NN"
                if len(parts) >= 3:
                    series_match = re.match(r"(.+?)\s+(\d+)", parts[1].strip())
                    if series_match:
                        metadata.series = series_match.group(1).strip()
                        try:
                            metadata.series_index = float(series_match.group(2))
                        except ValueError:
                            pass
                        if not metadata.title:
                            metadata.title = parts[2].strip()
                    else:
                        # Just "Author - Something - Title"
                        if not metadata.title:
                            metadata.title = parts[-1].strip()
                else:
                    # Just "Author - Title"
                    if not metadata.title:
                        metadata.title = parts[1].strip()

    # Clean up title (remove common cruft)
    if metadata.title:
        # Remove bracketed content like [scan], (epub), etc.
        metadata.title = re.sub(r"\s*[\[\(][^\]\)]*[\]\)]\s*", " ", metadata.title).strip()

    return metadata


def extract_metadata(file_path: Path, file_format: str) -> ExtractedMetadata:
    """Extract metadata from a file based on its format."""
    if file_format == "epub":
        metadata = extract_epub_metadata(file_path)
    elif file_format == "pdf":
        metadata = extract_pdf_metadata(file_path)
    elif file_format == "mobi":
        metadata = extract_mobi_metadata(file_path)
    else:
        metadata = ExtractedMetadata()

    # Check for OPF file in the same directory (Calibre metadata)
    opf_path = find_opf_in_directory(file_path)
    if opf_path:
        opf_meta = parse_opf_file(opf_path)

        # OPF is often more reliable, so prefer it for missing data
        if not metadata.title and opf_meta.title:
            metadata.title = opf_meta.title
        if not metadata.authors and opf_meta.authors:
            metadata.authors = opf_meta.authors
        if not metadata.series and opf_meta.series:
            metadata.series = opf_meta.series
        if metadata.series_index is None and opf_meta.series_index is not None:
            metadata.series_index = opf_meta.series_index
        if not metadata.publisher and opf_meta.publisher:
            metadata.publisher = opf_meta.publisher
        if not metadata.language and opf_meta.language:
            metadata.language = opf_meta.language
        if not metadata.description and opf_meta.description:
            metadata.description = opf_meta.description
        if not metadata.subjects and opf_meta.subjects:
            metadata.subjects = opf_meta.subjects

        # Add any ISBNs from OPF
        for isbn in opf_meta.isbns:
            if isbn not in metadata.isbns:
                metadata.isbns.append(isbn)

    # Parse filename for additional metadata (always, to get series info etc.)
    filename_meta = parse_filename(file_path)

    # Fill in any missing metadata from filename
    if not metadata.title and filename_meta.title:
        metadata.title = filename_meta.title
    if not metadata.authors and filename_meta.authors:
        metadata.authors = filename_meta.authors
    if not metadata.series and filename_meta.series:
        metadata.series = filename_meta.series
    if metadata.series_index is None and filename_meta.series_index is not None:
        metadata.series_index = filename_meta.series_index

    return metadata
