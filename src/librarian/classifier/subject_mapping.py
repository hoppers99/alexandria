"""Subject to DDC mapping for fallback classification."""

# Mapping of common subjects/categories to DDC numbers
# This is used when API lookups don't return a DDC classification

SUBJECT_TO_DDC: dict[str, str] = {
    # 000 - Computer Science, Information & General Works
    "computer science": "004",
    "computers": "004",
    "computing": "004",
    "programming": "005",
    "computer programming": "005",
    "software": "005",
    "software development": "005",
    "software engineering": "005",
    "web development": "006",
    "artificial intelligence": "006",
    "machine learning": "006",
    "data science": "006",
    "databases": "005",
    "networking": "004",
    "cybersecurity": "005",
    "security": "005",
    "python": "005",
    "javascript": "005",
    "java": "005",
    "c++": "005",
    "ruby": "005",
    "golang": "005",
    "rust": "005",
    # 100 - Philosophy & Psychology
    "philosophy": "100",
    "ethics": "170",
    "logic": "160",
    "psychology": "150",
    "self-help": "158",
    "personal development": "158",
    "motivation": "158",
    "mindfulness": "158",
    "meditation": "158",
    # 200 - Religion
    "religion": "200",
    "christianity": "230",
    "bible": "220",
    "islam": "297",
    "buddhism": "294",
    "hinduism": "294",
    "judaism": "296",
    "spirituality": "204",
    "mythology": "201",
    # 300 - Social Sciences
    "sociology": "301",
    "social science": "300",
    "politics": "320",
    "political science": "320",
    "government": "320",
    "economics": "330",
    "business": "650",
    "finance": "332",
    "investing": "332",
    "law": "340",
    "legal": "340",
    "education": "370",
    "teaching": "371",
    "anthropology": "301",
    "archaeology": "930",
    "gender studies": "305",
    "feminism": "305",
    # 400 - Language
    "language": "400",
    "linguistics": "410",
    "grammar": "415",
    "english language": "420",
    "french language": "440",
    "german language": "430",
    "spanish language": "460",
    "translation": "418",
    # 500 - Science
    "science": "500",
    "mathematics": "510",
    "math": "510",
    "algebra": "512",
    "geometry": "516",
    "calculus": "515",
    "statistics": "519",
    "physics": "530",
    "chemistry": "540",
    "biology": "570",
    "evolution": "576",
    "genetics": "576",
    "ecology": "577",
    "astronomy": "520",
    "cosmology": "523",
    "geology": "551",
    "earth science": "550",
    "meteorology": "551",
    "climate": "551",
    "botany": "580",
    "zoology": "590",
    # 600 - Technology
    "technology": "600",
    "engineering": "620",
    "medicine": "610",
    "health": "613",
    "nutrition": "613",
    "cooking": "641",
    "cookbooks": "641",
    "recipes": "641",
    "food": "641",
    "agriculture": "630",
    "gardening": "635",
    "pets": "636",
    "manufacturing": "670",
    "building": "690",
    "construction": "690",
    "automotive": "629",
    "aviation": "629",
    "electronics": "621",
    # 700 - Arts & Recreation
    "art": "700",
    "arts": "700",
    "fine arts": "700",
    "drawing": "741",
    "painting": "750",
    "sculpture": "730",
    "photography": "770",
    "music": "780",
    "film": "791",
    "movies": "791",
    "cinema": "791",
    "television": "791",
    "theater": "792",
    "theatre": "792",
    "drama": "792",
    "dance": "793",
    "games": "794",
    "sports": "796",
    "recreation": "790",
    "crafts": "745",
    "architecture": "720",
    # 800 - Literature
    "literature": "800",
    "poetry": "808",
    "essays": "808",
    "literary criticism": "801",
    "literary collections": "808",
    # Fiction by language/origin
    "fiction": "823",  # Default to English fiction
    "english fiction": "823",
    "british fiction": "823",
    "american fiction": "813",
    "french fiction": "843",
    "german fiction": "833",
    "spanish fiction": "863",
    "russian fiction": "891",
    "japanese fiction": "895",
    "chinese fiction": "895",
    # Fiction genres (all map to 823 English fiction by default)
    "science fiction": "823",
    "fantasy": "823",
    "mystery": "823",
    "thriller": "823",
    "romance": "823",
    "horror": "823",
    "historical fiction": "823",
    "literary fiction": "823",
    "young adult": "823",
    "ya": "823",
    "children's fiction": "823",
    "adventure": "823",
    "dystopian": "823",
    "crime": "823",
    "detective": "823",
    "suspense": "823",
    "action": "823",
    "urban fantasy": "823",
    "epic fantasy": "823",
    "space opera": "823",
    "cyberpunk": "823",
    "steampunk": "823",
    # 900 - History & Geography
    "history": "900",
    "world history": "909",
    "european history": "940",
    "british history": "941",
    "american history": "973",
    "asian history": "950",
    "african history": "960",
    "ancient history": "930",
    "medieval history": "940",
    "modern history": "909",
    "geography": "910",
    "travel": "910",
    "biography": "920",
    "autobiography": "920",
    "memoir": "920",
    "memoirs": "920",
}


def classify_from_subjects(subjects: list[str]) -> str | None:
    """
    Attempt to determine DDC from a list of subjects.

    Args:
        subjects: List of subject strings from metadata

    Returns:
        DDC code if a match is found, None otherwise
    """
    if not subjects:
        return None

    # Try each subject
    for subject in subjects:
        # Normalise: lowercase, strip whitespace
        normalised = subject.lower().strip()

        # Direct match
        if normalised in SUBJECT_TO_DDC:
            return SUBJECT_TO_DDC[normalised]

        # Try matching parts of the subject
        for key, ddc in SUBJECT_TO_DDC.items():
            if key in normalised:
                return ddc

    return None


def classify_from_categories(categories: list[str]) -> str | None:
    """
    Attempt to determine DDC from Google Books categories.

    Google Books categories are often hierarchical like "Fiction / Science Fiction"
    """
    if not categories:
        return None

    for category in categories:
        # Split on common separators
        parts = category.replace("/", "|").replace(">", "|").split("|")

        for part in parts:
            normalised = part.lower().strip()
            if normalised in SUBJECT_TO_DDC:
                return SUBJECT_TO_DDC[normalised]

    return None
