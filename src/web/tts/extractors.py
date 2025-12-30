"""Text extraction from ebook formats for TTS."""

import re
from pathlib import Path
from typing import TypedDict

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub


class Chapter(TypedDict):
    """Chapter metadata and content."""

    number: int
    title: str
    text: str
    word_count: int
    estimated_duration_seconds: float


class EPUBExtractor:
    """Extract clean text from EPUB files for TTS generation."""

    # Average words per minute for TTS (typical is 150-170 wpm)
    WORDS_PER_MINUTE = 150

    # Patterns to detect frontmatter/backmatter that should be skipped
    SKIP_PATTERNS = [
        # Frontmatter
        r"^(copyright|title page|half.?title|frontispiece)$",
        r"^(dedication|acknowledgements?|acknowledgments?)$",
        r"^(table of contents|contents|toc)$",
        r"^(foreword|preface|introduction)$",
        r"^(prologue|epigraph)$",
        # Backmatter
        r"^(epilogue|afterword|postscript)$",
        r"^(appendix|notes?|endnotes?|footnotes?)$",
        r"^(glossary|bibliography|references|index)$",
        r"^(about the author|about the book|also by)$",
        r"^(advertisement|preview|excerpt)$",
        # Publisher stuff
        r"^(by the same author|books? by|other.?titles)$",
        r"^(coming soon|newsletter|connect with)$",
    ]

    # Copyright indicators in text
    COPYRIGHT_INDICATORS = [
        "all rights reserved",
        "copyright ©",
        "published by",
        "isbn",
        "cataloging-in-publication",
        "library of congress",
    ]

    def __init__(self, epub_path: str | Path):
        """Initialize extractor with EPUB file path.

        Args:
            epub_path: Path to the EPUB file
        """
        self.epub_path = Path(epub_path)
        self.book = epub.read_epub(str(epub_path))

    def _should_skip_chapter(self, title: str, text: str) -> bool:
        """Check if a chapter should be skipped based on title or content.

        Args:
            title: Chapter title
            text: Chapter text content

        Returns:
            True if chapter should be skipped
        """
        # Normalize title for pattern matching
        title_normalized = title.lower().strip()

        # Check if title matches skip patterns
        for pattern in self.SKIP_PATTERNS:
            if re.match(pattern, title_normalized, re.IGNORECASE):
                return True

        # Skip placeholder titles like [ONE], [TWO], etc.
        if re.match(r'^\[.*\]$', title):
            return True

        # Check if text is too short (likely not a real chapter)
        # Increased threshold - real chapters typically have at least 500 words
        word_count = len(text.split())
        if word_count < 200:
            return True

        # Check for copyright indicators in text
        text_lower = text.lower()
        copyright_count = sum(
            1 for indicator in self.COPYRIGHT_INDICATORS if indicator in text_lower
        )

        # If text has multiple copyright indicators and is short, it's likely legal text
        if copyright_count >= 2 and word_count < 500:
            return True

        return False

    def get_chapters(self) -> list[Chapter]:
        """Extract all chapters using the EPUB's table of contents.

        Returns:
            List of chapters with title, text, and metadata
        """
        chapters: list[Chapter] = []

        # Get TOC structure
        toc = self.book.toc

        # If TOC is empty, fall back to document items
        if not toc:
            return self._get_chapters_from_spine()

        # Flatten TOC (handle nested sections)
        def flatten_toc(items, depth=0):
            flat = []
            for item in items:
                if isinstance(item, tuple):
                    # (section, subsections)
                    flat.append(item[0])
                    flat.extend(flatten_toc(item[1], depth + 1))
                elif isinstance(item, list):
                    flat.extend(flatten_toc(item, depth))
                else:
                    # Single item
                    flat.append(item)
            return flat

        toc_items = flatten_toc(toc)

        # Process each TOC entry
        for idx, toc_item in enumerate(toc_items):
            try:
                # Get the href from TOC item
                if hasattr(toc_item, 'href'):
                    href = toc_item.href.split('#')[0]  # Remove anchor
                    title = toc_item.title
                else:
                    continue

                # Find the corresponding item in the book
                item = self.book.get_item_with_href(href)
                if not item:
                    continue

                # Parse HTML content
                content = item.get_content()
                soup = BeautifulSoup(content, "lxml")

                # Get clean text suitable for TTS
                text = self._clean_html_for_tts(soup)

                # Skip frontmatter/backmatter and non-content chapters
                if self._should_skip_chapter(title, text):
                    continue

                # Calculate metadata
                word_count = len(text.split())
                duration_estimate = (word_count / self.WORDS_PER_MINUTE) * 60

                chapters.append(
                    {
                        "number": len(chapters) + 1,
                        "title": title or f"Chapter {len(chapters) + 1}",
                        "text": text,
                        "word_count": word_count,
                        "estimated_duration_seconds": duration_estimate,
                    }
                )
            except Exception as e:
                # Skip problematic TOC entries
                continue

        # If TOC gave us very few chapters, it might be sparse - try spine instead
        # Many EPUBs only have TOC entries for major sections, not every chapter
        if len(chapters) < 5:
            spine_chapters = self._get_chapters_from_spine()
            # Use spine result if it found significantly more chapters
            if len(spine_chapters) > len(chapters):
                return spine_chapters

        return chapters if chapters else self._get_chapters_from_spine()

    def _get_chapters_from_spine(self) -> list[Chapter]:
        """Fallback method: Extract chapters from spine (reading order).

        Returns:
            List of chapters
        """
        chapters: list[Chapter] = []

        # Get all document items in reading order
        for item in self.book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            # Parse HTML content
            content = item.get_content()
            soup = BeautifulSoup(content, "lxml")

            # Extract chapter title
            title = self._extract_title(soup, len(chapters) + 1)

            # Get clean text suitable for TTS
            text = self._clean_html_for_tts(soup)

            # Skip frontmatter/backmatter and non-content chapters
            if self._should_skip_chapter(title, text):
                continue

            # Calculate metadata
            word_count = len(text.split())
            duration_estimate = (word_count / self.WORDS_PER_MINUTE) * 60

            chapters.append(
                {
                    "number": len(chapters) + 1,
                    "title": title,
                    "text": text,
                    "word_count": word_count,
                    "estimated_duration_seconds": duration_estimate,
                }
            )

        return chapters

    def get_chapter(self, chapter_number: int) -> Chapter | None:
        """Get a specific chapter by number.

        Args:
            chapter_number: 1-indexed chapter number

        Returns:
            Chapter data or None if not found
        """
        chapters = self.get_chapters()
        if 0 < chapter_number <= len(chapters):
            return chapters[chapter_number - 1]
        return None

    def _is_chapter_title(self, title: str) -> bool:
        """Check if a title represents a chapter (not a scene/section).

        Args:
            title: Potential chapter title

        Returns:
            True if this looks like a chapter title
        """
        # Roman numerals (I, II, III, etc.) - common chapter markers
        if re.match(r'^[IVXLCDM]+$', title.strip()):
            return True

        # "Chapter N" style
        if re.match(r'^chapter\s+\d+', title.lower().strip()):
            return True

        # Just a number
        if re.match(r'^\d+$', title.strip()):
            return True

        # Location/date scene headings are NOT chapters
        # e.g., "Marburg an der Lahn, Germany 8 November 1942"
        if re.search(r'\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}', title):
            return False

        return False

    def _extract_title(self, soup: BeautifulSoup, chapter_num: int) -> str:
        """Extract chapter/scene title from HTML.

        Args:
            soup: BeautifulSoup parsed HTML
            chapter_num: Fallback chapter number

        Returns:
            Chapter/scene title or default
        """
        # Try to find title in h1, h2, h3 tags (includes scene headings)
        for tag in ["h1", "h2", "h3"]:
            heading = soup.find(tag)
            if heading:
                title = heading.get_text().strip()
                # Skip placeholder titles like [ONE], [TWO]
                if title and not re.match(r'^\[.*\]$', title):
                    return title

        # Try <title> tag
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text().strip()
            # Skip placeholder titles
            if title and not re.match(r'^\[.*\]$', title):
                return title

        # Look for Roman numerals at the start of content (common chapter style)
        # Try to find first paragraph or div with text
        for element in soup.find_all(['p', 'div'], limit=10):
            text = element.get_text().strip()
            # Check if it's a Roman numeral (I, II, III, IV, V, etc.)
            if text and re.match(r'^[IVXLCDM]+$', text) and len(text) <= 10:
                return text

        # Fallback to generic section number
        return f"Section {chapter_num}"

    def _clean_html_for_tts(self, soup: BeautifulSoup) -> str:
        """Clean HTML content for optimal TTS output.

        Removes navigation, scripts, styles, footnotes, and formats text
        for natural speech synthesis.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Cleaned text ready for TTS
        """
        # Remove elements that should not be read
        for tag in soup(
            [
                "script",
                "style",
                "nav",
                "header",
                "footer",
                "aside",
                "sup",  # Superscript (footnote markers)
                "sub",  # Subscript
                "button",
                "form",
            ]
        ):
            tag.decompose()

        # Remove common ebook navigation elements
        for nav_class in ["toc", "nav", "navigation", "footnotes", "endnotes"]:
            for element in soup.find_all(class_=re.compile(nav_class, re.I)):
                element.decompose()

        # Get text content
        text = soup.get_text()

        # Clean up whitespace
        # Replace multiple newlines with maximum two
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        # Replace multiple spaces with single space
        text = re.sub(r" +", " ", text)
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)

        # Prepare text for better TTS pronunciation
        text = self._prepare_for_tts(text)

        return text.strip()

    def _prepare_for_tts(self, text: str) -> str:
        """Prepare text for better TTS pronunciation.

        Expands abbreviations, fixes punctuation, and adds natural pauses.

        Args:
            text: Raw text content

        Returns:
            Text optimized for TTS
        """
        # Expand common abbreviations that TTS might mispronounce
        # These are common in fiction and narrative
        replacements = {
            # Titles and honorifics
            r"\bMr\.": "Mister",
            r"\bMrs\.": "Missus",
            r"\bMs\.": "Miss",
            r"\bDr\.": "Doctor",
            r"\bProf\.": "Professor",
            r"\bRev\.": "Reverend",
            r"\bSt\.": "Saint",
            # Common abbreviations
            r"\betc\.": "etcetera",
            r"\bvs\.": "versus",
            r"\be\.g\.": "for example",
            r"\bi\.e\.": "that is",
            # Fix ellipsis
            r"\.\.\.": "…",  # Convert to proper ellipsis character
        }

        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Handle dialogue attribution for better pacing
        # Move comma inside quotes for natural pause
        text = re.sub(r'," ', '", ', text)
        text = re.sub(r"\,' ", "', ", text)

        # Add slight pause markers for paragraph breaks
        # This helps TTS with natural pacing
        text = re.sub(r"\n\n+", "\n\n... ", text)

        # Handle chapter/section breaks (*** or ---)
        text = re.sub(r"(\*\*\*|---)\s*", "... ", text)

        # Clean up any multiple spaces introduced
        text = re.sub(r" +", " ", text)

        return text


class MOBIExtractor:
    """Extract clean text from MOBI files for TTS generation.

    Note: MOBI support requires conversion. For now, we recommend
    converting MOBI to EPUB using Calibre first, or we can implement
    mobi-python extraction if needed.
    """

    def __init__(self, mobi_path: str | Path):
        """Initialize extractor with MOBI file path.

        Args:
            mobi_path: Path to the MOBI file
        """
        self.mobi_path = Path(mobi_path)
        raise NotImplementedError(
            "MOBI extraction not yet implemented. "
            "Please convert to EPUB using Calibre, or use mobi-python library."
        )

    def get_chapters(self) -> list[Chapter]:
        """Extract chapters from MOBI file."""
        raise NotImplementedError("MOBI extraction not yet implemented")


def get_extractor(file_path: str | Path) -> EPUBExtractor | MOBIExtractor:
    """Get the appropriate extractor for a file.

    Args:
        file_path: Path to the ebook file

    Returns:
        Extractor instance for the file type

    Raises:
        ValueError: If file format is not supported
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    if suffix == ".epub":
        return EPUBExtractor(file_path)
    elif suffix in [".mobi", ".azw", ".azw3"]:
        return MOBIExtractor(file_path)
    else:
        raise ValueError(f"Unsupported format: {suffix}. Only EPUB and MOBI are supported.")
