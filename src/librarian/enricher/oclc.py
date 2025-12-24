"""OCLC Classify API client for DDC classification."""

import re
from dataclasses import dataclass, field
from xml.etree import ElementTree

import httpx

OCLC_CLASSIFY_BASE = "https://classify.oclc.org/classify2/Classify"

# XML namespaces used by OCLC
NAMESPACES = {
    "classify": "http://classify.oclc.org",
}


@dataclass
class OCLCResult:
    """Result from OCLC Classify API lookup."""

    title: str | None = None
    authors: list[str] = field(default_factory=list)
    ddc: str | None = None
    ddc_editions: list[str] = field(default_factory=list)
    lcc: str | None = None
    owi: str | None = None  # OCLC Work Identifier
    holdings: int | None = None  # Number of library holdings
    raw_xml: str | None = None


async def lookup_by_isbn(isbn: str, client: httpx.AsyncClient) -> OCLCResult | None:
    """
    Look up classification by ISBN using OCLC Classify API.

    Args:
        isbn: ISBN-10 or ISBN-13
        client: httpx AsyncClient

    Returns:
        OCLCResult if found, None otherwise
    """
    clean_isbn = isbn.replace("-", "").replace(" ", "")

    try:
        response = await client.get(
            OCLC_CLASSIFY_BASE,
            params={
                "isbn": clean_isbn,
                "summary": "true",
            },
            timeout=30.0,
        )
        response.raise_for_status()

        return _parse_response(response.text)

    except httpx.HTTPError:
        return None


async def lookup_by_title_author(
    title: str,
    author: str | None,
    client: httpx.AsyncClient,
) -> OCLCResult | None:
    """
    Look up classification by title and author using OCLC Classify API.

    Args:
        title: Book title
        author: Author name (optional)
        client: httpx AsyncClient

    Returns:
        OCLCResult if found, None otherwise
    """
    try:
        params: dict[str, str] = {
            "title": title,
            "summary": "true",
        }
        if author:
            params["author"] = author

        response = await client.get(
            OCLC_CLASSIFY_BASE,
            params=params,
            timeout=30.0,
        )
        response.raise_for_status()

        return _parse_response(response.text)

    except httpx.HTTPError:
        return None


def _parse_response(xml_text: str) -> OCLCResult | None:
    """Parse OCLC Classify XML response."""
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return None

    result = OCLCResult(raw_xml=xml_text)

    # Check response code
    response_elem = root.find("classify:response", NAMESPACES)
    if response_elem is None:
        return None

    code = response_elem.get("code")

    # Code 0 = single work found
    # Code 2 = single work found (alternative)
    # Code 4 = multiple works found (we'll take the first)
    if code not in ("0", "2", "4"):
        return None

    # Get work info
    work_elem = root.find(".//classify:work", NAMESPACES)
    if work_elem is not None:
        result.title = work_elem.get("title")
        result.owi = work_elem.get("owi")

        # Parse authors from the work element
        authors_text = work_elem.get("author")
        if authors_text:
            # Authors are often pipe-separated
            result.authors = [a.strip() for a in authors_text.split("|") if a.strip()]

    # Get DDC (most popular classification)
    ddc_elem = root.find(".//classify:ddc/classify:mostPopular", NAMESPACES)
    if ddc_elem is not None:
        result.ddc = ddc_elem.get("sfa")  # Standard format (abbreviated)
        if not result.ddc:
            result.ddc = ddc_elem.get("nsfa")  # Non-standard format
        result.holdings = int(ddc_elem.get("holdings", 0))

    # Get all DDC editions
    for ddc_elem in root.findall(".//classify:ddc/classify:edition", NAMESPACES):
        edition = ddc_elem.get("sfa") or ddc_elem.get("nsfa")
        if edition and edition not in result.ddc_editions:
            result.ddc_editions.append(edition)

    # Get LCC
    lcc_elem = root.find(".//classify:lcc/classify:mostPopular", NAMESPACES)
    if lcc_elem is not None:
        result.lcc = lcc_elem.get("sfa")
        if not result.lcc:
            result.lcc = lcc_elem.get("nsfa")

    # Only return if we got some useful data
    if result.ddc or result.lcc or result.title:
        return result

    return None


def normalise_ddc(ddc: str) -> str:
    """
    Normalise a DDC number to a standard format.

    Examples:
        "823.914" -> "823"
        "005.133" -> "005"
        "823" -> "823"
        "FIC" -> "823"  # Fiction maps to English fiction
    """
    if not ddc:
        return ""

    # Handle "FIC" for fiction
    if ddc.upper() == "FIC":
        return "823"

    # Extract just the main class (first 3 digits)
    match = re.match(r"(\d{1,3})", ddc)
    if match:
        num = match.group(1)
        # Pad to 3 digits
        return num.zfill(3)

    return ""
