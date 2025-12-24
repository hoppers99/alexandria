# Database Schema

## Overview

Bibliotheca Alexandria uses PostgreSQL 17 for metadata storage, full-text search, and user management.

## Entity Relationship Diagram

```
+------------------+       +------------------+       +------------------+
| classifications  |       |     creators     |       |      users       |
+------------------+       +------------------+       +------------------+
| id (PK)          |       | id (PK)          |       | id (PK)          |
| code (unique)    |       | name             |       | username         |
| name             |       | sort_name        |       | email            |
| parent_code (FK) |       | identifiers      |       | password_hash    |
| system           |       | bio              |       | display_name     |
+------------------+       | photo_path       |       | is_admin         |
        |                  +------------------+       +------------------+
        |                          |                         |
        |                          |                         |
        v                          v                         v
+------------------+       +------------------+       +------------------+
|      items       |<----->| item_creators    |       | user_progress    |
+------------------+       +------------------+       +------------------+
| id (PK)          |       | item_id (FK)     |       | user_id (FK)     |
| uuid             |       | creator_id (FK)  |       | item_id (FK)     |
| title            |       | role             |       | file_id (FK)     |
| classification   |------>| position         |       | progress_percent |
| media_type       |       +------------------+       | position         |
| isbn/identifiers |                                  | last_accessed    |
| description      |                                  | completed        |
| series_name      |       +------------------+       +------------------+
| tags[]           |       |     files        |
| cover_path       |       +------------------+       +------------------+
| search_vector    |<------| id (PK)          |       |   collections    |
+------------------+       | item_id (FK)     |       +------------------+
                           | file_path        |       | id (PK)          |
                           | format           |       | user_id (FK)     |
                           | size_bytes       |       | name             |
                           | checksum_md5     |       | description      |
                           | checksum_sha256  |       | is_public        |
                           +------------------+       +------------------+
                                                              |
                                                              v
                                                      +------------------+
                                                      | collection_items |
                                                      +------------------+
                                                      | collection_id    |
                                                      | item_id (FK)     |
                                                      | added_at         |
                                                      +------------------+
```

## Table Definitions

### classifications
Stores the classification hierarchy (DDC by default).

```sql
CREATE TABLE classifications (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,  -- e.g., "005.133"
    name VARCHAR(255) NOT NULL,         -- e.g., "Python programming"
    parent_code VARCHAR(20),            -- e.g., "005.13"
    system VARCHAR(50) DEFAULT 'ddc',   -- ddc, lcc, custom
    FOREIGN KEY (parent_code) REFERENCES classifications(code)
);

CREATE INDEX idx_classifications_parent ON classifications(parent_code);
CREATE INDEX idx_classifications_system ON classifications(system);
```

### creators
Authors, narrators, editors, directors, etc.

```sql
CREATE TABLE creators (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    sort_name VARCHAR(255),             -- "Surname, First"
    identifiers JSONB,                  -- {"openlibrary": "OL123A", "viaf": "..."}
    bio TEXT,
    photo_path VARCHAR(500)
);

CREATE INDEX idx_creators_name ON creators(name);
CREATE INDEX idx_creators_sort ON creators(sort_name);
```

### items
Core table for all library items.

```sql
CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT gen_random_uuid() UNIQUE,
    title VARCHAR(500) NOT NULL,
    sort_title VARCHAR(500),
    subtitle VARCHAR(500),

    -- Classification
    classification_code VARCHAR(20) REFERENCES classifications(code),

    -- Type and format
    media_type VARCHAR(50) NOT NULL,    -- book, audiobook, video, periodical, document

    -- Identifiers
    isbn VARCHAR(20),
    isbn13 VARCHAR(20),
    asin VARCHAR(20),
    doi VARCHAR(100),
    identifiers JSONB,                  -- flexible additional IDs

    -- Metadata
    description TEXT,
    publisher VARCHAR(255),
    publish_date DATE,
    language VARCHAR(10) DEFAULT 'en',
    series_name VARCHAR(255),
    series_index DECIMAL(5,2),
    tags TEXT[],                        -- PostgreSQL array

    -- Physical/technical
    page_count INTEGER,
    duration_seconds INTEGER,           -- for audio/video

    -- Cover
    cover_path VARCHAR(500),

    -- Timestamps
    date_added TIMESTAMP DEFAULT NOW(),
    date_modified TIMESTAMP DEFAULT NOW(),

    -- Full-text search
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(subtitle, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'C')
    ) STORED
);

CREATE INDEX idx_items_search ON items USING GIN(search_vector);
CREATE INDEX idx_items_classification ON items(classification_code);
CREATE INDEX idx_items_media_type ON items(media_type);
CREATE INDEX idx_items_isbn ON items(isbn);
CREATE INDEX idx_items_isbn13 ON items(isbn13);
CREATE INDEX idx_items_series ON items(series_name);
CREATE INDEX idx_items_tags ON items USING GIN(tags);
```

### files
Physical files belonging to items. One item can have multiple formats.

```sql
CREATE TABLE files (
    id SERIAL PRIMARY KEY,
    item_id INTEGER REFERENCES items(id) ON DELETE CASCADE,
    file_path VARCHAR(1000) NOT NULL UNIQUE,  -- relative to library root
    format VARCHAR(20) NOT NULL,              -- epub, pdf, mobi, mp3, mp4, etc.
    size_bytes BIGINT,
    checksum_md5 VARCHAR(32),
    checksum_sha256 VARCHAR(64),
    date_added TIMESTAMP DEFAULT NOW(),
    metadata_extracted BOOLEAN DEFAULT FALSE,
    extraction_error TEXT
);

CREATE INDEX idx_files_item ON files(item_id);
CREATE INDEX idx_files_format ON files(format);
CREATE INDEX idx_files_checksum ON files(checksum_md5);
```

### item_creators
Many-to-many relationship between items and creators with roles.

```sql
CREATE TABLE item_creators (
    item_id INTEGER REFERENCES items(id) ON DELETE CASCADE,
    creator_id INTEGER REFERENCES creators(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'author',  -- author, narrator, editor, director, translator
    position INTEGER DEFAULT 0,         -- ordering for multiple creators
    PRIMARY KEY (item_id, creator_id, role)
);

CREATE INDEX idx_item_creators_creator ON item_creators(creator_id);
```

### users
User accounts for authentication and personalisation.

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    is_admin BOOLEAN DEFAULT FALSE,
    can_download BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);
```

### user_progress
Tracks reading/viewing progress per user.

```sql
CREATE TABLE user_progress (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    item_id INTEGER REFERENCES items(id) ON DELETE CASCADE,
    file_id INTEGER REFERENCES files(id),
    progress_percent DECIMAL(5,2),
    position VARCHAR(100),              -- page, chapter, timestamp depending on format
    last_accessed TIMESTAMP DEFAULT NOW(),
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    PRIMARY KEY (user_id, item_id)
);

CREATE INDEX idx_progress_user ON user_progress(user_id);
CREATE INDEX idx_progress_last ON user_progress(last_accessed DESC);
```

### collections
User-created collections/shelves.

```sql
CREATE TABLE collections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_collections_user ON collections(user_id);
CREATE INDEX idx_collections_public ON collections(is_public) WHERE is_public = TRUE;
```

### collection_items
Items within collections.

```sql
CREATE TABLE collection_items (
    collection_id INTEGER REFERENCES collections(id) ON DELETE CASCADE,
    item_id INTEGER REFERENCES items(id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT NOW(),
    notes TEXT,
    PRIMARY KEY (collection_id, item_id)
);
```

## Full-Text Search

The `search_vector` column on items provides fast full-text search:

```sql
-- Example search query
SELECT id, title, ts_rank(search_vector, query) as rank
FROM items, plainto_tsquery('english', 'python programming') query
WHERE search_vector @@ query
ORDER BY rank DESC
LIMIT 20;
```

For more advanced search, consider adding Meilisearch or Elasticsearch as an optional component.

## Data Integrity

### Checksums
Files are checksummed (MD5 and SHA-256) to:
- Detect duplicates across the library
- Verify file integrity over time
- Track if files change externally

### Soft vs Hard Deletes
When files are removed from the filesystem:
- The `files` record is deleted
- The `items` record remains (orphaned) until explicitly cleaned up
- This allows for recovery if files are accidentally deleted

## Migration Strategy

Initial schema creation via Alembic migrations for version control and reproducibility.
