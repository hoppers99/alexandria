"""Main classifier module for determining DDC classification."""

from dataclasses import dataclass

from librarian.classifier.subject_mapping import (
    classify_from_categories,
    classify_from_subjects,
)
from librarian.enricher import EnrichedMetadata


@dataclass
class ClassificationResult:
    """Result of classification attempt."""

    ddc: str | None = None
    ddc_name: str | None = None
    source: str | None = None  # "oclc", "openlibrary", "subject_mapping", "filename"
    confidence: float = 0.0
    needs_review: bool = False
    is_fiction: bool = False
    genres: list[str] | None = None  # For fiction - extracted genre tags


# Top-level DDC names for display
DDC_NAMES: dict[str, str] = {
    "000": "Computer Science & Information",
    "001": "Knowledge",
    "002": "The Book",
    "003": "Systems",
    "004": "Data Processing & Computer Science",
    "005": "Computer Programming",
    "006": "Special Computer Methods",
    "010": "Bibliographies",
    "020": "Library & Information Science",
    "030": "Encyclopaedias",
    "100": "Philosophy",
    "110": "Metaphysics",
    "120": "Epistemology",
    "130": "Parapsychology & Occultism",
    "140": "Philosophical Schools",
    "150": "Psychology",
    "160": "Logic",
    "170": "Ethics",
    "180": "Ancient & Medieval Philosophy",
    "190": "Modern Philosophy",
    "200": "Religion",
    "210": "Philosophy of Religion",
    "220": "The Bible",
    "230": "Christianity",
    "240": "Christian Practice",
    "250": "Christian Ministry",
    "260": "Christian Organisation",
    "270": "Church History",
    "280": "Christian Denominations",
    "290": "Other Religions",
    "300": "Social Sciences",
    "310": "Statistics",
    "320": "Political Science",
    "330": "Economics",
    "340": "Law",
    "350": "Public Administration",
    "360": "Social Services",
    "370": "Education",
    "380": "Commerce",
    "390": "Customs & Folklore",
    "400": "Language",
    "410": "Linguistics",
    "420": "English Language",
    "430": "German Language",
    "440": "French Language",
    "450": "Italian Language",
    "460": "Spanish Language",
    "470": "Latin",
    "480": "Greek",
    "490": "Other Languages",
    "500": "Science",
    "510": "Mathematics",
    "520": "Astronomy",
    "530": "Physics",
    "540": "Chemistry",
    "550": "Earth Sciences",
    "560": "Palaeontology",
    "570": "Biology",
    "580": "Botany",
    "590": "Zoology",
    "600": "Technology",
    "610": "Medicine",
    "620": "Engineering",
    "630": "Agriculture",
    "640": "Home Economics",
    "641": "Food & Drink",
    "650": "Business",
    "660": "Chemical Engineering",
    "670": "Manufacturing",
    "680": "Specific Manufacturing",
    "690": "Building",
    "700": "Arts",
    "710": "Landscape & Area Planning",
    "720": "Architecture",
    "730": "Sculpture",
    "740": "Drawing & Decorative Arts",
    "750": "Painting",
    "760": "Graphic Arts",
    "770": "Photography",
    "780": "Music",
    "790": "Recreation",
    "800": "Literature",
    "810": "American Literature",
    "813": "American Fiction",
    "820": "English Literature",
    "823": "English Fiction",
    "830": "German Literature",
    "840": "French Literature",
    "850": "Italian Literature",
    "860": "Spanish Literature",
    "870": "Latin Literature",
    "880": "Greek Literature",
    "890": "Other Literatures",
    "900": "History & Geography",
    "910": "Geography & Travel",
    "920": "Biography",
    "930": "Ancient History",
    "940": "European History",
    "950": "Asian History",
    "960": "African History",
    "970": "North American History",
    "980": "South American History",
    "990": "Pacific & Polar History",
}

# Fiction DDC codes (800s literature classes that are fiction)
FICTION_DDC_CODES = {
    "813", "823", "833", "843", "853", "863", "873", "883", "893",  # Fiction by language
    "810", "820", "830", "840", "850", "860", "870", "880", "890",  # General literature
    "800",  # General literature
}

# Genre keywords to look for in subjects
GENRE_KEYWORDS = {
    "Fantasy": ["fantasy", "magic", "dragons", "wizards", "epic fantasy", "urban fantasy"],
    "Science Fiction": ["science fiction", "sci-fi", "scifi", "space opera", "dystopia", "cyberpunk"],
    "Mystery": ["mystery", "detective", "crime fiction", "whodunit", "cozy mystery"],
    "Thriller": ["thriller", "suspense", "psychological thriller"],
    "Romance": ["romance", "love stories", "romantic", "contemporary romance"],
    "Horror": ["horror", "supernatural", "gothic", "dark fantasy"],
    "Historical Fiction": ["historical fiction", "historical novel"],
    "Literary Fiction": ["literary fiction", "literary", "contemporary fiction"],
    "Adventure": ["adventure", "action adventure"],
    "Young Adult": ["young adult", "ya fiction", "teen fiction"],
    "Children's": ["children's fiction", "juvenile fiction", "middle grade"],
}


def _is_fiction(ddc: str | None, subjects: list[str] | None) -> bool:
    """Determine if an item is fiction based on DDC and subjects."""
    # Check DDC code
    if ddc:
        # Normalise to 3 digits for comparison
        ddc_prefix = ddc[:3] if len(ddc) >= 3 else ddc.zfill(3)
        if ddc_prefix in FICTION_DDC_CODES:
            return True

    # Check subjects for fiction indicators
    if subjects:
        subjects_lower = [s.lower() for s in subjects]
        fiction_indicators = [
            "fiction", "novel", "stories", "fantasy", "science fiction",
            "mystery", "thriller", "romance", "horror",
        ]
        for indicator in fiction_indicators:
            for subject in subjects_lower:
                if indicator in subject:
                    return True

    return False


def _extract_genres(subjects: list[str] | None) -> list[str]:
    """Extract genre tags from subject list."""
    if not subjects:
        return []

    genres = set()
    subjects_lower = [s.lower() for s in subjects]

    for genre, keywords in GENRE_KEYWORDS.items():
        for keyword in keywords:
            for subject in subjects_lower:
                if keyword in subject:
                    genres.add(genre)
                    break

    return sorted(genres)


def classify(enriched: EnrichedMetadata) -> ClassificationResult:
    """
    Determine classification from enriched metadata.

    For fiction: Sets is_fiction=True and extracts genre tags
    For non-fiction: Determines DDC classification

    Priority:
    1. DDC from OCLC (most authoritative)
    2. DDC from Open Library
    3. Subject mapping fallback
    4. Mark for review if uncertain

    Args:
        enriched: EnrichedMetadata from the enricher

    Returns:
        ClassificationResult with DDC/fiction status and confidence
    """
    result = ClassificationResult()

    # Check if we have DDC from API lookups
    if enriched.ddc_normalised:
        result.ddc = enriched.ddc_normalised
        result.source = "oclc" if "oclc" in enriched.sources else "openlibrary"
        result.confidence = 0.95 if result.source == "oclc" else 0.85
        result.ddc_name = _get_ddc_name(result.ddc)
    elif classify_from_subjects(enriched.subjects):
        # Try subject mapping
        result.ddc = classify_from_subjects(enriched.subjects)
        result.source = "subject_mapping"
        result.confidence = 0.6
        result.ddc_name = _get_ddc_name(result.ddc)
    elif classify_from_categories(enriched.subjects):
        # Try categories (Google Books)
        result.ddc = classify_from_categories(enriched.subjects)
        result.source = "subject_mapping"
        result.confidence = 0.5
        result.ddc_name = _get_ddc_name(result.ddc)
    else:
        # Unable to classify - needs review
        result.needs_review = True
        result.confidence = 0.0

    # Determine if fiction and extract genres
    result.is_fiction = _is_fiction(result.ddc, enriched.subjects)

    if result.is_fiction:
        result.genres = _extract_genres(enriched.subjects)
        # For fiction, we don't need DDC for filing (just for database record)
        # Boost confidence since fiction detection is fairly reliable
        if result.confidence < 0.5:
            result.confidence = 0.6
            result.needs_review = False

    return result


def classify_from_extracted_metadata(
    title: str | None,
    authors: list[str] | None,
    subjects: list[str] | None,
    series: str | None,
) -> ClassificationResult:
    """
    Attempt classification from extracted file metadata only.

    This is used before API enrichment as a quick check.
    """
    result = ClassificationResult()

    # Check subjects if available
    if subjects:
        ddc = classify_from_subjects(subjects)
        if ddc:
            result.ddc = ddc
            result.source = "subject_mapping"
            result.confidence = 0.4
            result.ddc_name = _get_ddc_name(ddc)
            return result

    # If we have a series name, it's likely fiction
    if series:
        result.ddc = "823"  # Default to English fiction
        result.source = "series_heuristic"
        result.confidence = 0.3
        result.ddc_name = "English Fiction"
        return result

    result.needs_review = True
    return result


def _get_ddc_name(ddc: str) -> str:
    """Get the human-readable name for a DDC code."""
    if not ddc:
        return ""

    # Try exact match first
    if ddc in DDC_NAMES:
        return DDC_NAMES[ddc]

    # Try progressively shorter prefixes
    for length in [2, 1]:
        prefix = ddc[:length] + "0" * (3 - length)
        if prefix in DDC_NAMES:
            return DDC_NAMES[prefix]

    return ""


def normalise_ddc_for_path(ddc: str) -> str:
    """
    Normalise DDC for use in filesystem paths.

    Returns the 3-digit top-level DDC class.
    """
    if not ddc:
        return "000"

    # Ensure it's zero-padded to 3 digits
    try:
        num = int(ddc[:3].replace(".", ""))
        return str(num).zfill(3)
    except ValueError:
        return "000"
