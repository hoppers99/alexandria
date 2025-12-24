"""Open Library API client for metadata enrichment."""

from dataclasses import dataclass, field
from typing import Any

import httpx

OPENLIBRARY_API_BASE = "https://openlibrary.org"
OPENLIBRARY_COVERS_BASE = "https://covers.openlibrary.org"


@dataclass
class OpenLibraryResult:
    """Result from Open Library API lookup."""

    title: str | None = None
    authors: list[str] = field(default_factory=list)
    publishers: list[str] = field(default_factory=list)
    publish_date: str | None = None
    description: str | None = None
    subjects: list[str] = field(default_factory=list)
    isbn_10: list[str] = field(default_factory=list)
    isbn_13: list[str] = field(default_factory=list)
    ddc: list[str] = field(default_factory=list)
    lcc: list[str] = field(default_factory=list)
    cover_url: str | None = None
    openlibrary_key: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


async def lookup_by_isbn(isbn: str, client: httpx.AsyncClient) -> OpenLibraryResult | None:
    """
    Look up a book by ISBN using Open Library API.

    Args:
        isbn: ISBN-10 or ISBN-13
        client: httpx AsyncClient for making requests

    Returns:
        OpenLibraryResult if found, None otherwise
    """
    # Clean ISBN
    clean_isbn = isbn.replace("-", "").replace(" ", "")

    try:
        # Use the ISBN API endpoint
        response = await client.get(
            f"{OPENLIBRARY_API_BASE}/isbn/{clean_isbn}.json",
            follow_redirects=True,
            timeout=30.0,
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()
        data = response.json()

        return await _parse_edition(data, client)

    except httpx.HTTPError:
        return None


async def lookup_by_title_author(
    title: str,
    author: str | None,
    client: httpx.AsyncClient,
) -> OpenLibraryResult | None:
    """
    Search for a book by title and author.

    Args:
        title: Book title
        author: Author name (optional)
        client: httpx AsyncClient

    Returns:
        OpenLibraryResult if found, None otherwise
    """
    results = await search_by_title_author(title, author, client, max_results=1)
    return results[0] if results else None


async def search_by_title_author(
    title: str,
    author: str | None,
    client: httpx.AsyncClient,
    max_results: int = 5,
) -> list[OpenLibraryResult]:
    """
    Search for books by title and author, returning multiple results.

    Args:
        title: Book title
        author: Author name (optional)
        client: httpx AsyncClient
        max_results: Maximum number of results to return (default 5)

    Returns:
        List of OpenLibraryResult, may be empty
    """
    try:
        params: dict[str, str] = {"title": title}
        if author:
            params["author"] = author
        params["limit"] = str(max_results)

        response = await client.get(
            f"{OPENLIBRARY_API_BASE}/search.json",
            params=params,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("docs"):
            return []

        results = []
        for doc in data["docs"]:
            result = OpenLibraryResult(
                title=doc.get("title"),
                authors=doc.get("author_name", []),
                publishers=doc.get("publisher", [])[:3] if doc.get("publisher") else [],
                publish_date=str(doc.get("first_publish_year")) if doc.get("first_publish_year") else None,
                subjects=doc.get("subject", [])[:10] if doc.get("subject") else [],
                isbn_10=doc.get("isbn", [])[:3] if doc.get("isbn") else [],
                ddc=doc.get("ddc", []) if doc.get("ddc") else [],
                lcc=doc.get("lcc", []) if doc.get("lcc") else [],
                openlibrary_key=doc.get("key"),
                raw=doc,
            )

            # Get cover URL if available
            if doc.get("cover_i"):
                result.cover_url = f"{OPENLIBRARY_COVERS_BASE}/b/id/{doc['cover_i']}-L.jpg"

            results.append(result)

        return results

    except httpx.HTTPError:
        return []


async def _parse_edition(data: dict[str, Any], client: httpx.AsyncClient) -> OpenLibraryResult:
    """Parse an edition response into OpenLibraryResult."""
    result = OpenLibraryResult(
        title=data.get("title"),
        publishers=data.get("publishers", []),
        publish_date=data.get("publish_date"),
        isbn_10=data.get("isbn_10", []),
        isbn_13=data.get("isbn_13", []),
        openlibrary_key=data.get("key"),
        raw=data,
    )

    # Get description
    desc = data.get("description")
    if isinstance(desc, dict):
        result.description = desc.get("value")
    elif isinstance(desc, str):
        result.description = desc

    # Get cover
    covers = data.get("covers", [])
    if covers:
        result.cover_url = f"{OPENLIBRARY_COVERS_BASE}/b/id/{covers[0]}-L.jpg"

    # Fetch work data for authors, subjects, and classification
    works = data.get("works", [])
    if works:
        work_key = works[0].get("key")
        if work_key:
            try:
                work_response = await client.get(
                    f"{OPENLIBRARY_API_BASE}{work_key}.json",
                    timeout=30.0,
                )
                if work_response.status_code == 200:
                    work_data = work_response.json()

                    # Get subjects
                    result.subjects = work_data.get("subjects", [])[:10]

                    # Get DDC and LCC from work
                    result.ddc = work_data.get("dewey_number", [])
                    result.lcc = work_data.get("lc_classifications", [])

                    # Get authors
                    author_keys = [a.get("author", {}).get("key") for a in work_data.get("authors", [])]
                    for author_key in author_keys[:3]:  # Limit to 3 authors
                        if author_key:
                            author_response = await client.get(
                                f"{OPENLIBRARY_API_BASE}{author_key}.json",
                                timeout=30.0,
                            )
                            if author_response.status_code == 200:
                                author_data = author_response.json()
                                if author_data.get("name"):
                                    result.authors.append(author_data["name"])

            except httpx.HTTPError:
                pass

    return result
