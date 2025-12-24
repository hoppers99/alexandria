"""Seed the database with initial classification data."""

from sqlalchemy.orm import Session

from librarian.db.models import Classification

# Top-level DDC classes and their subdivisions
DDC_DATA = [
    # 000 - Computer Science, Information & General Works
    ("000", "Computer Science, Information & General Works", None),
    ("001", "Knowledge", "000"),
    ("002", "The Book", "000"),
    ("003", "Systems", "000"),
    ("004", "Data Processing & Computer Science", "000"),
    ("005", "Computer Programming", "000"),
    ("006", "Special Computer Methods", "000"),
    ("010", "Bibliographies", "000"),
    ("020", "Library & Information Science", "000"),
    ("030", "Encyclopaedias & Books of Facts", "000"),
    ("040", "Unassigned", "000"),
    ("050", "Magazines, Journals & Serials", "000"),
    ("060", "Associations, Organisations & Museums", "000"),
    ("070", "News Media, Journalism & Publishing", "000"),
    ("080", "Quotations", "000"),
    ("090", "Manuscripts & Rare Books", "000"),
    # 100 - Philosophy & Psychology
    ("100", "Philosophy & Psychology", None),
    ("110", "Metaphysics", "100"),
    ("120", "Epistemology", "100"),
    ("130", "Parapsychology & Occultism", "100"),
    ("140", "Philosophical Schools of Thought", "100"),
    ("150", "Psychology", "100"),
    ("160", "Logic", "100"),
    ("170", "Ethics", "100"),
    ("180", "Ancient & Medieval Philosophy", "100"),
    ("190", "Modern Western Philosophy", "100"),
    # 200 - Religion
    ("200", "Religion", None),
    ("210", "Philosophy & Theory of Religion", "200"),
    ("220", "The Bible", "200"),
    ("230", "Christianity & Christian Theology", "200"),
    ("240", "Christian Moral & Devotional Theology", "200"),
    ("250", "Christian Pastoral Practice", "200"),
    ("260", "Christian Organisation, Work & Worship", "200"),
    ("270", "History of Christianity", "200"),
    ("280", "Christian Denominations", "200"),
    ("290", "Other Religions", "200"),
    # 300 - Social Sciences
    ("300", "Social Sciences", None),
    ("310", "Statistics", "300"),
    ("320", "Political Science", "300"),
    ("330", "Economics", "300"),
    ("340", "Law", "300"),
    ("350", "Public Administration & Military Science", "300"),
    ("360", "Social Problems & Social Services", "300"),
    ("370", "Education", "300"),
    ("380", "Commerce, Communications & Transportation", "300"),
    ("390", "Customs, Etiquette & Folklore", "300"),
    # 400 - Language
    ("400", "Language", None),
    ("410", "Linguistics", "400"),
    ("420", "English & Old English Languages", "400"),
    ("430", "German & Related Languages", "400"),
    ("440", "French & Related Languages", "400"),
    ("450", "Italian, Romanian & Related Languages", "400"),
    ("460", "Spanish, Portuguese & Galician", "400"),
    ("470", "Latin & Italic Languages", "400"),
    ("480", "Classical & Modern Greek Languages", "400"),
    ("490", "Other Languages", "400"),
    # 500 - Science
    ("500", "Science", None),
    ("510", "Mathematics", "500"),
    ("520", "Astronomy", "500"),
    ("530", "Physics", "500"),
    ("540", "Chemistry", "500"),
    ("550", "Earth Sciences & Geology", "500"),
    ("560", "Fossils & Prehistoric Life", "500"),
    ("570", "Biology & Life Sciences", "500"),
    ("580", "Plants (Botany)", "500"),
    ("590", "Animals (Zoology)", "500"),
    # 600 - Technology
    ("600", "Technology", None),
    ("610", "Medicine & Health", "600"),
    ("620", "Engineering", "600"),
    ("630", "Agriculture", "600"),
    ("640", "Home & Family Management", "600"),
    ("641", "Food & Drink", "640"),
    ("650", "Management & Public Relations", "600"),
    ("660", "Chemical Engineering", "600"),
    ("670", "Manufacturing", "600"),
    ("680", "Manufacture for Specific Uses", "600"),
    ("690", "Building & Construction", "600"),
    # 700 - Arts & Recreation
    ("700", "Arts", None),
    ("710", "Landscaping & Area Planning", "700"),
    ("720", "Architecture", "700"),
    ("730", "Sculpture, Ceramics & Metalwork", "700"),
    ("740", "Drawing & Decorative Arts", "700"),
    ("750", "Painting", "700"),
    ("760", "Graphic Arts", "700"),
    ("770", "Photography & Computer Art", "700"),
    ("780", "Music", "700"),
    ("790", "Sports, Games & Entertainment", "700"),
    # 800 - Literature
    ("800", "Literature, Rhetoric & Criticism", None),
    ("810", "American Literature in English", "800"),
    ("811", "American Poetry", "810"),
    ("812", "American Drama", "810"),
    ("813", "American Fiction", "810"),
    ("820", "English & Old English Literatures", "800"),
    ("821", "English Poetry", "820"),
    ("822", "English Drama", "820"),
    ("823", "English Fiction", "820"),
    ("830", "German & Related Literatures", "800"),
    ("840", "French & Related Literatures", "800"),
    ("850", "Italian, Romanian & Related Literatures", "800"),
    ("860", "Spanish, Portuguese & Galician Literatures", "800"),
    ("870", "Latin & Italic Literatures", "800"),
    ("880", "Classical & Modern Greek Literatures", "800"),
    ("890", "Other Literatures", "800"),
    # 900 - History & Geography
    ("900", "History", None),
    ("910", "Geography & Travel", "900"),
    ("920", "Biography & Genealogy", "900"),
    ("930", "History of the Ancient World", "900"),
    ("940", "History of Europe", "900"),
    ("950", "History of Asia", "900"),
    ("960", "History of Africa", "900"),
    ("970", "History of North America", "900"),
    ("980", "History of South America", "900"),
    ("990", "History of Other Areas", "900"),
]


def seed_classifications(session: Session) -> int:
    """
    Seed the classifications table with DDC data.

    Returns the number of classifications added.
    """
    added = 0

    for code, name, parent_code in DDC_DATA:
        # Check if already exists
        existing = session.query(Classification).filter(Classification.code == code).first()
        if existing:
            continue

        classification = Classification(
            code=code,
            name=name,
            parent_code=parent_code,
            system="ddc",
        )
        session.add(classification)
        added += 1

    session.commit()
    return added
