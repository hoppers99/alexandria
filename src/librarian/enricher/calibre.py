"""Calibre database lookup for enriching metadata."""

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CalibreBook:
    """Book record from Calibre database."""

    id: int
    title: str
    authors: list[str] = field(default_factory=list)
    series: str | None = None
    series_index: float | None = None
    publisher: str | None = None
    isbn: str | None = None
    identifiers: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    description: str | None = None
    language: str | None = None
    path: str | None = None  # Relative path in Calibre library


def lookup_by_path(db_path: Path, file_path: Path, calibre_root: Path) -> CalibreBook | None:
    """
    Look up a book in Calibre by matching the file path.

    Args:
        db_path: Path to Calibre's metadata.db
        file_path: Full path to the ebook file
        calibre_root: Root directory of the Calibre library

    Returns:
        CalibreBook if found, None otherwise
    """
    if not db_path.exists():
        return None

    # Get relative path from Calibre root
    try:
        rel_path = file_path.relative_to(calibre_root)
    except ValueError:
        return None

    # In Calibre, the path in DB is just "Author/Title (id)"
    # The actual filename is in the 'data' table
    filename = file_path.stem  # Without extension
    file_format = file_path.suffix.lstrip(".").upper()

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Try to match by filename in the data table
        cursor.execute("""
            SELECT b.id, b.title, b.series_index, b.isbn, b.path
            FROM books b
            JOIN data d ON d.book = b.id
            WHERE d.name = ? AND d.format = ?
        """, (filename, file_format))

        row = cursor.fetchone()
        if not row:
            # Try matching by path pattern
            # Calibre paths are like "Author/Title (id)"
            parent_name = rel_path.parent.name
            cursor.execute("""
                SELECT b.id, b.title, b.series_index, b.isbn, b.path
                FROM books b
                WHERE b.path LIKE ?
            """, (f"%{parent_name}%",))
            row = cursor.fetchone()

        if not row:
            return None

        book_id = row["id"]

        # Get authors
        cursor.execute("""
            SELECT a.name FROM authors a
            JOIN books_authors_link bal ON bal.author = a.id
            WHERE bal.book = ?
            ORDER BY bal.id
        """, (book_id,))
        authors = [r["name"] for r in cursor.fetchall()]

        # Get series
        cursor.execute("""
            SELECT s.name FROM series s
            JOIN books_series_link bsl ON bsl.series = s.id
            WHERE bsl.book = ?
        """, (book_id,))
        series_row = cursor.fetchone()
        series = series_row["name"] if series_row else None

        # Get publisher
        cursor.execute("""
            SELECT p.name FROM publishers p
            JOIN books_publishers_link bpl ON bpl.publisher = p.id
            WHERE bpl.book = ?
        """, (book_id,))
        pub_row = cursor.fetchone()
        publisher = pub_row["name"] if pub_row else None

        # Get identifiers (including additional ISBNs)
        cursor.execute("""
            SELECT type, val FROM identifiers WHERE book = ?
        """, (book_id,))
        identifiers = {r["type"]: r["val"] for r in cursor.fetchall()}

        # Get tags
        cursor.execute("""
            SELECT t.name FROM tags t
            JOIN books_tags_link btl ON btl.tag = t.id
            WHERE btl.book = ?
        """, (book_id,))
        tags = [r["name"] for r in cursor.fetchall()]

        # Get description/comments
        cursor.execute("SELECT text FROM comments WHERE book = ?", (book_id,))
        comment_row = cursor.fetchone()
        description = comment_row["text"] if comment_row else None

        # Get language
        cursor.execute("""
            SELECT l.lang_code FROM languages l
            JOIN books_languages_link bll ON bll.lang_code = l.id
            WHERE bll.book = ?
        """, (book_id,))
        lang_row = cursor.fetchone()
        language = lang_row["lang_code"] if lang_row else None

        # Use ISBN from identifiers if not in main field
        isbn = row["isbn"] if row["isbn"] else identifiers.get("isbn")

        return CalibreBook(
            id=book_id,
            title=row["title"],
            authors=authors,
            series=series,
            series_index=row["series_index"] if series else None,
            publisher=publisher,
            isbn=isbn,
            identifiers=identifiers,
            tags=tags,
            description=description,
            language=language,
            path=row["path"],
        )

    finally:
        conn.close()


def _enrich_book_from_row(cursor: sqlite3.Cursor, row: sqlite3.Row) -> CalibreBook:
    """Fetch additional book details given a book row."""
    book_id = row["id"]

    # Get authors
    cursor.execute("""
        SELECT a.name FROM authors a
        JOIN books_authors_link bal ON bal.author = a.id
        WHERE bal.book = ?
        ORDER BY bal.id
    """, (book_id,))
    authors = [r["name"] for r in cursor.fetchall()]

    # Get series
    cursor.execute("""
        SELECT s.name FROM series s
        JOIN books_series_link bsl ON bsl.series = s.id
        WHERE bsl.book = ?
    """, (book_id,))
    series_row = cursor.fetchone()
    series = series_row["name"] if series_row else None

    # Get publisher
    cursor.execute("""
        SELECT p.name FROM publishers p
        JOIN books_publishers_link bpl ON bpl.publisher = p.id
        WHERE bpl.book = ?
    """, (book_id,))
    pub_row = cursor.fetchone()
    publisher = pub_row["name"] if pub_row else None

    # Get identifiers
    cursor.execute("SELECT type, val FROM identifiers WHERE book = ?", (book_id,))
    identifiers = {r["type"]: r["val"] for r in cursor.fetchall()}

    # Get tags
    cursor.execute("""
        SELECT t.name FROM tags t
        JOIN books_tags_link btl ON btl.tag = t.id
        WHERE btl.book = ?
    """, (book_id,))
    tags = [r["name"] for r in cursor.fetchall()]

    # Get description
    cursor.execute("SELECT text FROM comments WHERE book = ?", (book_id,))
    comment_row = cursor.fetchone()
    description = comment_row["text"] if comment_row else None

    # Get language
    cursor.execute("""
        SELECT l.lang_code FROM languages l
        JOIN books_languages_link bll ON bll.lang_code = l.id
        WHERE bll.book = ?
    """, (book_id,))
    lang_row = cursor.fetchone()
    language = lang_row["lang_code"] if lang_row else None

    isbn = row["isbn"] if row["isbn"] else identifiers.get("isbn")

    return CalibreBook(
        id=book_id,
        title=row["title"],
        authors=authors,
        series=series,
        series_index=row["series_index"] if series else None,
        publisher=publisher,
        isbn=isbn,
        identifiers=identifiers,
        tags=tags,
        description=description,
        language=language,
        path=row["path"],
    )


def lookup_by_isbn(db_path: Path, isbn: str) -> CalibreBook | None:
    """
    Look up a book in Calibre by ISBN.

    Args:
        db_path: Path to Calibre's metadata.db
        isbn: ISBN-10 or ISBN-13 to search for

    Returns:
        CalibreBook if found, None otherwise
    """
    if not db_path.exists():
        return None

    # Clean the ISBN
    clean_isbn = isbn.replace("-", "").replace(" ", "").upper()

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Search in identifiers table (most reliable)
        cursor.execute("""
            SELECT b.id, b.title, b.series_index, b.isbn, b.path
            FROM books b
            JOIN identifiers i ON i.book = b.id
            WHERE i.type = 'isbn' AND REPLACE(UPPER(i.val), '-', '') = ?
        """, (clean_isbn,))

        row = cursor.fetchone()

        # Also try the main isbn field in books table
        if not row:
            cursor.execute("""
                SELECT id, title, series_index, isbn, path
                FROM books
                WHERE REPLACE(UPPER(isbn), '-', '') = ?
            """, (clean_isbn,))
            row = cursor.fetchone()

        if not row:
            return None

        return _enrich_book_from_row(cursor, row)

    finally:
        conn.close()


def lookup_by_filename(db_path: Path, filename: str) -> CalibreBook | None:
    """
    Look up a book in Calibre by matching the filename.

    Searches the data table which contains format information for each book.

    Args:
        db_path: Path to Calibre's metadata.db
        filename: Filename to search for (with or without extension)

    Returns:
        CalibreBook if found, None otherwise
    """
    if not db_path.exists():
        return None

    # Remove extension if present
    name = Path(filename).stem
    file_format = Path(filename).suffix.lstrip(".").upper() if "." in filename else None

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Search by filename in the data table
        if file_format:
            cursor.execute("""
                SELECT b.id, b.title, b.series_index, b.isbn, b.path
                FROM books b
                JOIN data d ON d.book = b.id
                WHERE d.name = ? AND d.format = ?
            """, (name, file_format))
        else:
            cursor.execute("""
                SELECT b.id, b.title, b.series_index, b.isbn, b.path
                FROM books b
                JOIN data d ON d.book = b.id
                WHERE d.name = ?
            """, (name,))

        row = cursor.fetchone()

        # If no exact match, try fuzzy match on name
        if not row:
            cursor.execute("""
                SELECT b.id, b.title, b.series_index, b.isbn, b.path
                FROM books b
                JOIN data d ON d.book = b.id
                WHERE d.name LIKE ?
                LIMIT 1
            """, (f"%{name}%",))
            row = cursor.fetchone()

        if not row:
            return None

        return _enrich_book_from_row(cursor, row)

    finally:
        conn.close()


def lookup_by_title_author(
    db_path: Path,
    title: str,
    author: str | None = None,
) -> CalibreBook | None:
    """
    Look up a book in Calibre by title and optionally author.

    Args:
        db_path: Path to Calibre's metadata.db
        title: Book title to search for
        author: Author name (optional)

    Returns:
        CalibreBook if found, None otherwise
    """
    if not db_path.exists():
        return None

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        if author:
            cursor.execute("""
                SELECT b.id, b.title, b.series_index, b.isbn, b.path
                FROM books b
                JOIN books_authors_link bal ON bal.book = b.id
                JOIN authors a ON a.id = bal.author
                WHERE b.title LIKE ? AND a.name LIKE ?
                LIMIT 1
            """, (f"%{title}%", f"%{author}%"))
        else:
            cursor.execute("""
                SELECT b.id, b.title, b.series_index, b.isbn, b.path
                FROM books b
                WHERE b.title LIKE ?
                LIMIT 1
            """, (f"%{title}%",))

        row = cursor.fetchone()
        if not row:
            return None

        # Reuse the same enrichment logic
        book_id = row["id"]

        # Get authors
        cursor.execute("""
            SELECT a.name FROM authors a
            JOIN books_authors_link bal ON bal.author = a.id
            WHERE bal.book = ?
            ORDER BY bal.id
        """, (book_id,))
        authors = [r["name"] for r in cursor.fetchall()]

        # Get series
        cursor.execute("""
            SELECT s.name FROM series s
            JOIN books_series_link bsl ON bsl.series = s.id
            WHERE bsl.book = ?
        """, (book_id,))
        series_row = cursor.fetchone()
        series = series_row["name"] if series_row else None

        # Get publisher
        cursor.execute("""
            SELECT p.name FROM publishers p
            JOIN books_publishers_link bpl ON bpl.publisher = p.id
            WHERE bpl.book = ?
        """, (book_id,))
        pub_row = cursor.fetchone()
        publisher = pub_row["name"] if pub_row else None

        # Get identifiers
        cursor.execute("SELECT type, val FROM identifiers WHERE book = ?", (book_id,))
        identifiers = {r["type"]: r["val"] for r in cursor.fetchall()}

        # Get tags
        cursor.execute("""
            SELECT t.name FROM tags t
            JOIN books_tags_link btl ON btl.tag = t.id
            WHERE btl.book = ?
        """, (book_id,))
        tags = [r["name"] for r in cursor.fetchall()]

        # Get description
        cursor.execute("SELECT text FROM comments WHERE book = ?", (book_id,))
        comment_row = cursor.fetchone()
        description = comment_row["text"] if comment_row else None

        # Get language
        cursor.execute("""
            SELECT l.lang_code FROM languages l
            JOIN books_languages_link bll ON bll.lang_code = l.id
            WHERE bll.book = ?
        """, (book_id,))
        lang_row = cursor.fetchone()
        language = lang_row["lang_code"] if lang_row else None

        isbn = row["isbn"] if row["isbn"] else identifiers.get("isbn")

        return CalibreBook(
            id=book_id,
            title=row["title"],
            authors=authors,
            series=series,
            series_index=row["series_index"] if series else None,
            publisher=publisher,
            isbn=isbn,
            identifiers=identifiers,
            tags=tags,
            description=description,
            language=language,
            path=row["path"],
        )

    finally:
        conn.close()
