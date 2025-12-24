# Architecture Overview

## System Design

Bibliotheca Alexandria consists of two main components:

1. **The Librarian** - Backend cataloguing engine
2. **Web UI** - Patron-facing interface

Both interact with a shared PostgreSQL database and organised filesystem.

```
+------------------+
|   Returns Folder |  (Drop zone for new files)
+--------+---------+
         |
         v
+----------------------------------+
|        THE LIBRARIAN             |
|    (CLI + Background Daemon)     |
|----------------------------------|
|  - Inspect & identify files      |
|  - Extract metadata              |
|  - ISBN/API lookup               |
|  - Classify (Fiction vs DDC)     |
|  - File in correct location      |
|  - Extract/fetch covers          |
|  - Update database               |
|  - Handle duplicates             |
|  - Queue uncertain items         |
+----------------------------------+
         |
         v
+----------------------------------------------------------+
|                    Library Filesystem                     |
|  /library                                                 |
|  ├── Fiction/                                             |
|  │   └── Brandon Sanderson - Mistborn 01/                |
|  │       ├── cover.jpg                                   |
|  │       └── Brandon Sanderson - Mistborn 01.epub        |
|  ├── Non-Fiction/                                         |
|  │   └── 005 - Computer Programming/                     |
|  │       └── Robert C. Martin - Clean Code/              |
|  │           ├── cover.jpg                               |
|  │           └── Robert C. Martin - Clean Code.pdf       |
|  └── .returns/                                            |
|      └── (incoming files)                                 |
+----------------------------------------------------------+
         |
         v
+------------------+
|   PostgreSQL 17  |
|   (Catalogue)    |
+------------------+
         |
         v
+----------------------------------+
|           WEB UI                 |
|    (Browse, Search, Download)    |
|----------------------------------|
|  - Author/genre/series browsing  |
|  - Full-text search              |
|  - Item details & covers         |
|  - File download                 |
|  - User accounts                 |
|  - Admin review queue            |
+----------------------------------+
```

## Core Principles

### 1. Filesystem as Source of Truth

The library folder structure is authoritative. The database is an index that enriches and enables search, but files live where the user (via The Librarian) places them.

- Files are never moved without explicit action
- If a file disappears, the database record is marked orphaned
- The Librarian manages filing, not the web UI

### 2. Hybrid Classification

The Librarian uses a practical approach to classification:

**Fiction** - Stored flat without genre subfolders:
- Genres are multi-valued and stored as database tags
- Subjects from APIs (Open Library, Google Books) are mapped to genre tags
- Web UI enables filtering by any combination of genres

**Non-Fiction** - Organised by DDC:
- Consults authoritative sources (OCLC Classify, Open Library)
- Uses subject-to-DDC mapping when lookups fail
- Queues uncertain items for human review
- Does not guess - escalates when unsure

### 3. Separation of Concerns

| Component | Responsibility |
|-----------|----------------|
| The Librarian | Cataloguing, classification, filing, metadata |
| Web UI | Discovery, access, user experience |
| PostgreSQL | Persistence, search indexing |
| Filesystem | Actual storage, DDC organisation |

## Component Details

### The Librarian

**Purpose:** Process new acquisitions and maintain the catalogue.

**Interfaces:**
- CLI for manual operations
- Daemon for automated watching
- Direct database access

**Key modules:**
- `inspector` - File format detection, checksum, embedded metadata
- `identifier` - ISBN extraction, content scanning
- `enricher` - API lookups (OCLC, Open Library, Google Books)
- `classifier` - DDC determination, subject mapping
- `filer` - Naming, moving, database updates
- `maintainer` - Integrity checks, duplicate handling

See [The Librarian](the-librarian.md) for detailed documentation.

### Web UI

**Purpose:** Allow users to discover and access library content.

**Technology:** FastAPI backend + Vue.js/Svelte frontend

**Key views:**
- Browse (by author, genre, series, recent)
- Search results
- Item detail
- Download/access
- Admin (review queue, settings)

**API endpoints:**
```
GET  /api/items                 # List/search items
GET  /api/items/{id}            # Item details
GET  /api/items/{id}/files      # Available files
GET  /api/items/{id}/cover      # Cover image
GET  /api/files/{id}/download   # Download file

GET  /api/authors               # List authors
GET  /api/authors/{id}          # Author with their items

GET  /api/series                # List series
GET  /api/series/{name}         # Series with items

GET  /api/genres                # List genres/tags

GET  /api/review-queue          # Items needing review
POST /api/review-queue/{id}     # Submit review decision

POST /api/auth/login            # User login
POST /api/auth/logout           # User logout
GET  /api/auth/me               # Current user
```

### Database

**Purpose:** Store metadata, enable search, track users and progress.

**Technology:** PostgreSQL 17 with:
- Full-text search via `tsvector`
- JSONB for flexible identifiers
- Arrays for tags

See [Database Schema](schema.md) for full details.

### Filesystem

**Structure:**
```
/library                              # Configurable root
├── Fiction/                          # All fiction (genres as tags)
│   ├── Author - Title/               # Per-item folder
│   │   ├── cover.jpg                 # Cover image
│   │   ├── Author - Title.epub       # Primary format
│   │   └── Author - Title.mobi       # Additional formats
│   └── Author - Series NN - Title/   # Series with index
│       ├── cover.jpg
│       └── Author - Series NN - Title.epub
│
├── Non-Fiction/                      # DDC-organised non-fiction
│   ├── 000 - Computer Science/
│   │   └── Author - Title/
│   │       ├── cover.jpg
│   │       └── Author - Title.pdf
│   ├── 100 - Philosophy/
│   ├── 200 - Religion/
│   ├── 300 - Social Sciences/
│   ├── 400 - Language/
│   ├── 500 - Science/
│   ├── 600 - Technology/
│   ├── 700 - Arts/
│   └── 900 - History/
│
└── .returns/                         # Incoming items (drop zone)
```

**Key points:**
- Each item gets its own folder containing all formats and the cover
- Fiction uses flat structure with genre tags in database
- Non-Fiction uses DDC with human-readable folder names (e.g., "005 - Computer Programming")
- No separate `.covers/` directory - covers live with their items

## Data Flow

### Adding New Content

```
1. User drops file in /library/Returns/

2. The Librarian detects new file (via watch or manual trigger)

3. Inspector module:
   - Calculates checksum
   - Checks for duplicates
   - Identifies format
   - Extracts embedded metadata

4. Identifier module:
   - Looks for ISBN in metadata
   - Optionally scans content for ISBN

5. Enricher module:
   - Queries OCLC Classify
   - Queries Open Library
   - Queries Google Books (fallback)
   - Merges results

6. Classifier module:
   - Uses DDC from lookup if available
   - Falls back to subject mapping
   - Queues for review if uncertain

7. Filer module:
   - Generates canonical filename
   - Moves to DDC folder
   - Creates database records
   - Saves cover image

8. Item appears in Web UI
```

### Accessing Content

```
1. User browses or searches in Web UI

2. API queries PostgreSQL for matching items

3. Results returned with metadata and cover URLs

4. User selects item, views details

5. User clicks download

6. API serves file from filesystem
```

## Deployment

### Docker Compose

```yaml
services:
  librarian:
    build: ./librarian
    volumes:
      - library:/library
      - config:/config
    depends_on:
      - postgres

  web:
    build: ./web
    ports:
      - "8080:8080"
    volumes:
      - library:/library:ro    # Read-only access
    depends_on:
      - postgres

  postgres:
    image: postgres:17-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: alexandria
      POSTGRES_USER: alexandria
      POSTGRES_PASSWORD: ${DB_PASSWORD}

volumes:
  library:      # Mount to your DDC folder structure
  config:       # Configuration files
  pgdata:       # Database storage
```

### Deployment Options

- **Unraid**: Community Applications template
- **Docker Compose**: Standard deployment
- **Kubernetes**: Helm chart (future)

## Security Considerations

- Web UI requires authentication
- File downloads respect user permissions
- The Librarian runs with filesystem write access
- Web UI has read-only filesystem access
- Database credentials managed via environment/secrets
- No external network access required (APIs are optional enrichment)
