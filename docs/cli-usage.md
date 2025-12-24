# CLI Usage Guide

The Librarian is the command-line interface for managing your Alexandria library. This guide covers all available commands and their options.

## Installation

After cloning the repository:

```bash
# Install dependencies
uv sync

# Start the database
docker compose up -d

# Run database migrations
uv run alembic upgrade head

# Seed classification data (DDC codes)
uv run librarian seed
```

## Command Overview

| Command | Description |
|---------|-------------|
| `librarian seed` | Seed the database with DDC classification codes |
| `librarian migrate scan` | Scan source library and extract file metadata |
| `librarian migrate rescan` | Re-extract metadata with improved extractors |
| `librarian migrate calibre` | Enrich files with metadata from Calibre database |
| `librarian migrate run` | Process files through enrichment and classification pipeline |
| `librarian migrate status` | Show migration progress statistics |
| `librarian review` | Interactively review files needing manual classification |

## Migration Commands

### Scanning Your Library

```bash
# Scan the default source library (from .env)
uv run librarian migrate scan

# Scan a specific directory
uv run librarian migrate scan --source /path/to/books

# Skip duplicate identification
uv run librarian migrate scan --no-identify-duplicates
```

The scan command:
- Finds all supported files (EPUB, MOBI, PDF, etc.)
- Extracts embedded metadata (title, authors, ISBN, etc.)
- Stores file info in the database for processing
- Identifies duplicate files by content hash

### Re-extracting Metadata

If extractors are improved or you want to refresh metadata:

```bash
# Rescan all pending files
uv run librarian migrate rescan

# Rescan only MOBI files
uv run librarian migrate rescan --format mobi

# Rescan all files regardless of status
uv run librarian migrate rescan --status all

# Limit to first 100 files
uv run librarian migrate rescan --limit 100

# Adjust batch size for commits
uv run librarian migrate rescan --batch-size 100
```

Options:
- `--status`: Filter by status (`pending`, `failed`, `all`)
- `--format`: Filter by format (`epub`, `pdf`, `mobi`)
- `--limit`: Maximum number of files to process
- `--batch-size`: Commit to database every N files (default: 50)

### Calibre Enrichment

If you have a Calibre library, you can pull ISBNs and metadata from it:

```bash
# Enrich pending files from Calibre
uv run librarian migrate calibre

# Process only first 500 files
uv run librarian migrate calibre --limit 500
```

This is particularly useful for files where the ISBN isn't embedded but Calibre has it from manual entry or other sources.

**Configuration required in `.env`:**
```bash
ALEXANDRIA_ENABLE_CALIBRE=true
ALEXANDRIA_CALIBRE_LIBRARY=/path/to/calibre/library
```

### Running the Pipeline

The main processing step that enriches, classifies, and files your books:

```bash
# Run the full pipeline
uv run librarian migrate run

# Process in smaller batches
uv run librarian migrate run --batch-size 5

# Limit total files processed
uv run librarian migrate run --limit 100

# Preview without making changes
uv run librarian migrate run --dry-run
```

Options:
- `--batch-size`: Files per batch (default: 10)
- `--limit`: Maximum files to process
- `--dry-run`: Show what would be done without copying files

The pipeline for each file:
1. Queries metadata APIs (OpenLibrary, Google Books, LibraryThing)
2. Attempts DDC classification from subjects and API data
3. Either files to library (high confidence) or marks for review (low confidence)

### Checking Status

```bash
uv run librarian migrate status
```

Shows:
- Files by status (pending, migrated, duplicate, failed, skipped)
- Files by format (EPUB, PDF, MOBI, etc.)
- Total library size

## Review Command

For files that couldn't be automatically classified:

```bash
# Start interactive review
uv run librarian review

# Review only PDFs
uv run librarian review --format pdf

# Show 50 files at a time
uv run librarian review --limit 50

# Skip first 20 files
uv run librarian review --skip 20
```

### Interactive Review Actions

When reviewing a file, you have these options:

| Key | Action |
|-----|--------|
| `s` | Skip to next file |
| `i` | Search by ISBN (prompts for ISBN input) |
| `t` | Search by title/author (prompts for input) |
| `f` | Force file with current metadata |
| `d` | Mark as duplicate/skip permanently |
| `o` | Open file location in file manager |
| `q` | Quit review |

### Review Workflow Example

```
━━━ 1/1738 ━━━

Filename: Python_Programming_Guide.pdf
Path: /source/library/programming/Python_Programming_Guide.pdf
Format: PDF  Size: 5.2 MB

Extracted metadata:
  Title: Python Programming Guide
  Authors: [none]
  ISBN: [none]

Classification:
  DDC: [none]
  Confidence: 0%

Actions:
  s Skip to next
  i Search by ISBN
  t Search by title/author
  f File with current metadata (force)
  d Mark as duplicate/skip permanently
  o Open file location
  q Quit review

Action [s]:
```

## Other Commands

### Seeding Classifications

Must be run once before using the system:

```bash
uv run librarian seed
```

Populates the database with Dewey Decimal Classification codes.

### Placeholder Commands

These commands are defined but not yet implemented:

- `librarian add <path>` - Add a specific file to the library
- `librarian identify <path>` - Identify a file without filing it
- `librarian lookup` - Search for metadata manually
- `librarian check` - Verify library integrity
- `librarian duplicates` - Find and report duplicate files
- `librarian process` - Process files in the Returns folder

## Configuration

All configuration is done via environment variables. Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

### Key Settings

```bash
# Database connection
ALEXANDRIA_DB_HOST=localhost
ALEXANDRIA_DB_PORT=5433
ALEXANDRIA_DB_NAME=alexandria
ALEXANDRIA_DB_USER=alexandria
ALEXANDRIA_DB_PASSWORD=alexandria

# Library paths
ALEXANDRIA_LIBRARY_ROOT=/path/to/your/library
ALEXANDRIA_SOURCE_LIBRARY=/path/to/source/library
ALEXANDRIA_COVERS_DIR=/path/to/your/library/.covers
ALEXANDRIA_RETURNS_DIR=/path/to/your/library/.returns

# Calibre integration
ALEXANDRIA_ENABLE_CALIBRE=false
ALEXANDRIA_CALIBRE_LIBRARY=/path/to/calibre/library

# Classification threshold (0.0-1.0)
# Files below this confidence go to review queue
ALEXANDRIA_CONFIDENCE_THRESHOLD=0.6

# API settings
ALEXANDRIA_ENABLE_OCLC=true
ALEXANDRIA_ENABLE_OPENLIBRARY=true
ALEXANDRIA_ENABLE_GOOGLE_BOOKS=true
ALEXANDRIA_ENABLE_LIBRARYTHING=true
# ALEXANDRIA_LIBRARYTHING_API_KEY=your-key-here
```

## Typical Migration Workflow

1. **Initial setup:**
   ```bash
   docker compose up -d
   uv run alembic upgrade head
   uv run librarian seed
   ```

2. **Scan your source library:**
   ```bash
   uv run librarian migrate scan
   ```

3. **Optionally enrich from Calibre:**
   ```bash
   uv run librarian migrate calibre
   ```

4. **Run the pipeline:**
   ```bash
   uv run librarian migrate run
   ```

5. **Check progress:**
   ```bash
   uv run librarian migrate status
   ```

6. **Review files that need attention:**
   ```bash
   uv run librarian review
   ```

7. **If extractors are improved, rescan and rerun:**
   ```bash
   uv run librarian migrate rescan --format mobi
   uv run librarian migrate run
   ```

## Troubleshooting

### Database Connection Issues

If you see database connection errors:

```bash
# Check if Docker is running
docker ps

# Start the database
docker compose up -d

# Check database logs
docker compose logs db
```

### Files Not Being Classified

If many files end up in the review queue:

1. **Check the confidence threshold** - Lower it in `.env`:
   ```bash
   ALEXANDRIA_CONFIDENCE_THRESHOLD=0.5
   ```

2. **Enable Calibre integration** - ISBNs from Calibre can help:
   ```bash
   ALEXANDRIA_ENABLE_CALIBRE=true
   ALEXANDRIA_CALIBRE_LIBRARY=/path/to/calibre
   ```

3. **Check for extraction issues** - Rescan specific formats:
   ```bash
   uv run librarian migrate rescan --format mobi
   ```

### Reviewing Large Queues

For large review queues, filter by format to work through systematically:

```bash
# Work through EPUBs first (often have better metadata)
uv run librarian review --format epub

# Then MOBIs
uv run librarian review --format mobi

# Finally PDFs (often need manual input)
uv run librarian review --format pdf
```
