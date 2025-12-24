# Bibliotheca Alexandria

A self-hosted, open-source digital library system for mixed media, organised by classification system.

## Overview

Bibliotheca Alexandria (or simply "Alexandria") is a personal digital library management system designed to organise and serve mixed media collections - e-books, audiobooks, video tutorials, documents, and more - using a filesystem-based approach with rich metadata indexing.

Unlike traditional e-book managers like Calibre that take ownership of your file structure, Alexandria treats your organised filesystem as the source of truth and builds a searchable, browsable catalogue on top of it.

## Key Principles

1. **Filesystem is truth** - Files stay where you put them; the database indexes but doesn't own
2. **Classification-first** - Dewey Decimal Classification (DDC) built-in, extensible to other systems
3. **Format-agnostic** - E-books, audiobooks, video, documents, periodicals
4. **Metadata-rich** - Leverage existing tools, APIs, and AI for extraction
5. **Shareable** - Multi-user with permissions
6. **Self-hosted** - Docker-first deployment, designed for home servers (Unraid, etc.)

## Status

**Active Development** - Core cataloguing pipeline and web UI functional.

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/hoppers99/alexandria.git
cd alexandria

# Copy and configure environment
cp .env.example .env
# Edit .env to set ALEXANDRIA_LIBRARY_ROOT to your library path

# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec backend uv run alembic upgrade head

# Seed classification data
docker-compose exec backend uv run librarian seed
```

Access the web UI at http://localhost:5173

### Development Setup

See [CONTRIBUTING.md](CONTRIBUTING.md) for local development instructions.

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Root directory for your library. Should contain:
#   - Fiction/       (flat structure, genres as database tags)
#   - Non-Fiction/   (DDC-organised subdirectories)
#   - .returns/      (drop zone for new files to be processed)
ALEXANDRIA_LIBRARY_ROOT=/path/to/your/library

# Classification confidence threshold (0.0-1.0)
# Files below this threshold go to the review queue
ALEXANDRIA_CONFIDENCE_THRESHOLD=0.8

# Optional: Calibre integration for migration
# ALEXANDRIA_ENABLE_CALIBRE=true
# ALEXANDRIA_CALIBRE_LIBRARY=/path/to/calibre/library
```

## Library Structure

```
/library                    # ALEXANDRIA_LIBRARY_ROOT
├── Fiction/                # Flat structure, genres as database tags
│   └── Author - Title/
│       ├── cover.jpg
│       └── Author - Title.epub
├── Non-Fiction/            # DDC-organised subdirectories
│   └── 005 - Computer Programming/
│       └── Author - Title/
│           ├── cover.jpg
│           └── Author - Title.pdf
└── .returns/               # Drop zone for new files to be processed
```

## Features

### Current

- **Review Queue** - Process incoming files with metadata enrichment from Google Books and Open Library
- **Multi-source Search** - Search multiple metadata sources and select the best match
- **Duplicate Detection** - Warns before filing if a potential duplicate exists
- **Library Browser** - Browse by author, series, or recent additions
- **Piles (Collections)** - Create personal reading lists and collections
- **In-browser Reader** - Read EPUB, MOBI, and other formats directly in the browser
- **Item Enrichment** - Improve metadata on existing library items via search
- **Metadata Editing** - Edit titles, descriptions, series, tags, and request author fixes or refile operations

### Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) for planned features including:
- Cover search and replacement from external sources
- Background/backdrop images (Plex-style)
- Book sample extraction and preview
- OPDS feed for e-reader apps
- Watch folder for automatic processing

## How It Works

### Pipeline Flow

```
.returns/ (drop zone for new files)
         │
         ▼
┌─────────────────┐
│  Metadata       │  Extract from EPUB/MOBI/PDF internals
│  Extraction     │  Parse filenames for author/title/series
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Enrichment     │  Query Google Books, Open Library
└────────┬────────┘  Merge results with priority rules
         │
         ▼
┌─────────────────┐
│  Classification │  Determine DDC code
└────────┬────────┘  Detect fiction vs non-fiction
         │
         ▼
     ┌───┴───┐
     │       │
High conf.  Low conf.
     │       │
     ▼       ▼
┌─────────┐ ┌─────────────┐
│  Auto   │ │   Review    │
│  File   │ │   Queue     │
└─────────┘ └─────────────┘
```

### Metadata Sources

| Source | What it provides |
|--------|------------------|
| **File extraction** | Title, authors, ISBN (from EPUB/MOBI/PDF internals) |
| **Filename parsing** | Author, title, series from naming conventions |
| **Google Books API** | Title, authors, description, covers, page count |
| **Open Library API** | Title, authors, subjects, DDC, covers |
| **OCLC Classify** | Authoritative DDC classification |
| **LibraryThing API** | Series info (optional, requires API key) |

### Migration from Existing Library

For migrating an existing library (e.g., from Calibre):

```bash
# Scan source library to extract metadata
uv run librarian migrate scan /path/to/source/library

# Optional: Enrich from Calibre database
uv run librarian migrate calibre

# Run the pipeline - enriches, classifies, and files
uv run librarian migrate run

# Review files that need manual classification
uv run librarian review
```

See the [CLI Usage Guide](docs/cli-usage.md) for detailed documentation.

## Documentation

- [Architecture Overview](docs/architecture.md) - System design and data flow
- [CLI Usage Guide](docs/cli-usage.md) - Command-line interface reference
- [Database Schema](docs/schema.md) - Data model documentation
- [Roadmap](docs/ROADMAP.md) - Planned features and future ideas
- [Contributing](CONTRIBUTING.md) - Development setup and guidelines

## Technology Stack

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: SvelteKit 5, Tailwind CSS
- **Deployment**: Docker, docker-compose

## Licence

This project is licensed under the GNU General Public License v3.0 (GPL-3.0).

See [LICENCE](LICENCE) for details.
