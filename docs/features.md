# Feature Roadmap

## Project Focus

Bibliotheca Alexandria has two main components:

1. **The Librarian** - Backend cataloguing engine (CLI + daemon)
2. **Web UI** - Patron-facing browse/search/download interface

## Status Key

- **MVP** - Minimum viable product, required for first usable release
- **v1.0** - First stable release features
- **Stretch** - Nice to have, lower priority
- **Future** - Planned but not yet scheduled

---

## The Librarian (Cataloguing Engine)

### File Processing

| Feature | Status | Description |
|---------|--------|-------------|
| Process Returns folder | MVP | Scan and process all files in Returns |
| Add single file | MVP | `librarian add /path/to/file` |
| Format detection | MVP | Identify EPUB, PDF, MOBI, etc. |
| Checksum calculation | MVP | MD5 + SHA-256 for duplicate detection |
| Duplicate detection | MVP | Prevent adding duplicate files |

### Metadata Extraction

| Feature | Status | Description |
|---------|--------|-------------|
| EPUB metadata | MVP | Extract from OPF |
| PDF metadata | MVP | Extract from XMP/properties |
| MOBI metadata | v1.0 | Extract from MOBI headers |
| ISBN extraction | MVP | Find ISBN in metadata |
| ISBN from content | v1.0 | Scan first pages for ISBN |
| Audio metadata | v1.0 | Extract from ID3/MP4 tags |
| Video metadata | v1.0 | Extract from container metadata |

### Metadata Enrichment

| Feature | Status | Description |
|---------|--------|-------------|
| OCLC Classify lookup | MVP | Authoritative DDC classification |
| Open Library lookup | MVP | Metadata and covers |
| Google Books lookup | MVP | Fallback metadata source |
| Cover extraction | MVP | Extract embedded covers |
| Cover download | MVP | Fetch covers from APIs |
| Subject mapping | MVP | Map subjects to DDC when lookup fails |

### Filing & Organisation

| Feature | Status | Description |
|---------|--------|-------------|
| DDC folder filing | MVP | Move files to correct DDC location |
| Canonical naming | MVP | `Author - Title.ext` format |
| Series naming | MVP | `Author - Series NN - Title.ext` |
| Database record creation | MVP | Add to PostgreSQL catalogue |
| User review queue | MVP | Queue uncertain items for review |

### Maintenance

| Feature | Status | Description |
|---------|--------|-------------|
| Library integrity check | v1.0 | Verify files match database |
| Duplicate report | v1.0 | Find and list duplicates |
| Orphan cleanup | v1.0 | Handle missing files |
| Metadata refresh | v1.0 | Re-fetch metadata for items |

### Operation Modes

| Feature | Status | Description |
|---------|--------|-------------|
| CLI tool | MVP | Command-line interface |
| Web UI trigger | MVP | "Process Returns" button in admin |
| API trigger | MVP | `POST /api/librarian/process` |
| Cron-friendly | MVP | Exit codes suitable for scheduled runs |
| Docker container | MVP | Containerised deployment |

---

## Web UI (Patron Interface)

### Browsing

| Feature | Status | Description |
|---------|--------|-------------|
| Author listing | MVP | Browse by author |
| Genre/tag browsing | MVP | Browse by genre or tags |
| Series grouping | MVP | View series together |
| Recently added | MVP | View newest items |
| Cover grid view | MVP | Visual browsing with covers |
| List view | MVP | Compact sortable listing |
| DDC tree view | Stretch | Browse by classification hierarchy |

### Search

| Feature | Status | Description |
|---------|--------|-------------|
| Full-text search | MVP | Search titles, authors, descriptions |
| Filter by format | MVP | EPUB, PDF, audio, video, etc. |
| Filter by media type | MVP | Books, audiobooks, video |
| Sort options | MVP | Title, author, date added, etc. |
| Advanced search | v1.0 | Field-specific queries |

### Item Details

| Feature | Status | Description |
|---------|--------|-------------|
| Metadata display | MVP | Title, author, description, cover |
| Available formats | MVP | List all formats for item |
| Series navigation | v1.0 | Next/previous in series |
| Related items | Future | Suggestions based on classification |

### Content Access

| Feature | Status | Description |
|---------|--------|-------------|
| File download | MVP | Download original files |
| Format selection | MVP | Choose from available formats |
| EPUB reader | Stretch | In-browser reading via epub.js |
| PDF viewer | Stretch | In-browser viewing via PDF.js |
| Audio streaming | Stretch | Stream audiobooks |
| Video streaming | Stretch | Stream video content |
| Reading progress | Stretch | Track position in books |

### User Features

| Feature | Status | Description |
|---------|--------|-------------|
| User accounts | MVP | Login/logout |
| Reading history | v1.0 | Track what you've accessed |
| Personal collections | v1.0 | Create shelves/lists |
| Continue reading | Stretch | Resume where you left off |

---

## Administration

### Library Management

| Feature | Status | Description |
|---------|--------|-------------|
| Review queue | MVP | Process uncertain items |
| Metadata editing | v1.0 | Manually edit item details |
| Bulk operations | Future | Edit multiple items |
| Re-process items | v1.0 | Trigger re-classification |

### System

| Feature | Status | Description |
|---------|--------|-------------|
| Configuration | MVP | Library paths, API settings |
| Health checks | MVP | Docker health endpoints |
| Statistics dashboard | v1.0 | Library overview |
| Log viewer | v1.0 | View processing logs |

---

## Integration

| Feature | Status | Description |
|---------|--------|-------------|
| REST API | MVP | Programmatic access |
| OPDS feed | v1.0 | Standard catalogue for e-reader apps |
| Webhooks | Future | Notify external systems |
| reMarkable sync | Future | Direct sync to reMarkable |

---

## MVP Summary

The minimum viable product includes:

**The Librarian:**
- Process files from Returns folder
- Extract metadata from EPUB/PDF
- Look up metadata via OCLC/OpenLibrary/Google Books
- Determine DDC classification
- File with canonical naming
- Handle covers
- Queue uncertain items for review

**Web UI:**
- Browse by author, genre, series
- Search library
- View item details
- Download files
- Basic user accounts
- Admin review queue

**Infrastructure:**
- PostgreSQL database
- Docker deployment
- Configuration system

---

## Non-Goals (Explicitly Out of Scope)

- Format conversion (use Calibre for this)
- E-reader device sync (use Calibre for this)
- Social features (reviews, ratings, recommendations)
- Purchase/acquisition management
- DRM handling
