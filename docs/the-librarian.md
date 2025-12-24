# The Librarian

The Librarian is the backend cataloguing engine for Bibliotheca Alexandria. It handles all the behind-the-scenes work of processing, classifying, and filing items in the library.

## Concept

Think of The Librarian as an actual librarian would work:
- Receives new acquisitions (the "Returns" pile)
- Inspects each item to identify it
- Looks up catalogue information from reference sources
- Determines the correct classification
- Files the item in its proper location
- Updates the catalogue (database)
- Maintains order and handles problems

The Librarian is **systematic rather than smart** - it follows established procedures and consults authoritative sources rather than guessing.

## Components

### CLI Tool

```bash
# Process all items in the Returns folder
librarian process

# Add a specific file
librarian add /path/to/book.epub

# Add with hints (speeds up identification)
librarian add /path/to/book.pdf --isbn 9780134685991
librarian add /path/to/book.epub --title "Clean Code" --author "Robert Martin"

# Identify a file without filing it
librarian identify /path/to/unknown.epub

# Search for metadata manually
librarian lookup --isbn 9780134685991
librarian lookup --title "Dune" --author "Herbert"

# Library maintenance
librarian check          # Verify integrity (missing files, orphan records)
librarian duplicates     # Find and report duplicates
librarian refresh <id>   # Re-fetch metadata for an item

```

### Triggering Processing

Processing can be triggered by:
- **CLI**: `librarian process` (manual or via cron)
- **Web UI**: "Process Returns" button in admin interface
- **API**: `POST /api/librarian/process` endpoint

No daemon required - just run when needed.

## Processing Pipeline

When The Librarian processes a file, it follows this procedure:

### Stage 1: Inspect

```
1. Calculate file checksum (MD5 + SHA-256)
2. Check for duplicates in existing library
3. Identify file format (EPUB, PDF, MOBI, etc.)
4. Extract embedded metadata:
   - For EPUB: OPF metadata (title, author, ISBN, description, etc.)
   - For PDF: XMP/document properties
   - For MOBI: MOBI headers
   - For audio: ID3 tags / MP4 atoms
```

### Stage 2: Identify

Goal: Confirm what this item actually is and find its ISBN or other identifier.

```
1. Check extracted metadata for ISBN
2. If no ISBN, scan content for ISBN:
   - EPUB: Check copyright page, first few chapters
   - PDF: OCR first few pages if needed
3. If ISBN found, validate format (ISBN-10 or ISBN-13)
4. If no ISBN, prepare for title/author search
```

### Stage 3: Enrich

Goal: Gather complete metadata from authoritative sources.

```
1. Query OCLC Classify (by ISBN if available)
   → Returns: DDC number, author, title, subjects

2. Query Open Library (by ISBN or title/author)
   → Returns: Full metadata, cover images, DDC

3. Query Google Books (fallback)
   → Returns: Metadata, descriptions, covers

4. Merge results, preferring:
   - OCLC for classification
   - Open Library for metadata completeness
   - Google Books for descriptions and covers
```

### Stage 4: Classify

Goal: Determine the DDC classification for filing.

```
1. Use DDC from OCLC Classify if available (most authoritative)
2. Else use DDC from Open Library record
3. Else map from subject headings:
   - Maintain a subject → DDC mapping table
   - "Computer programming" → 005.1
   - "Python (Programming language)" → 005.133
   - "English fiction" → 823
   - "Science fiction" → 823 (filed under language of text)
4. If classification cannot be determined:
   - Queue for user review
   - Prompt in interactive mode
```

### Stage 5: File

Goal: Move the file to its correct location and update the database.

```
1. Generate canonical filename:
   - Non-series: "Author - Title.ext"
   - Series: "Author - Series NN - Title.ext"
   - Examples:
     - "Frank Herbert - Dune 01 - Dune.epub"
     - "Robert C. Martin - Clean Code.pdf"
     - "Douglas Adams - Hitchhiker's Guide 01 - The Hitchhiker's Guide to the Galaxy.epub"

2. Determine target path:
   - /library/DDC/filename
   - Example: /library/823/Frank Herbert - Dune 01 - Dune.epub

3. Move file to target location

4. Create/update database records:
   - items table (metadata)
   - files table (path, checksum)
   - item_creators table (author relationship)
   - Download/extract cover image
```

### Stage 6: Report

```
1. Log action taken
2. Update processing statistics
3. If issues encountered:
   - Add to review queue
   - Log warning/error
```

## Filename Convention

### Standard Format

```
Author - Title.ext
```

### Series Format

```
Author - Series NN - Title.ext
```

Where:
- **Author**: Primary author's name as "First Last" or "Last, First" (configurable)
- **Series**: Series name
- **NN**: Zero-padded series number (01, 02, etc.)
- **Title**: Book title (subtitle omitted or abbreviated)
- **ext**: Original file extension

### Examples

| Type | Filename |
|------|----------|
| Single work | `George Orwell - 1984.epub` |
| Series | `Frank Herbert - Dune 01 - Dune.epub` |
| Series | `Frank Herbert - Dune 02 - Dune Messiah.epub` |
| Multi-author | `Larry Niven & Jerry Pournelle - The Mote in God's Eye.epub` |
| Non-fiction | `Robert C. Martin - Clean Code.pdf` |

### Character Handling

- Replace filesystem-unsafe characters: `: / \ * ? " < > |`
- Normalise whitespace
- Preserve Unicode characters where filesystem supports them

## Classification Strategy

### Authoritative Sources (in order of preference)

1. **OCLC Classify** (http://classify.oclc.org/classify2/)
   - Most authoritative source
   - Returns DDC based on actual library cataloguing
   - Free API access

2. **Open Library** (https://openlibrary.org/)
   - Good coverage, includes DDC in many records
   - CC0 data licence
   - Free API

3. **Library of Congress**
   - Primarily uses LCC, but sometimes includes DDC
   - Very authoritative for works they hold

### Subject Mapping Fallback

When no DDC is found in reference sources, map from subject headings:

```
# Top-level mapping (simplified)
Computer Science, Programming      → 005
Philosophy                         → 100
Psychology                         → 150
Religion                           → 200
Politics, Government               → 320
Economics                          → 330
Law                                → 340
Science (general)                  → 500
Mathematics                        → 510
Physics                            → 530
Chemistry                          → 540
Biology                            → 570
Medicine, Health                   → 610
Engineering                        → 620
Cooking                            → 641
Business, Management               → 650
Art                                → 700
Music                              → 780
Fiction (English language)         → 823
Fiction (American)                 → 813
History (general)                  → 900
Biography                          → 920
```

A more detailed mapping table will be maintained in the codebase.

### User Review Queue

Items that cannot be classified automatically are added to a review queue:
- Visible in web UI for admin users
- Can also be processed via CLI: `librarian review`
- Shows extracted metadata and suggested classifications
- User confirms or corrects, then item is filed

## Configuration

```yaml
# librarian.yaml

library:
  root: /library                    # Root of DDC folder structure
  returns: /library/Returns         # Incoming items folder

naming:
  format: "{author} - {title}"      # Standard format
  series_format: "{author} - {series} {number:02d} - {title}"
  author_format: "first_last"       # or "last_first"

classification:
  auto_file: true                   # File automatically when confident
  confidence_threshold: 0.8         # Require 80% confidence for auto-file
  default_ddc: "000"                # Fallback if all else fails

apis:
  oclc_classify: true
  open_library: true
  google_books: true

processing:
  batch_size: 10                    # Items to process per batch
```

## Future Enhancements

These are not in initial scope but could be added later:

- **AI-assisted classification**: Use Claude API for uncertain items
- **Cover generation**: Generate covers for items without them
- **OCR pipeline**: Extract text from scanned PDFs
- **Learning from corrections**: Improve subject mapping based on user edits
- **Bulk import tools**: Special handling for large collections
- **Format conversion**: Convert to preferred formats during import
