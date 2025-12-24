"""LibraryThing API integration for book metadata enrichment.

LibraryThing offers several APIs:
- ThingISBN: Free, returns all ISBNs for editions of a work
- Developer API: Requires key (free for non-commercial, 1000 req/day)

See: https://www.librarything.com/services/
"""

from dataclasses import dataclass, field

import httpx


@dataclass
class LibraryThingResult:
    """Result from LibraryThing lookup."""

    work_id: str | None = None
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    series: str | None = None
    series_number: float | None = None
    tags: list[str] = field(default_factory=list)
    related_isbns: list[str] = field(default_factory=list)


async def lookup_related_isbns(
    isbn: str,
    client: httpx.AsyncClient,
) -> list[str]:
    """
    Use ThingISBN to find all related ISBNs for a work.

    This is useful for:
    - Finding alternative editions
    - Cross-referencing when one ISBN doesn't return results

    Args:
        isbn: ISBN-10 or ISBN-13
        client: httpx AsyncClient

    Returns:
        List of related ISBNs (including the original)
    """
    clean_isbn = isbn.replace("-", "").replace(" ", "")

    try:
        # ThingISBN returns XML with all related ISBNs
        url = f"https://www.librarything.com/api/thingISBN/{clean_isbn}"
        response = await client.get(url, timeout=10.0)

        if response.status_code != 200:
            return [clean_isbn]

        # Parse simple XML response
        # Format: <idlist><isbn>...</isbn><isbn>...</isbn></idlist>
        import xml.etree.ElementTree as ET

        root = ET.fromstring(response.text)
        isbns = [elem.text for elem in root.findall(".//isbn") if elem.text]

        # Ensure original is included
        if clean_isbn not in isbns:
            isbns.insert(0, clean_isbn)

        return isbns

    except Exception:
        return [clean_isbn]


async def lookup_by_isbn(
    isbn: str,
    client: httpx.AsyncClient,
    api_key: str | None = None,
) -> LibraryThingResult | None:
    """
    Look up book metadata from LibraryThing.

    Args:
        isbn: ISBN-10 or ISBN-13
        client: httpx AsyncClient
        api_key: Optional LibraryThing developer API key

    Returns:
        LibraryThingResult if found, None otherwise
    """
    clean_isbn = isbn.replace("-", "").replace(" ", "")

    # First, get related ISBNs (free API)
    related_isbns = await lookup_related_isbns(isbn, client)

    result = LibraryThingResult(related_isbns=related_isbns)

    # If we have an API key, get more detailed metadata
    if api_key:
        try:
            # Developer API for work info
            url = "https://www.librarything.com/services/rest/1.1/"
            params = {
                "method": "librarything.ck.getwork",
                "isbn": clean_isbn,
                "apikey": api_key,
            }
            response = await client.get(url, params=params, timeout=10.0)

            if response.status_code == 200:
                import xml.etree.ElementTree as ET

                root = ET.fromstring(response.text)

                # Parse work info
                work_elem = root.find(".//item")
                if work_elem is not None:
                    result.work_id = work_elem.get("id")

                    title_elem = work_elem.find("title")
                    if title_elem is not None and title_elem.text:
                        result.title = title_elem.text

                    author_elem = work_elem.find("author")
                    if author_elem is not None and author_elem.text:
                        result.authors = [author_elem.text]

        except Exception:
            pass

    # Get tags if we have the work ID
    if result.work_id and api_key:
        try:
            url = "https://www.librarything.com/services/rest/1.1/"
            params = {
                "method": "librarything.ck.getworktags",
                "id": result.work_id,
                "apikey": api_key,
            }
            response = await client.get(url, params=params, timeout=10.0)

            if response.status_code == 200:
                import xml.etree.ElementTree as ET

                root = ET.fromstring(response.text)
                tags = []
                for tag_elem in root.findall(".//tag"):
                    tag_name = tag_elem.get("name")
                    if tag_name:
                        tags.append(tag_name)
                result.tags = tags[:20]  # Limit to top 20 tags

        except Exception:
            pass

    return result if result.related_isbns or result.title else None


async def get_series_info(
    isbn: str,
    client: httpx.AsyncClient,
    api_key: str,
) -> tuple[str | None, float | None]:
    """
    Get series information for a book from LibraryThing.

    LibraryThing is particularly good at tracking series.

    Args:
        isbn: ISBN-10 or ISBN-13
        client: httpx AsyncClient
        api_key: LibraryThing developer API key

    Returns:
        Tuple of (series_name, series_number) or (None, None)
    """
    clean_isbn = isbn.replace("-", "").replace(" ", "")

    try:
        url = "https://www.librarything.com/services/rest/1.1/"
        params = {
            "method": "librarything.ck.getwork",
            "isbn": clean_isbn,
            "apikey": api_key,
        }
        response = await client.get(url, params=params, timeout=10.0)

        if response.status_code != 200:
            return None, None

        import xml.etree.ElementTree as ET

        root = ET.fromstring(response.text)
        work_elem = root.find(".//item")

        if work_elem is not None:
            series_elem = work_elem.find("series")
            if series_elem is not None and series_elem.text:
                series_name = series_elem.text
                # Try to extract series number from the series string
                # Format often like "Series Name, #5" or "Series Name (5)"
                import re

                number_match = re.search(r"[#,]\s*(\d+(?:\.\d+)?)", series_name)
                if number_match:
                    series_number = float(number_match.group(1))
                    # Clean series name
                    series_name = re.sub(r"\s*[#,]\s*\d+(?:\.\d+)?", "", series_name).strip()
                    return series_name, series_number
                return series_name, None

    except Exception:
        pass

    return None, None
