"""Google Books API client for metadata enrichment."""

from dataclasses import dataclass, field
from typing import Any

import httpx

GOOGLE_BOOKS_API_BASE = "https://www.googleapis.com/books/v1"


@dataclass
class GoogleBooksResult:
    """Result from Google Books API lookup."""

    title: str | None = None
    subtitle: str | None = None
    authors: list[str] = field(default_factory=list)
    publisher: str | None = None
    publish_date: str | None = None
    description: str | None = None
    categories: list[str] = field(default_factory=list)
    isbn_10: str | None = None
    isbn_13: str | None = None
    page_count: int | None = None
    language: str | None = None
    cover_url: str | None = None
    google_books_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


async def lookup_by_isbn(isbn: str, client: httpx.AsyncClient) -> GoogleBooksResult | None:
    """
    Look up a book by ISBN using Google Books API.

    Args:
        isbn: ISBN-10 or ISBN-13
        client: httpx AsyncClient

    Returns:
        GoogleBooksResult if found, None otherwise
    """
    clean_isbn = isbn.replace("-", "").replace(" ", "")

    try:
        response = await client.get(
            f"{GOOGLE_BOOKS_API_BASE}/volumes",
            params={"q": f"isbn:{clean_isbn}"},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("totalItems", 0) == 0:
            return None

        return _parse_volume(data["items"][0])

    except httpx.HTTPError:
        return None


async def lookup_by_title_author(
    title: str,
    author: str | None,
    client: httpx.AsyncClient,
) -> GoogleBooksResult | None:
    """
    Search for a book by title and author.

    Args:
        title: Book title
        author: Author name (optional)
        client: httpx AsyncClient

    Returns:
        GoogleBooksResult if found, None otherwise
    """
    results = await search_by_title_author(title, author, client, max_results=1)
    return results[0] if results else None


async def search_by_title_author(
    title: str,
    author: str | None,
    client: httpx.AsyncClient,
    max_results: int = 5,
) -> list[GoogleBooksResult]:
    """
    Search for books by title and author, returning multiple results.

    Args:
        title: Book title
        author: Author name (optional)
        client: httpx AsyncClient
        max_results: Maximum number of results to return (default 5)

    Returns:
        List of GoogleBooksResult, may be empty
    """
    try:
        query = f'intitle:"{title}"'
        if author:
            query += f' inauthor:"{author}"'

        response = await client.get(
            f"{GOOGLE_BOOKS_API_BASE}/volumes",
            params={"q": query, "maxResults": str(max_results)},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("totalItems", 0) == 0:
            return []

        return [_parse_volume(item) for item in data.get("items", [])]

    except httpx.HTTPError:
        return []


def _parse_volume(item: dict[str, Any]) -> GoogleBooksResult:
    """Parse a Google Books volume into GoogleBooksResult."""
    volume_info = item.get("volumeInfo", {})

    result = GoogleBooksResult(
        title=volume_info.get("title"),
        subtitle=volume_info.get("subtitle"),
        authors=volume_info.get("authors", []),
        publisher=volume_info.get("publisher"),
        publish_date=volume_info.get("publishedDate"),
        description=volume_info.get("description"),
        categories=volume_info.get("categories", []),
        page_count=volume_info.get("pageCount"),
        language=volume_info.get("language"),
        google_books_id=item.get("id"),
        raw=item,
    )

    # Extract ISBNs
    for identifier in volume_info.get("industryIdentifiers", []):
        if identifier.get("type") == "ISBN_10":
            result.isbn_10 = identifier.get("identifier")
        elif identifier.get("type") == "ISBN_13":
            result.isbn_13 = identifier.get("identifier")

    # Get cover URL (prefer larger image)
    image_links = volume_info.get("imageLinks", {})
    for size in ["extraLarge", "large", "medium", "thumbnail"]:
        if size in image_links:
            # Replace http with https and remove edge=curl parameter
            url = image_links[size].replace("http://", "https://")
            url = url.replace("&edge=curl", "")
            result.cover_url = url
            break

    return result
